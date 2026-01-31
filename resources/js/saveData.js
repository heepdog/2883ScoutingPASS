function saveLocalData(){
    console.log('save data called')
    mydata = getData(dataFormat);
    console.log(mydata)

    if (Object.is(laststore,null)){
        laststore = ""
    }
    else{
        laststore = localStorage.getItem("scoutData")
    }

    localStorage.setItem("scoutData", laststore + "\n" + mydata)


}