import importlib
import re
import os
import json
from shapely.geometry import shape, Point

from typing import get_type_hints

def strict_types(f):
    def type_checker(*args, **kwargs):
        hints = get_type_hints(f)

        all_args = kwargs.copy()
        all_args.update(dict(zip(f.__code__.co_varnames, args)))

        for key in all_args:
            if key in hints:
                if type(all_args[key]) != hints[key]:
                    raise Exception('Type of {} is {} and not {}'.format(key, type(all_args[key]), hints[key]))

        return f(*args, **kwargs)

    return type_checker

def getLocationDetailsRecursive(lon, lat, levelList = ["UnitedStates"], definingKey = "NAME") -> set[list, dict]:
    """
    Recursively returns the location details of the given latitude and longitude.
    """
    startingPoint = Point(lon, lat)

    try:
        # with open(f'{getSubClassPath(levelList, delim="/")}/geometry.geojson') as geo:
        #     geometry = json.load(geo)
        with importlib.resources.open_text(f"{getSubClassPath(levelList, delim=".")}", "geometry.geojson") as file:
            geometry = json.load(file)
    except FileNotFoundError:
        # happens when the final location is reached and it isn't a parent folder
        return levelList, {"status": "success", "message": ""}

    for feature in geometry['features']:
        polygon = shape(feature['geometry'])

        if polygon.contains(startingPoint):
            # print(feature['properties']["NAME"])
            try:
                modulePath = getSubClassPath(levelList) + "." + re.sub(r'\W+','', feature['properties'][definingKey])
                module = importlib.import_module(modulePath)
                my_class = getattr(module, re.sub(r'\W+','', feature['properties'][definingKey]))
                levelList.append(feature['properties'][definingKey])

                # new defining key
                definingKey = my_class.getDefiningGeometryKey()
                levelList, error = getLocationDetailsRecursive(lon, lat, levelList, definingKey)

                return levelList, error
            
            except ModuleNotFoundError:
                return levelList, {"status": "error", "message": f"We currently do not offer {feature['properties'][definingKey]}"}
    
    # if the location is not found
    return levelList, {"status": "error", "message": f"We currently do not offer {feature['properties'][definingKey]}"}

# def _getNextLevel(location:list, path:str):


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

# Helper function to convert string values to integers
def convert_to_int(value):
    if isinstance(value, int):
        return value
    try:
        return int(value.replace(',', '').replace('$', ''))
    except (ValueError, AttributeError):
        return 0