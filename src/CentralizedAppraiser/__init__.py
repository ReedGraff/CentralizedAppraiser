import importlib
import json
import os
import uuid
# import motor.motor_asyncio
import geopandas as gpd
import asyncio
# import pymongo
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)


from CentralizedAppraiser.abstracts._address import MongoInfo

# local imports
from .utils import get_all_modules, getSubClassPath, interleave_lists
from .abstracts import Country, AddressInfo, AppraiserInfo
from .abstracts._exceptions import *

# Localize:
from .abstracts._client import *



# ==================================================================================================
# Generate Data Locally
# ==================================================================================================
async def generateAtPath(path: str, addressClient: Client) -> list: # Blocking
    """Generates a new document in the database for the specified path"""
    modulePathList = path.split(".")
    classObj = classByPath(modulePathList)

    gdf:gpd.GeoDataFrame = await classObj.generate(addressClient)

    # Ensure 'uuid' and 'path' columns exist
    if 'uuid' not in gdf.columns:
        gdf['uuid'] = None
    if 'path' not in gdf.columns:
        gdf['path'] = None

    # Function to generate new column values
    for index, row in gdf.iterrows():
        gdf.at[index, 'uuid'] = str(uuid.uuid4())
        gdf.at[index, 'path'] = modulePathList

    # Change the projection
    gdf.set_crs(epsg=2236, inplace=True, allow_override=True)
    gdf.to_crs(epsg=4326, inplace=True)

    # Save data to the _data folder
    __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__), ""))
    gdf.to_file(os.path.join(__location__, *modulePathList, 'data.kml'), driver='KML')
    # gdf.to_json(os.path.join(__location__, *modulePathList, 'data.json'), driver='GeoJSON')
    with open(os.path.join(__location__, *modulePathList, 'data.json'), "w") as f:
        json.dump(gdf.to_geo_dict(), f, indent=4)

    return [
        f"CentralizedAppraiser/{path.replace('.', '/')}/_data/data.kml",
        f"CentralizedAppraiser/{path.replace('.', '/')}/_data/data.json"
    ]

async def generateAllAtPath(path: str, addressClient: Client) -> dict: # Non Blocking
    nestedModules = get_all_modules(path)
    tasks = []

    for modulePath in nestedModules:
        task = asyncio.create_task(generateAtPath(modulePath, addressClient))
        tasks.append(task)
    res = await asyncio.gather(*tasks)

    # convert to a dictionary for easier access
    output = {}
    for index, vals in enumerate(res):
        output.update({nestedModules[index]: vals})

    return output

# ==================================================================================================
# Sync Data With MongoDB
# ==================================================================================================
def syncAtPath(mongoClientCreds: dict, path: str) -> dict:
    """Generates a new document in the database at the specified path"""
    modulePathList = path.split(".")
    modulePathList = ["geoDB", "geoCollection"]
    
    # Load GeoJSON data from a file
    with open('larger.json', 'r') as file:
        geojson_data = json.load(file)

    print("Running makeMongoDB")
    # Connect to MongoDB
    client = pymongo.MongoClient('mongodb+srv://ReedG:97eJPbuphnqRsIMl@serverlessinstance0.mos4bob.mongodb.net/?retryWrites=true&w=majority&appName=ServerlessInstance0')
    db = client['geoDB']
    collection = db['geoCollection']

    # Create a unique index on the FOLIO field
    collection.create_index("FOLIO", unique=True)

    # Insert GeoJSON data into MongoDB
    def insert_geojson_to_mongo(geojson_data, collection, batch_size=1000):
        if geojson_data['type'] == 'FeatureCollection':
            features = geojson_data['features']
            operations = []
            for feature in features:
                operations.append(
                    pymongo.UpdateOne(
                        {"FOLIO": feature["properties"]["FOLIO"]},
                        {"$set": feature},
                        upsert=True
                    )
                )
                if len(operations) == batch_size:
                    collection.bulk_write(operations)
                    operations = []
            if operations:
                collection.bulk_write(operations)
        else:
            raise ValueError("Invalid GeoJSON format")

    # Insert the data
    insert_geojson_to_mongo(geojson_data, collection)


def makeMongoDB(mongoClientCreds: dict, path: str):
    print("GeoJSON data has been inserted into MongoDB.")



# ==================================================================================================
# Request Data
# ==================================================================================================
async def requestQueryAtPath(mongoClientCreds: dict, query: dict, path: str) -> dict:
    """Finds all addresses that match the unformatted address which are at a specific path"""
    modulePathList = path.split(".")
    modulePathList = ["geoDB", "geoCollection"]

    client = motor.motor_asyncio.AsyncIOMotorClient(f'mongodb+srv://{mongoClientCreds["u"]}:{mongoClientCreds["p"]}@serverlessinstance0.mos4bob.mongodb.net/?retryWrites=true&w=majority&appName={mongoClientCreds["a"]}')
    db = client["+".join(modulePathList[0:-1])]  # UnitedStates+Florida
    collection = db[modulePathList[-1]]  # Broward

    # Retrieve data from MongoDB
    cursor = collection.find(query)
    results = await cursor.to_list(length=None)
    return results

async def requestAllAtPath(mongoClientCreds: dict, query: dict, path: str) -> list[dict]:
    """Finds all addresses that match the unformatted address which are within the path"""
    nestedModules = get_all_modules(path)
    nestedModules = ["geoDB.geoCollection"]

    potentialAddresses = []

    # Connect to MongoDB
    for modulePath in nestedModules:
        results = await requestQueryAtPath(mongoClientCreds, query, modulePath)
        potentialAddresses.append(results)

    return interleave_lists(potentialAddresses)



# ==================================================================================================
# Generate & Sync Data
# ==================================================================================================
def generateAndSync(mongoClientCreds: dict, path: str):
    generateAtPath(mongoClientCreds, path)
    syncAtPath(mongoClientCreds, path)



# ==================================================================================================
# Other Helper Functions
# ==================================================================================================
def classByPath(path:list) -> Country:
    """return the class by the path"""
    # Import the module and return the class
    try:
        subclassPath = getSubClassPath(path)
        module = importlib.import_module(subclassPath)
        my_class = getattr(module, path[-1])

    except Exception as _:
        subclassPath = getSubClassPath(path)
        module = importlib.import_module(subclassPath)
        my_class = getattr(module, path[-2])

    return my_class