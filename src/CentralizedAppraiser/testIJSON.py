# pip install ijson

import json
import ijson
import timeit
import re

import json
from pymongo import MongoClient, UpdateOne
from collections import defaultdict


def loadFL():
    # 3.39390529999946s
    with open('larger.json', 'r') as f:

        objects = ijson.items(f, 'features.item')
        florida = (o["properties"]["FOLIO"] for o in objects if o["properties"]["FOLIO"] == '474129055160')

        print(next(florida))
        pass

def loadFL2():
    # 14.870992199998s
    with open('larger.json', 'r') as f:
        parser = ijson.parse(f)
        for prefix, event, value in parser:
            if prefix == 'features.item.properties.FOLIO' and value == '474129055160':
                print(value)
                pass

def loadFL3():
    # 7.34505160000117s
    dictJson = json.load(open('larger.json', 'r'))
    for feature in dictJson['features']:
        if feature['properties']['FOLIO'] == '474129055160':
            print(feature['properties']['FOLIO'])
            pass


def makeMongoDB():
    # Load GeoJSON data from a file
    with open('larger.json', 'r') as file:
        geojson_data = json.load(file)

    print("Running makeMongoDB")
    # Connect to MongoDB
    client = MongoClient('mongodb+srv://ReedG:97eJPbuphnqRsIMl@serverlessinstance0.mos4bob.mongodb.net/?retryWrites=true&w=majority&appName=ServerlessInstance0')
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
                    UpdateOne(
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
    
    print("GeoJSON data has been inserted into MongoDB.")

def load_from_mongo(query={}):
    # Connect to MongoDB
    client = MongoClient('mongodb+srv://ReedG:97eJPbuphnqRsIMl@serverlessinstance0.mos4bob.mongodb.net/?retryWrites=true&w=majority&appName=ServerlessInstance0')
    db = client['geoDB']
    collection = db['geoCollection']

    # Retrieve data from MongoDB
    results = collection.find(query)
    return list(results)

def remove_duplicates():
    # Connect to MongoDB
    client = MongoClient('mongodb+srv://ReedG:97eJPbuphnqRsIMl@serverlessinstance0.mos4bob.mongodb.net/?retryWrites=true&w=majority&appName=ServerlessInstance0')
    db = client['geoDB']
    collection = db['geoCollection']

    # Retrieve all documents
    all_documents = list(collection.find({}))

    # Dictionary to track unique FOLIOs and their corresponding document IDs
    folio_dict = defaultdict(list)

    # Populate the dictionary with FOLIOs and their document IDs
    for doc in all_documents:
        folio = doc['properties']['FOLIO']
        folio_dict[folio].append(doc['_id'])

    # Identify and delete duplicates
    for folio, ids in folio_dict.items():
        if len(ids) > 1:
            # Keep the first document and delete the rest
            collection.delete_many({'_id': {'$in': ids[1:]}})
            print(f"deleted {len(ids) - 1} duplicates for FOLIO {folio}")

    print("Duplicate FOLIOs have been removed.")

if __name__ == '__main__':
    # print(timeit.timeit(loadFL, number=10))
    # print(timeit.timeit(loadFL2, number=10))
    # print(timeit.timeit(loadFL3, number=10))

    # makeMongoDB()
    remove_duplicates()

    # # Example usage of loading data from MongoDB
    # print(timeit.timeit(lambda: load_from_mongo({"properties.FOLIO": "474129055160"}), number=10)) # this will automatically make idexes when needed.
    
    """
    # Create a regex pattern to match entries that start with the prefix
    prefix = "4741290551"
    regex_pattern = f'^{re.escape(prefix)}'
    query = {"properties.FOLIO": {"$regex": regex_pattern}}

    print(len(load_from_mongo(query)))
    """

