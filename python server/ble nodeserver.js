// Critical Steps for Windows
// Driver Setup: You must follow the Bleno Windows Setup Guide. This involves using Zadig 
// to switch your Bluetooth adapter to the WinUSB driver.
// Installation:
// bash
// npm install @abandonware/bleno
// Use code with caution.

// Permissions: Run your command prompt or VS Code as Administrator


const bleno = require('@abandonware/bleno');

const UART_SERVICE_UUID = '6e400001b5a3f393e0a9e50e24dcca9e';
const RX_CHAR_UUID = '6e400002b5a3f393e0a9e50e24dcca9e';
const TX_CHAR_UUID = '6e400003b5a3f393e0a9e50e24dcca9e';

// Define the RX Characteristic (where Web Bluetooth writes data)
const RxCharacteristic = new bleno.Characteristic({
    uuid: RX_CHAR_UUID,
    properties: ['write', 'writeWithoutResponse'],
    onWriteRequest: function(data, offset, withoutResponse, callback) {
        console.log('Received from Web Bluetooth:', data.toString('utf8'));
        callback(this.RESULT_SUCCESS);
    }
});

// Define the TX Characteristic (for sending data back)
const TxCharacteristic = new bleno.Characteristic({
    uuid: TX_CHAR_UUID,
    properties: ['notify'],
    onSubscribe: function(maxValueSize, updateValueCallback) {
        console.log('Web Bluetooth subscribed to TX notifications');
    }
});

bleno.on('stateChange', function(state) {
    if (state === 'poweredOn') {
        bleno.startAdvertising('NodeJS_UART', [UART_SERVICE_UUID]);
    } else {
        bleno.stopAdvertising();
    }
});

bleno.on('advertisingStart', function(error) {
    if (!error) {
        bleno.setServices([
            new bleno.PrimaryService({
                uuid: UART_SERVICE_UUID,
                characteristics: [RxCharacteristic, TxCharacteristic]
            })
        ]);
        console.log('UART Server is live...');
    }
});
