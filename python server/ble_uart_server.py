from bluezero import peripheral

# Standard Nordic UART UUIDs
UART_SERVICE = '6E400001-B5A3-F393-E0A9-E50E24DCCA9E'
RX_CHARACTERISTIC = '6E400002-B5A3-F393-E0A9-E50E24DCCA9E'
TX_CHARACTERISTIC = '6E400003-B5A3-F393-E0A9-E50E24DCCA9E'

def uart_received(value, options):
    print(f"Server received: {bytes(value).decode('utf-8')}")

# Setup the peripheral #adapter_address='XX:XX:XX:XX:XX:XX', use bluetoothctl to find your adapter address
uart_server = peripheral.Peripheral(adapter_address='08:71:90:71:EA:4D',
                                   local_name='Python-NUS-Server')
uart_server.add_service(srv_id=1, uuid=UART_SERVICE, primary=True)
uart_server.add_characteristic(srv_id=1, chr_id=1, uuid=RX_CHARACTERISTIC,
                               value=[], notifying=False, 
                               flags=['write', 'write-without-response'],
                               write_callback=uart_received)
# (Add TX characteristic similarly for sending data back).gt
uart_server.publish()
