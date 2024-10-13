import json

from pymongo import MongoClient
from pymongo.server_api import ServerApi
import CentralizedAppraiser
import CentralizedAppraiser.UnitedStates
import CentralizedAppraiser.UnitedStates.Florida
import CentralizedAppraiser.UnitedStates.Florida.Broward
import CentralizedAppraiser.UnitedStates.Florida.MiamiDade
from CentralizedAppraiser.abstracts._proxy import CustomRotating, Proxy
from CentralizedAppraiser.abstracts._client import USAReverseClient


import asyncio
import requests
import logging

""" Generate all properties """
# Set up proxy server
with open("credentials.txt", "r") as f:
    username, password, proxy = f.read().split("\n")
proxy_auth = "{}:{}@{}".format(username, password, proxy)
customProxy = Proxy(url="http://{}".format(proxy_auth))
usaReverseClient = USAReverseClient()

with open("creds.txt", "r") as f:
    u, p, a = f.read().split("\n")
mongoClientCreds = {
    "u": u,
    "p": p,
    "a": a
}

countyObj = CentralizedAppraiser.UnitedStates.Florida.Broward.Broward(
    addressClient=usaReverseClient,
    proxy=customProxy,
    mongoClientCreds = mongoClientCreds,
    maxConcurrent=100
)
# out = asyncio.run(countyObj.generate())
# out = print(asyncio.run(countyObj.appraiserInfoByFolio("494222082380")))

'''
# upload all data
async def testin():
    gridDict = json.load(open("C:/Users/range/CodingProjects/RGBZ/Aeri4l/AllofPermitFly/CentralizedAppraiser/src/CentralizedAppraiser/UnitedStates/Florida/Broward/_data/_grids.json", "r"))

    # Connect to MongoDB once
    uri = f"mongodb+srv://ReedG:2xWgqq4Zf6IdnWUZ@centralizedappraiser.i0rek.mongodb.net/?retryWrites=true&w=majority&appName=CentralizedAppraiser"
    # Create a new client and connect to the server
    client = MongoClient(uri, server_api=ServerApi('1'))

    # Limit concurrency with a semaphore
    semaphore = asyncio.Semaphore(500)

    async def upload_with_semaphore(grid_obj, index):
        async with semaphore:
            await countyObj.uploadGridFiles(grid_obj, index, client)

    tasks = [upload_with_semaphore(gridObj, index) for index, gridObj in enumerate(gridDict)]
    await asyncio.gather(*tasks)

asyncio.run(testin())
'''
# json.dump(asyncio.run(testin()), open("C:/Users/range/CodingProjects/RGBZ/Aeri4l/AllofPermitFly/CentralizedAppraiser/src/CentralizedAppraiser/UnitedStates/Florida/MiamiDade/_data/_grids_cleaned.json", "w"), indent=4)

# def stream_geojson_to_file(data, filename):
#     def write_features(f, features):
#         for i, feature in enumerate(features):
#             f.write(json.dumps(feature))
#             if i < len(features) - 1:
#                 f.write(',\n')
#             else:
#                 f.write('\n')

#     with open(filename, 'w') as f:
#         f.write('{\n"type": "FeatureCollection",\n"features": [\n')
#         write_features(f, data['features'])
#         f.write(']\n}')

# stream_geojson_to_file(out.to_geo_dict(), "out.geojson")
# out.to_file("out.kml", driver="KML")

# out = CentralizedAppraiser.generateAllAtPath("UnitedStates.Florida.MiamiDade", addressClient=usaReverseClient, proxy=proxy)
# print(out)
""" Upload all properties """
#

""" Query all properties """
# mongoClientCreds = {
#     "u": "ReedG",
#     "p": "97eJPbuphnqRsIMl",
#     "a": "ServerlessInstance0"
# }
# query = { # https://www.mongodb.com/docs/atlas/atlas-search/text/#text
#   "$search": {
#     "index": '<index name>, // optional, defaults to "default"',
#     "text": {
#       "query": "<search-string>",
#       "path": "<field-to-search>",
#       "fuzzy": '<options>',
#       "score": '<options>',
#       "synonyms": "<synonyms-mapping-name>"
#     }
#   }
# }
# {
#     "properties.owners.name": {
#         "$regex": owner_name,
#         "$options": "i"  # Case-insensitive search
#     }
# }
# {"apn": "0131120140300"}
# {"properties.apn": "0131120140300"}
# print(CentralizedAppraiser.requestQueryAtPath(mongoClientCreds, {"$text": {"$search": "123 main"}}, "UnitedStates.Florida.Broward"))
# print(CentralizedAppraiser.typeahead(mongoClientCreds, "123 Main St.", "UnitedStates.Florida.Broward"))
# {"properties.locationInfo.formattedAddress":{ $regex: "^123 Main St", $options: "i" }}
