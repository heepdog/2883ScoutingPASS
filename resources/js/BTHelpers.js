// Bluetooth helper utilities moved out of individual pages
// Provides a simple global API (window.BTHelpers) for connecting, sending
// and receiving data over a generic BLE UART-style service.

(function() {
    const FILE_SERVICE_UUID = '6e400001-b5a3-f393-e0a9-e50e24dcca9e';
    const FILE_TX_CHARACTERISTIC = '6e400002-b5a3-f393-e0a9-e50e24dcca9e';
    const FILE_RX_CHARACTERISTIC = '6e400003-b5a3-f393-e0a9-e50e24dcca9e';

    // The physical BluetoothDevice returned by the browser API
    let connectedDevice = null;
    // A separate reference to the gatt server obtained from the device
    let gattServer = null;
    let service = null;
    let txCharacteristic = null;
    let rxCharacteristic = null;

    async function connect() {
        // If already connected simply return the existing device object
        if (connectedDevice && connectedDevice.gatt.connected) {
            return connectedDevice;
        }

        let device;
        try {
            device = await navigator.bluetooth.requestDevice({
                filters: [{ services: [FILE_SERVICE_UUID] }],
                optionalServices: [FILE_SERVICE_UUID]
            });
        } catch (err) {
            console.warn('requestDevice with service filter failed, falling back to acceptAllDevices:', err);
            device = await navigator.bluetooth.requestDevice({
                acceptAllDevices: true,
                optionalServices: [FILE_SERVICE_UUID]
            });
        }

        // open a GATT connection but keep the device around for its metadata
        gattServer = await device.gatt.connect();
        connectedDevice = device;
        console.log(`Connected to device: ${device.name || device.id}`);

        try {
            service = await gattServer.getPrimaryService(FILE_SERVICE_UUID);
        } catch (err) {
            console.error('Failed to get UART service from device:', err);
            if (gattServer && gattServer.connected) {
                try { gattServer.disconnect(); } catch (_) {}
            }
            throw new Error('Could not find UART service on the connected device.');
        }

        console.log('Obtained service:', service.uuid);
        txCharacteristic = await service.getCharacteristic(FILE_TX_CHARACTERISTIC);
        console.log('Obtained TX characteristic:', txCharacteristic.uuid);
        rxCharacteristic = await service.getCharacteristic(FILE_RX_CHARACTERISTIC);
        console.log('Obtained RX characteristic:', rxCharacteristic.uuid);

        return connectedDevice;
    }

    /**
     * Begin listening for incoming notifications.
     *
     * @param {function(Uint8Array|Object):void} onData  callback invoked when
     *        a complete packet is available.  Use {@link options.buffer} or
     *        supply a protoType to aggregate chunked data until an end marker
     *        is seen.
     * @param {object} [options]
     * @param {protobuf.Type} [options.protoType]  message constructor from
     *        `root.lookupType(...)` used to decode the completed bytes.
     * @param {boolean} [options.buffer=false]  if true, chunks are collected
     *        internally until an end marker is detected, then onData is called
     *        with the full buffer (or decoded object).  Without buffering each
     *        chunk triggers onData immediately.
     * @param {Uint8Array|number} [options.endMarker=0x02]  byte or sequence that
     *        marks the end of a transmission when buffering.  A single number
     *        is treated as a one-byte marker.
     */
    async function startNotifications(onData, options = {}) {
        if (!rxCharacteristic) {
            throw new Error('Call connect() before starting notifications');
        }

        await rxCharacteristic.startNotifications();

        const bufferChunks = [];
        const { protoType, buffer: wantBuffer=false } = options;
        //setsup the end marker for buffered reads, defaulting to 0x02 if not specified.
        // The marker can be a single byte (number) or a sequence (Uint8Array).
        let endMarker;
        if (options.endMarker !== undefined) {
            if (typeof options.endMarker === 'number') {
                endMarker = new Uint8Array([options.endMarker]);
            } else {
                endMarker = options.endMarker;
            }
        } else {
            endMarker = new Uint8Array([0x02]);
        }

        // This function is called whenever a new chunk of data is received.
        // It either delivers the chunk directly to onData, or buffers it until
        // the end marker is detected and then delivers the full message.
        // If protoType is provided, it attempts to decode the bytes before delivering.
        const deliver = raw => {
            if (protoType && window.protobuf) {
                try {
                    const decoded = protoType.decode(raw);
                    onData(decoded);
                    return;
                } catch (e) {
                    console.warn('protobuf decode failed, passing raw bytes', e);
                }
            }
            onData(raw);
        };

        const tryFlush = () => {
            if (bufferChunks.length === 0) return;
            const all = new Uint8Array(bufferChunks.reduce((sum, arr) => sum + arr.length, 0));
            let offset = 0;
            for (const arr of bufferChunks) {
                all.set(arr, offset);
                offset += arr.length;
            }
            bufferChunks.length = 0;
            deliver(all);
        };

        rxCharacteristic.addEventListener('characteristicvaluechanged', event => {
            const chunk = new Uint8Array(event.target.value.buffer);
            if (wantBuffer) {
                bufferChunks.push(chunk);
                // Check whether the end marker appears at the end of the
                // accumulated data (simple check: last byte(s) of chunk).
                let markerFound = false;
                if (endMarker.length === 1) {
                    if (chunk[chunk.length - 1] === endMarker[0]) {
                        markerFound = true;
                    }
                } else if (chunk.length >= endMarker.length) {
                    markerFound = true;
                    for (let i = 0; i < endMarker.length; i++) {
                        if (chunk[chunk.length - endMarker.length + i] !== endMarker[i]) {
                            markerFound = false;
                            break;
                        }
                    }
                }
                if (markerFound) {
                    tryFlush();
                }
            } else {
                deliver(chunk);
            }
        });
    }

    async function writeBytes(bytes) {
        if (!txCharacteristic) {
            throw new Error('Call connect() before writing');
        }
        await txCharacteristic.writeValue(bytes);
    }

    async function sendFile(blob) {
        // This helper opens a fresh connection for each transfer, mirroring the
        // behaviour previously embedded in saveData.exportBT().
        const device = await navigator.bluetooth.requestDevice({
            filters: [{ services: [FILE_SERVICE_UUID] }]
        });
        const server = await device.gatt.connect();
        const svc = await server.getPrimaryService(FILE_SERVICE_UUID);
        const char = await svc.getCharacteristic(FILE_TX_CHARACTERISTIC);

        const arrayBuffer = await blob.arrayBuffer();
        const bytes = new Uint8Array(arrayBuffer);
        const CHUNK_SIZE = 20; // BLE safe chunk size

        // header/start marker
        await char.writeValue(new Uint8Array([0x01]));

        for (let i = 0; i < bytes.length; i += CHUNK_SIZE) {
            const chunk = bytes.slice(i, i + CHUNK_SIZE);
            await char.writeValue(chunk);
            console.log(`Sent ${Math.min(i + CHUNK_SIZE, bytes.length)} of ${bytes.length} bytes`);
        }

        // trailer/end marker
        await char.writeValue(new Uint8Array([0x02]));

        server.disconnect();
    }

    function disconnect() {
        if (connectedDevice && connectedDevice.gatt.connected) {
            connectedDevice.gatt.disconnect();
        }
    }

    // Expose the helper on the global window for backwards compatibility with
    // existing inline onclick handlers.
    window.BTHelpers = {
        connect,
        startNotifications,
        writeBytes,
        sendFile,
        disconnect,
        // also make constants available for callers who might need them
        FILE_SERVICE_UUID,
        FILE_TX_CHARACTERISTIC,
        FILE_RX_CHARACTERISTIC,
        // expose the physical device object (not the gatt server)
        get connectedDevice() {
            return connectedDevice;
        }
    };
})();
