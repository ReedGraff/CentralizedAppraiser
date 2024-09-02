import json
import pandas as pd
import CentralizedAppraiser
from CentralizedAppraiser import GoogleClient, RegridClient

from CentralizedAppraiser.UnitedStates.Florida.Broward import Broward

with open("creds.txt", "r") as f:
    googleApiKey = f.readline().strip()
    regridApiKey = f.readline().strip()

client = GoogleClient(googleApiKey) # API KEY
# client = RegridClient(regridApiKey) # API KEY
# addressInfo, errorHandler = client.getByID("5a3af608-4ad5-453f-95ad-533a53012d7e") # ChIJbYEx-KsN3ogRPgtsV_hq0kg: Brevard. ChIJU_2RLn-h2YgRV1AjoNx__kg: broward. ChIJV5BVdnmx2YgR8_GX_kzbH-s: miamiDade
addressInfo, errorHandler = client.getByAddress("3230 NW 14th Pl, fort lauderdale") # ChIJbYEx-KsN3ogRPgtsV_hq0kg: Brevard. ChIJU_2RLn-h2YgRV1AjoNx__kg: broward. ChIJV5BVdnmx2YgR8_GX_kzbH-s: miamiDade
classPointer, errorHandler = CentralizedAppraiser.classByAddressInfo(addressInfo)
folio, errorHandler = classPointer.folioByAddressInfo(addressInfo) # should return the folio
print(folio)
print(classPointer.getPropertyLinesByFolio(folio))

# appraiserInfo, errorHandler = CentralizedAppraiser.appraiserInfoByAddressInfo(addressInfo, client)
# addressInfo, errorHandler = addressInfo.get()
# folio, errorHandler = classPointer.folioByAddressInfo(addressInfo) # should return the folio
# appraiserInfo, errorHandler = classPointer.appraiserInfoByFolio(addressInfo["folio"], client)
# # json.dump(appraiserInfo.get(), open("output.json", "w"), indent=4) # should return the formatted data


# data = {}

# print(CentralizedAppraiser.AppraiserInfo(data, client, Broward.DELETEtranslate()).get()) # should return the formatted data

"""
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
"""

"""
# Iterate through the placeIDs in the file and get the address infos only if the address is in Miami-Dade
with open("placeIDs.txt", "r") as file:
    placeID = file.read()

for line in placeID.split("\n"):
    if line:
        addressInfo = client.getAddress(line)
        # appraiserInfo, error = CentralizedAppraiser.fromAddressInfoGetAppraiserInfo(addressInfo)  # TODO
        mostNestedClass, path, error = CentralizedAppraiser.fromAddressInfoGetClassAndPath(addressInfo)

        if "Broward" in path:
            mostNestedClass.getAddress(addressInfo) # TODO
            print(f"path: {str(path):>40} | error: {error:>30} \n")
"""

# addressInfo = client.getAddress("ChIJWXmrftjG2YgRWeptrcs7UK0") # ChIJEaMLdnmx2YgRBBrSX0X3sXY: 60. ChIJj61dQgK6j4AR4GeTYWZsKWw: google # ChIJWXmrftjG2YgRWeptrcs7UK0: 10301 SW 98th Ave

# # locationClass, error = CentralizedAppraiser.fromAddressInfoGetClass(addressInfo)
# # print(locationClass.getAddress(addressInfo)) # should return the formatted data

# appraiserInfo, error = CentralizedAppraiser.fromAddressInfoGetAppraiserInfo(addressInfo)

# # print(appraiserInfo, error)
