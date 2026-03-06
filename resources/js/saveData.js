const formDataKey = "scoutData"

// import { load } from "protobufjs";
async function testprotobuf(raw_matchdata){
    console.log("testing protobuf")
    // Load the protobuf definition file

    root = await protobuf.load("resources/js/scouting_data.proto");

    console.log("protobuf loaded")
    // Obtain the message type
    const MatchDataMessage = root.lookupType("MatchData");
    const CompetitionDataSet = root.lookupType("CompetitionDataSet");

    const matchfields = MatchDataMessage.fieldsArray;
    // Convert raw match data (tab-separated values) into an array of objects (must match the protobuf definition)
    const matchdata = raw_matchdata.split("\n").filter(line => line.trim() !== "").map(line => line.split("\t"));
    console.log(matchdata);
    // Map the raw match data to protobuf messages
    const matches_as_message = matchdata.map((match, index) => {
        return MatchDataMessage.create(match.reduce((obj, field, i) => {
            obj[matchfields[i].name] = field;
            return obj;
        }, {}));
    });

    console.log(matches_as_message);

    // Build competition data set and encode it
    const competitionDataSetMessage = CompetitionDataSet.create({ matches: matches_as_message });
    const competitionDataSetBuffer = CompetitionDataSet.encode(competitionDataSetMessage).finish();

    console.log("Encoded competition data set message:", competitionDataSetBuffer);

    // Example of decoding to verify correctness (can be removed later)
    const decodedMessage = CompetitionDataSet.decode(competitionDataSetBuffer);
    console.log("Decoded message:", decodedMessage);

    // return the raw Uint8Array so callers can wrap it in a Blob if desired
    return competitionDataSetBuffer;
}

function saveLocalData(){

    // uses the local storage to save the data from the form.  The data is saved into "scoutData" in the local storage.
    // Each entry is separated by a newline character to create a CTV file.  

    document.getElementsByClassName("savebutton")[0].disabled = true
    console.log('save data called')
    mydata = getData(dataFormat);
    // mydata = getData("kvs");
    console.log(mydata)
    laststore = localStorage.getItem(formDataKey) || ""

    localStorage.setItem(formDataKey, laststore + mydata + "\n")
}

// `useProto` parameter can be used to have the function run the
// `testprotobuf()` converter instead of sending raw TSV text.  It is
// async because protobuf loading is async.
async function exportBT(useProto = false){
    const localStorageData = localStorage.getItem(formDataKey) || "";
    let blob;

    if (useProto && typeof testprotobuf === 'function') {
        try {
            const protoBytes = await testprotobuf(localStorageData);
            blob = new Blob([protoBytes], { type: "application/octet-stream" });
        } catch (err) {
            console.error('protobuf conversion failed:', err);
            // fall back to plain text
            blob = new Blob([localStorageData], { type: "application/text" });
        }
    } else {
        blob = new Blob([localStorageData], { type: "application/text" });
    }

    if (window.BTHelpers && typeof window.BTHelpers.sendFile === 'function') {
        BTHelpers.sendFile(blob);
    } else {
        console.error('BTHelpers not available; cannot export via Bluetooth');
    }
}

function downloadLocalStorage() {
    // 1. Retrieve all data and format it as a human-readable JSON string
    //const localStorageData = JSON.stringify(localStorage, null, 4);
    const localStorageData = localStorage.getItem(formDataKey)

    // 2. Create a Blob object with the JSON data
    const blob = new Blob([localStorageData], { type: "application/text" });

    // 3. Generate a temporary URL for the Blob
    const url = URL.createObjectURL(blob);

    // 4. Create a link element to trigger the download
    const link = document.createElement("a");
    link.href = url;
    // Set the filename for the downloaded file
    link.download = "scout_data_export.csv";
    link.style.display = "none"; // Hide the link

    // Append link to body, click it, and remove it
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // 5. Clean up the temporary object URL
    URL.revokeObjectURL(url);
    localStorage.removeItem("scoutData")
}
