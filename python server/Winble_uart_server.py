import time
from bleson import get_adapter, Advertiser, Service, Characteristic
from bleson.uuids import UUID128

# Nordic UART UUIDs
UART_SERVICE_UUID = UUID128("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
RX_CHAR_UUID      = UUID128("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")

def on_rx_write(value):
    print(f"Data received from WebBluetooth: {value.decode('utf-8')}")

def start_server():
    adapter = get_adapter()
    
    # Define the Service
    nus_service = Service(UART_SERVICE_UUID)
    
    # Define the RX Characteristic (Write)
    rx_char = Characteristic(RX_CHAR_UUID, on_write=on_rx_write)
    nus_service.add_characteristic(rx_char)
    
    # Start Advertising
    advertiser = Advertiser(adapter)
    advertiser.name = "Windows-UART-Server"
    advertiser.add_service(nus_service)
    
    print("Starting advertisement... Connect via WebBluetooth now.")
    advertiser.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        advertiser.stop()

if __name__ == "__main__":
    start_server()
