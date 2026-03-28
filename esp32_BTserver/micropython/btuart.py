import uasyncio as asyncio
import aioble
import bluetooth
import os

# Nordic UART Service UUIDs
_SERVICE_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_WRITE_UUID   = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
_READ_UUID    = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")

# Command bytes
CMD_PUT   = 0x01
CMD_END   = 0x02
CMD_GET   = 0x03
CMD_CLEAR = 0x04

CHUNK_SIZE = 20
LOG_FILE = "ble_data.txt"

put_mode = False

uart_service = aioble.Service(_SERVICE_UUID)
write_char = aioble.Characteristic(
    uart_service,
    _WRITE_UUID,
    write=True,
    write_no_response=True,
    capture=True
)
read_char = aioble.Characteristic(
    uart_service,
    _READ_UUID,
    read=True,
    notify=True
)
aioble.register_services(uart_service)


def append_to_file(data: bytes):
    try:
        with open(LOG_FILE, "ab") as f:
            f.write(data)
        print(f"Saved {len(data)} bytes to {LOG_FILE}")
    except Exception as e:
        print("Failed to write to file:", e)


async def send_stored_data(connection):
    if LOG_FILE not in os.listdir():
        print("No data file found")
        read_char.notify(connection, b"No data file found")
        return

    try:
        with open(LOG_FILE, "rb") as f:
            has_data = False
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                has_data = True
                read_char.notify(connection, chunk)
                print(f"Sent chunk ({len(chunk)} bytes)")
                await asyncio.sleep_ms(15)

        if has_data:
            read_char.notify(connection, bytes([CMD_END]))
            print("All data sent")
        else:
            read_char.notify(connection, b"No data stored")
            print("Data file exists but is empty")
    except Exception as e:
        print("Error reading stored data:", e)
        read_char.notify(connection, b"ERR:READ_FAIL")


async def clear_stored_data(connection):
    try:
        os.remove(LOG_FILE)
        read_char.notify(connection, b"Data Cleared")
        print("Data file deleted")
    except OSError:
        read_char.notify(connection, b"No data file found")
        print("No data file to delete")


async def handle_writes(connection):
    global put_mode

    while True:
        if not getattr(connection, 'connected', True):
            print("Connection closed, exiting write handler")
            break

        try:
            conn, data = await write_char.written()
        except Exception as e:
            print("write_char.written() failed or connection ended:", e)
            break

        if not getattr(connection, 'connected', True):
            print("Connection dropped after write event, exiting write handler")
            break

        print(f"Received {len(data)} bytes from {conn}")

        if len(data) == 0:
            continue

        command = data[0]

        if command == CMD_PUT:
            put_mode = True
            read_char.notify(connection, b"Entered put mode")
            print("Entered put mode")
            continue

        if command == CMD_END:
            if put_mode:
                put_mode = False
                read_char.notify(connection, b"Exited put mode")
                print("Exited put mode")
            continue

        if command == CMD_GET:
            print("Send stored data command received")
            asyncio.create_task(send_stored_data(connection))
            continue

        if command == CMD_CLEAR:
            print("Clear stored data command received")
            await clear_stored_data(connection)
            continue

        if put_mode:
            append_to_file(data)
            read_char.notify(connection, b"Data Stored")
            print("Data stored")
            continue

        read_char.notify(connection, b"Unknown command")
        print("Unknown command")


async def main():
    while True:
        print("Advertising BLE UART service...")
        try:
            async with await aioble.advertise(
                250_000,
                name="ESP32-C3 FRED",
                services=[_SERVICE_UUID]
            ) as connection:
                print("Connected to", connection)
                global put_mode
                put_mode = False

                writer_task = asyncio.create_task(handle_writes(connection))

                try:
                    # Wait for the client to disconnect before continuing.
                    if hasattr(connection, "disconnected"):
                        await connection.disconnected()
                    elif hasattr(connection, "wait_disconnected"):
                        await connection.wait_disconnected()
                    else:
                        # Fallback: keep the task running until it ends.
                        await writer_task
                except Exception as e:
                    print("Disconnect wait ended with:", e)
                finally:
                    if not writer_task.done():
                        try:
                            writer_task.cancel()
                        except Exception:
                            pass

                print("Client disconnected, restarting advertising")
        except Exception as e:
            print("Connection error:", e)
            await asyncio.sleep_ms(200)


try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Stopped")
