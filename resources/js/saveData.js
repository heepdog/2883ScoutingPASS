function saveLocalData(){
    
    document.getElementsByClassName("savebutton")[0].disabled = true
    console.log('save data called')
    mydata = getData(dataFormat);
    // mydata = getData("kvs");
    console.log(mydata)
    laststore = localStorage.getItem("scoutData")


    if (Object.is(laststore,null)){
        laststore = ""
    }
    localStorage.setItem("scoutData", laststore + mydata + "\n")


}

function exportBT(){
    // Example UUIDs (Use your device's specific UUIDs)
    const FILE_SERVICE_UUID = '6e400001-b5a3-f393-e0a9-e50e24dcca9e'; // Example: Nordic UART Service
    const FILE_TX_CHARACTERISTIC = '6e400002-b5a3-f393-e0a9-e50e24dcca9e';

    async function sendFile(file) {
        const device = await navigator.bluetooth.requestDevice({
            filters: [{ services: [FILE_SERVICE_UUID] }]
        });
        const server = await device.gatt.connect();
        const service = await server.getPrimaryService(FILE_SERVICE_UUID);
        const characteristic = await service.getCharacteristic(FILE_TX_CHARACTERISTIC);

        const arrayBuffer = await file.arrayBuffer();
        const bytes = new Uint8Array(arrayBuffer);
        const CHUNK_SIZE = 20; // Standard BLE safe chunk size

        for (let i = 0; i < bytes.length; i += CHUNK_SIZE) {
            const chunk = bytes.slice(i, i + CHUNK_SIZE);
            await characteristic.writeValue(chunk); // Send sequentially
            console.log(`Sent ${Math.min(i + CHUNK_SIZE, bytes.length)} of ${bytes.length} bytes`);
        }
        server.disconnect();
    }

    // Get the scouting data and send it
    const localStorageData = localStorage.getItem("scoutData") || "";
    const blob = new Blob([localStorageData], { type: "application/text" });
    sendFile(blob);
}

function downloadLocalStorage() {
    // 1. Retrieve all data and format it as a human-readable JSON string
    //const localStorageData = JSON.stringify(localStorage, null, 4);
    const localStorageData = localStorage.getItem("scoutData")

    // 2. Create a Blob object with the JSON data
    const blob = new Blob([localStorageData], { type: "application/text" });

    // 3. Generate a temporary URL for the Blob
    const url = URL.createObjectURL(blob);

    // 4. Create a link element to trigger the download
    const link = document.createElement("a");
    link.href = url;
    // Set the filename for the downloaded file
    link.download = "localStorage_export.csv";
    link.style.display = "none"; // Hide the link

    // Append link to body, click it, and remove it
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // 5. Clean up the temporary object URL
    URL.revokeObjectURL(url);
    localStorage.removeItem("scoutData")
}
