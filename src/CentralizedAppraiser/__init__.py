import importlib
import re

# local imports
from .utils import getLocationDetailsRecursive, getSubClassPath
from .abstracts import Country, AddressInfo, AppraiserInfo

# Localize:
from .abstracts._client import *



def pathByAddressInfo(addressInfo:AddressInfo) -> set[list, dict]:
    """return the most nested class that the placeID is in, and an error message if the most nested class is not found"""
    locationData, error = addressInfo.get()
    if error["status"] == "error":
        return None, error
    else:
        path, error = getLocationDetailsRecursive(locationData["geo"]["lng"], locationData["geo"]["lat"])

        if error["status"] == "error":
            return None, error
        else:
            return path, error



def classByPath(path:list) -> set[Country, dict]:
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

    return my_class, {"status": "success", "message": ""}



def classByAddressInfo(addressInfo:AddressInfo) -> set[Country, dict]:
    """return the class by the address info"""
    path, error = pathByAddressInfo(addressInfo)
    if error["status"] == "error":
        return None, error
    else:
        return classByPath(path)



def appraiserInfoByAddressInfo(addressInfo:AddressInfo, client:Client) -> set[AppraiserInfo, dict]:
    """return the appraiser info by the address info"""
    locationClass, error = classByAddressInfo(addressInfo)
    if error["status"] == "error":
        return None, error
    else:
        return locationClass.appraiserInfoByAddressInfo(addressInfo, client)
'''
from ijson.common import JSONError, IncompleteJSONError, ObjectBuilder

from ijson.utils import coroutine, sendable_list
from .version import __version__

def get_backend(backend):
    """Import the backend named ``backend``"""
    import importlib
    return importlib.import_module('ijson.backends.' + backend)

def _default_backend():
    import os
    if 'IJSON_BACKEND' in os.environ:
        return get_backend(os.environ['IJSON_BACKEND'])
    for backend in ('yajl2_c', 'yajl2_cffi', 'yajl2', 'yajl', 'python'):
        try:
            return get_backend(backend)
        except ImportError:
            continue
    raise ImportError('no backends available')
backend = _default_backend()
del _default_backend

basic_parse = backend.basic_parse
basic_parse_coro = backend.basic_parse_coro
parse = backend.parse
parse_coro = backend.parse_coro
items = backend.items
items_coro = backend.items_coro
kvitems = backend.kvitems
kvitems_coro = backend.kvitems_coro
basic_parse_async = backend.basic_parse_async
parse_async = backend.parse_async
items_async = backend.items_async
kvitems_async = backend.kvitems_async
backend = backend.backend
'''