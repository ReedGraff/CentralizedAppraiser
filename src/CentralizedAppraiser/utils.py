import importlib
import re
import os
import json
import inspect
import pkgutil
import numpy as np
from pymongo import UpdateOne
from pyproj import CRS, Transformer
from shapely import Polygon
from shapely.geometry import shape, Point

from .abstracts._location import Country


def getSubClassPath(location:list, startingPath='CentralizedAppraiser', delim=".") -> str:
    """
    Helper function to get the path to the subclass of the location.
    """

    searchPath = startingPath + delim

    for locationPath in location:
        # print(locationPath)
        searchPath += locationPath + delim

    # Remove the trailing '.'
    searchPath = searchPath.rstrip(delim)
    return searchPath

def extends_county(module):
    """Check if the module extends the County class."""
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, Country.State.County):
            return True
    return False

def get_all_modules(path: str):
    """Recursively get all module paths that extend County or their submodules."""
    module = importlib.import_module(f"CentralizedAppraiser.{path}")
    
    if extends_county(module):
        return [path]
    
    nested_modules = [name for _, name, _ in pkgutil.iter_modules(module.__path__)]

    result_modules = []
    for nested_module in nested_modules:
        sub_module_path = f"{path}.{nested_module}"
        sub_module = importlib.import_module(f"CentralizedAppraiser.{sub_module_path}")
        if extends_county(sub_module):
            result_modules.append(sub_module_path)
        else:
            result_modules.extend(get_all_modules(sub_module_path))

    return result_modules

# Helper function to convert string values to integers
def convert_to_int(value):
    if isinstance(value, int):
        return value
    try:
        return int(value.replace(',', '').replace('$', ''))
    except (ValueError, AttributeError):
        return 0

# =================================================================================================
# Geometry Helper Functions
# =================================================================================================
def esri_to_geojson(esri_json):
    features = []
    for feature in esri_json.get("features", []):
        geometry = feature["geometry"]
        if geometry and "rings" in geometry:
            # Convert Esri rings to GeoJSON-like coordinates
            coordinates = geometry["rings"]
            geojson_geometry = {
                "type": "Polygon",
                "coordinates": coordinates
            }
            features.append({
                "type": "Feature",
                "geometry": geojson_geometry,
                "properties": feature["attributes"]
            })
    return {
        "type": "FeatureCollection",
        "features": features
    }

def project_coordinates(longitude, latitude, spatial_reference_system):
    # Define the projection for WGS84 (latitude and longitude)
    wgs84 = CRS.from_epsg(4326)

    # Define the projection for the target spatial reference system
    target_proj = CRS.from_epsg(spatial_reference_system)

    # Transform the coordinates
    transformer = Transformer.from_crs(wgs84, target_proj, always_xy=True)
    x, y = transformer.transform(longitude, latitude)

    return x, y

def make_grid(shape, granularity):
    """
    Returns a list of tuples [((lat, lng), (lat, lng)), ((lat, lng), (lat, lng))] that represents (swLat, swLng), (neLat, neLng) for each grid square.
    """
    min_lng, min_lat, max_lng, max_lat = shape.bounds
    print("Shape bounds: ", min_lng, min_lat, max_lng, max_lat)
    granularityDeg = meters_to_degrees(granularity)
    print("Granularity in degrees: ", granularityDeg)

    # Add buffers to the bounds
    if ((min_lng - max_lng) % granularityDeg != 0):
        offset = (min_lng - max_lng) % granularityDeg
        min_lng = min_lng - offset / 2
        max_lng = max_lng + offset / 2
    if ((min_lat - max_lat) % granularityDeg != 0):
        offset = (min_lat - max_lat) % granularityDeg
        min_lat = min_lat - offset / 2
        max_lat = max_lat + offset / 2

    print("Shape bounds with buffer: ", min_lng, min_lat, max_lng, max_lat)

    # Create the grid
    results = []
    for horizontalRow in np.arange(min_lng, max_lng, granularityDeg):
        for verticalCell in np.arange(min_lat, max_lat, granularityDeg):
            sw = (verticalCell, horizontalRow)
            ne = (verticalCell + granularityDeg, horizontalRow + granularityDeg)

            box = Polygon([(sw[1], sw[0]), (ne[1], sw[0]), (ne[1], ne[0]), (sw[1], ne[0])])
            if shape.intersects(box):
                results.append((sw, ne))
    
    print("Number of grid squares: ", len(results))
    return results

def meters_to_degrees(meters):
    return meters / 111_111
    # new_latitude  = latitude  + (dy / r_earth) * (180 / pi);
    # new_longitude = longitude + (dx / r_earth) * (180 / pi) / cos(latitude * pi/180);











def interleave_lists(*lists):
    newlist = []
    max_length = max(len(lst) for lst in lists)

    for i in range(max_length):
        for lst in lists:
            if i < len(lst):
                newlist.append(lst[i])

    return newlist

def makeMongoDB(mongoClient):
    # Load GeoJSON data from a file
    with open('larger.json', 'r') as file:
        geojson_data = json.load(file)

    print("Running makeMongoDB")
    # Connect to MongoDB
    db = mongoClient['geoDB']
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

def load_from_mongo(mongoClient, query={}):
    # Connect to MongoDB
    db = mongoClient['geoDB']
    collection = db['geoCollection']

    # Retrieve data from MongoDB
    results = collection.find(query)
    return list(results)