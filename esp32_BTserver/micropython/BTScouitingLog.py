import asyncio
import aioble
import bluetooth
import binascii
import os

# UUIDs
# _SERVICE_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
# _WRITE_UUID   = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E") 
# _READ_UUID    = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E") 

# Using Nordic UART Service UUIDs for compatibility with existing clients (like WebBluetooth)
_SERVICE_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_WRITE_UUID   = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
_READ_UUID    = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")


# Control Bytes
CMD_FILE_START  = b'\x01'
CMD_FILE_STOP   = b'\x03'
CMD_FILE_CLEAR  = b'\x04' # Clear log file (responds with "DELETED")
CMD_STORAGE_INF = b'\x05' # Request for free storage info (responds with "FREE:XXKB")
CMD_AUTH_ATTEMPT = b'\x06' # Prefix for the passkey
CMD_LOG_ENABLE  = b'\x12' # Enable logging (data after this will be logged until CMD_LOG_DISABLE is received or space runs out)
CMD_LOG_DISABLE = b'\x14' # Disable logging (stop accepting log data, but don't clear the file)

CHUNK_SIZE = 20 # Bluetooth LE typically has a max payload of 20 bytes, adjust as needed

# Security Configuration
PASSKEY = "12345" # Change this to your desired pin
LOG_FILE = "data_log.txt"
MIN_FREE_SPACE = 50 * 1024 # 50KB safety

# Global States (Reset on every connection)
is_authenticated = False
is_transferring = False
is_logging = False

log_service = aioble.Service(_SERVICE_UUID)
write_char = aioble.Characteristic(log_service, _WRITE_UUID, write=True, write_no_response=True, capture=True)
read_char  = aioble.Characteristic(log_service, _READ_UUID, read=True, notify=True)
aioble.register_services(log_service)

async def send_file_task(connection):
    """Sends the log file to the device that requests it

    Args:
        connection (BLEServer): Ble service that is running on the device
    """
    global is_transferring
    if LOG_FILE not in os.listdir():
        print("Log file not found, cannot transfer")
        read_char.notify(connection, b"ERR:NO_FILE")
        is_transferring = False
        return
    crc = 0
    with open(LOG_FILE, "rb") as f: # Read in binary mode for accurate CRC calculation
        while is_transferring:
            # Bluetooth LE typically has a max payload of 20 bytes, adjust as needed
            chunk = f.read(CHUNK_SIZE)
            
            # If the chunk is empty, we've reached the end of the file. Send the 
            # final CRC and break.
            if not chunk:
                read_char.notify(connection, "CRC:{:08X}".format(crc & 0xFFFFFFFF).encode())
                break
            # Update the CRC with the new chunk
            crc = binascii.crc32(chunk, crc)
            print(f"Sending chunk: {chunk} - CRC so far: {crc:08X}")
            read_char.notify(connection, chunk)
            await asyncio.sleep_ms(15)
    is_transferring = False

async def handle_writes(connection):
    """Continuously monitors the Write characteristic of the service that is started on
    the device. This is where all commands and log data are sent from the client, so
    this function handles authentication, command parsing, and log data writing. 
    The function is designed to run indefinitely until the client disconnects, at which
    point the main loop will restart it with a fresh state.

    Args:
        connection (BLEServer): Ble service that is running on the device
    """
    global is_authenticated, is_transferring, is_logging
    
    while True:
        conn, data = await write_char.written()
        print(f"Received data: {data} from {conn} - Authenticated: {is_authenticated} - Transferring: {is_transferring} - Logging: {is_logging}")
        # 1. Authentication Check (MUST happen first)
        if not is_authenticated:
            # Check if the packet starts with our Auth Byte
            if data.startswith(CMD_AUTH_ATTEMPT):
                attempt = data[1:].decode().strip()
                if attempt == PASSKEY:
                    is_authenticated = True
                    read_char.notify(connection, b"AUTH_OK")
                    print("Access Granted")
                else:
                    read_char.notify(connection, b"AUTH_FAIL")
                    print("Invalid Passkey")
            else:
                read_char.notify(connection, b"ERR_LOCKED")
            continue

        # 2. Authenticated Commands (Only accessible after AUTH_OK)
        if data == CMD_FILE_START and not is_transferring:  # Prevent multiple simultaneous transfers
            is_transferring = True
            print("Starting file transfer...")
            asyncio.create_task(send_file_task(connection))
            
        elif data == CMD_FILE_STOP: # This command can be sent during a transfer to stop it early
            print("Stopping file transfer...")
            is_transferring = False
            
        elif data == CMD_FILE_CLEAR: # Clear the log file (only if not currently transferring)
            try: os.remove(LOG_FILE)
            except: pass
            read_char.notify(connection, b"DELETED")
            print("Log file cleared")
            
        elif data == CMD_LOG_ENABLE:
            print("Enabling logging...")
            is_logging = True
            read_char.notify(connection, b"LOG:ON")
            
        elif data == CMD_LOG_DISABLE:
            print("Disabling logging...")
            is_logging = False
            read_char.notify(connection, b"LOG:OFF")
        elif data == CMD_STORAGE_INF:
            print("Sending storage info...")
            fs = os.statvfs('/')
            free = (fs[0] * fs[3]) // 1024
            read_char.notify(connection, f"FREE:{free}KB".encode())
            print(f"Reported {free}KB free storage")

        # 3. Data Logging (with space check)
        elif is_logging:
            fs = os.statvfs('/')
            if (fs[0] * fs[3]) > MIN_FREE_SPACE:
                with open(LOG_FILE, "a") as f:
                    f.write(data.decode())
            else:
                is_logging = False
                read_char.notify(connection, b"ERR:FULL")

async def main():
    global is_authenticated, is_transferring, is_logging
    while True:
        try:
            async with await aioble.advertise(250_000, name="mpy-logger", services=[_SERVICE_UUID]) as conn:
                print("New connection - Locked")
                is_authenticated = False # Force login on every connection
                is_transferring = False
                is_logging = False
                await handle_writes(conn)
        except Exception: pass

asyncio.run(main())
