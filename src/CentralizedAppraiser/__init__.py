import importlib
import json
import uuid
import motor.motor_asyncio
import geopandas as gpd
import re
import pkgutil

import pymongo

from CentralizedAppraiser.abstracts._address import MongoInfo

# local imports
from .utils import get_all_modules, getSubClassPath, interleave_lists
from .abstracts import Country, AddressInfo, AppraiserInfo
from .abstracts._exceptions import *

# Localize:
from .abstracts._client import *



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
# Generate Data Locally
# ==================================================================================================
async def generateAtPath(path: str, addressClient: Client) -> None:
    """Generates a new document in the database at the specified path"""
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
    gdf.to_file(f"CentralizedAppraiser/{path.replace('.', '/')}/_data/data.kml", driver='KML')
    with open(f"CentralizedAppraiser/{path.replace('.', '/')}/_data/data.json", "w") as file:
        json.dump(gdf.to_geo_dict(), file, indent=4)

def generateAllAtPath(path: str, addressClient: Client) -> None:
    nestedModules = get_all_modules(path)

    # Connect to MongoDB
    for modulePath in nestedModules:
        generateAtPath(modulePath, addressClient)

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