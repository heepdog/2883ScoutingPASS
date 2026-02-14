
"""
Example for a BLE 4.0 Server
"""

import sys
import logging
import asyncio
import threading
import signal
import argparse
import csv
import datetime

# Path to append received data to (can be overridden by CLI)
output_file: str = "scouting_data.tsv"

from typing import Any, Union

from bless import (  # type: ignore
    BlessServer,
    BlessGATTCharacteristic,
    GATTCharacteristicProperties,
    GATTAttributePermissions,
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=__name__)

# NOTE: Some systems require different synchronization methods.
trigger: Union[asyncio.Event, threading.Event]
if sys.platform in ["darwin", "win32"]:
    trigger = threading.Event()
else:
    trigger = asyncio.Event()


def read_request(characteristic: BlessGATTCharacteristic, **kwargs) -> bytearray:
    logger.debug(f"Reading {characteristic.value}")
    return characteristic.value


def write_request(characteristic: BlessGATTCharacteristic, value: Any, **kwargs):
    characteristic.value = value
    logger.debug(f"Char value set to {characteristic.value}")
    # Persist received data to TSV: timestamp, characteristic id (if available), value (string)
    try:
        # v_str = characteristic.value
        # char_id = getattr(characteristic, "uuid", "") or getattr(characteristic, "_uuid", "")
        # ts = datetime.datetime.utcnow().isoformat()
        with open(output_file, "a", newline="") as f:
            f.write(characteristic.value.decode("utf-8"))
            # writer = csv.writer(f, delimiter="\t")
            # writer.writerow([ts, char_id, v_str])
    except Exception:
        logger.exception("Failed to write received data to file")

    # original behavior: set trigger on special value
    if characteristic.value == b"\x0f":
        logger.debug("NICE")
        trigger.set()
        
def exit_program():
    logger.info("Exiting program")
    trigger.set()

async def run(service_name: str = "2883 Scouting Service"):
    trigger.clear()
    # connect system signals to trigger the server to stop when the process is killed
    for sig in ["SIGINT", "SIGTERM"]:
        if hasattr(signal, sig):
            # signal.signal(getattr(signal, sig), lambda *_: trigger.set())
            signal.signal(getattr(signal, sig), lambda *_: exit_program())
    
    # Instantiate the server
    loop = asyncio.get_event_loop()
    server = BlessServer(name=service_name, loop=loop)
    server.read_request_func = read_request
    server.write_request_func = write_request

    # Add Service
    my_service_uuid = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E" # UART Service
    # my_service_uuid = "A07498CA-AD5B-474E-940D-16F1FBE7E8CD"
    await server.add_new_service(my_service_uuid)

    # Add a Characteristic to the service
    # my_char_uuid = "51FF12BB-3ED8-46E5-B4F9-D64E2FEC021B"
    my_char_uuid = '6E400002-B5A3-F393-E0A9-E50E24DCCA9E' # RX Characteristic
    char_flags = (
        GATTCharacteristicProperties.write
        | GATTCharacteristicProperties.read
        | GATTCharacteristicProperties.indicate
    )
    permissions = GATTAttributePermissions.readable | GATTAttributePermissions.writeable
    await server.add_new_characteristic(
        my_service_uuid, my_char_uuid, char_flags, None, permissions
    )

    logger.debug(server.get_characteristic(my_char_uuid))
    await server.start()
    logger.debug("Advertising")
    # logger.info(f"Write '0xF' to the advertised characteristic: {my_char_uuid}")
    logger.info(f"Listening for writes to the advertised characteristic: {my_char_uuid}")
    logger.info(f"Press Ctrl+C to stop the server\n")
    if trigger.__module__ == "threading":
        trigger.wait()
    else:
        await trigger.wait()

    # await asyncio.sleep(2)
    # logger.debug("Updating")
    # server.get_characteristic(my_char_uuid)
    # server.update_value(my_service_uuid, my_char_uuid)
    # server.update_value(my_service_uuid, "51FF12BB-3ED8-46E5-B4F9-D64E2FEC021B")
    # await asyncio.sleep(5)
    await server.stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BLE UART server")
    parser.add_argument(
        "--name",
        "-n",
        help="BLE service name to advertise",
        default="2883 Scouting Service",
    )
    parser.add_argument(
        "--file",
        "-f",
        help="Output TSV file to append received data",
        default="scouting_data.tsv",
    )
    args = parser.parse_args()

    # set module-level output file
    output_file = args.file

    print("Starting BLE Server")
    asyncio.run(run(service_name=args.name))
