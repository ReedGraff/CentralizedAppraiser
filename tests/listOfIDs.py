import pandas as pd

# local imports
import CentralizedAppraiser
from CentralizedAppraiser import GoogleClient

# initialize client
client = GoogleClient("") # API KEY

# Iterate through the placeIDs in the file and get the address infos
with open("placeIDs.txt", "r") as file:
    placeID = file.read()

df = pd.DataFrame(columns=["id", "error.status", "error.message", "propertyInfo.folio", "propertyInfo.subdivision", "propertyInfo.blk", "propertyInfo.lot", "propertyInfo.plat.book", "propertyInfo.plat.page", "owners.0.name", "owners.0.mailingAddresses.0.formattedAddress" ])

for line in placeID.split("\n"):
    if line:
        print("line: ", line)

        addressInfo, errorHandler = client.getByID(line) # ChIJbYEx-KsN3ogRPgtsV_hq0kg: Brevard. ChIJU_2RLn-h2YgRV1AjoNx__kg: broward. ChIJV5BVdnmx2YgR8_GX_kzbH-s: miamiDade
        if errorHandler["status"] == "error":
            df = pd.concat([pd.DataFrame([[line, errorHandler["status"], errorHandler["message"], None, None, None, None, None, None, None, None]], columns=df.columns), df], ignore_index=True)
            continue

        classPointer, errorHandler = CentralizedAppraiser.classByAddressInfo(addressInfo)
        if errorHandler["status"] == "error":
            df = pd.concat([pd.DataFrame([[line, errorHandler["status"], errorHandler["message"], None, None, None, None, None, None, None, None]], columns=df.columns), df], ignore_index=True)
            continue

        folio, errorHandler = classPointer.folioByAddressInfo(addressInfo) # should return the folio
        if errorHandler["status"] == "error":
            df = pd.concat([pd.DataFrame([[line, errorHandler["status"], errorHandler["message"], None, None, None, None, None, None, None, None]], columns=df.columns), df], ignore_index=True)
            continue
        
        appraiserInfo, errorHandler = classPointer.appraiserInfoByFolio(folio, client) # should return the folio
        if errorHandler["status"] == "error":
            df = pd.concat([pd.DataFrame([[line, errorHandler["status"], errorHandler["message"], folio, None, None, None, None, None, None, None]], columns=df.columns), df], ignore_index=True)
            continue

        appraiserInfo, errorHandler = appraiserInfo.get()
        if errorHandler["status"] == "error":
            df = pd.concat([pd.DataFrame([[line, errorHandler["status"], errorHandler["message"], folio, None, None, None, None, None, None, None]], columns=df.columns), df], ignore_index=True)
            continue

        df = pd.concat([pd.DataFrame([[line, errorHandler["status"], errorHandler["message"], folio, appraiserInfo["propertyInfo"]["subdivision"], appraiserInfo["propertyInfo"]["blk"], appraiserInfo["propertyInfo"]["lot"], appraiserInfo["propertyInfo"]["plat"]["book"], appraiserInfo["propertyInfo"]["plat"]["page"], appraiserInfo["owners"][0]["name"], appraiserInfo["owners"][0]["mailingAddresses"][0]["formattedAddress"]]], columns=df.columns), df], ignore_index=True)

df.to_csv("output.csv", index=False)