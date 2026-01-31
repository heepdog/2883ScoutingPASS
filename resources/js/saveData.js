function saveLocalData(){
    console.log('save data called')
    mydata = getData(dataFormat);
    console.log(mydata)
    laststore = localStorage.getItem("scoutData")
    localStorage.setItem("scoutData", laststoreore + "\n" + mydata)
    

}