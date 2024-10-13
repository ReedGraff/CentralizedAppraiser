from ...Florida import Florida

# Localized Imports
from .collect import Collect
from .generate import Generate
from ....abstracts import Proxy

# External Imports
import os
import asyncio

class MiamiDade(
    Collect, Generate,
    Florida.County, Florida, 
    ):
    """
    self.addressClient = kwargs.get("addressClient", None)  
    self.proxy = kwargs.get("proxy", None)  
    self.mongoClientCreds = kwargs.get("mongoClientCreds", None)  
    """
    def __init__(self, **kwargs):
        self.addressClient = kwargs.get("addressClient", None)
        self.proxy = kwargs.get("proxy", Proxy())
        self.mongoClientCreds = kwargs.get("mongoClientCreds", {
            "u": "",
            "p": "",
            "a": ""
        })
        self.semaphore = asyncio.Semaphore(kwargs.get("maxConcurrent", 50))
        self.__location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__))
        )

        # Initialize _data directory
        if not os.path.exists(os.path.join(self.__location__, "_data")):
            os.makedirs(os.path.join(self.__location__, "_data"))
        if not os.path.exists(os.path.join(self.__location__, "_data", "_grids")):
            os.makedirs(os.path.join(self.__location__, "_data", "_grids"))
        if not os.path.exists(os.path.join(self.__location__, "_data", "_appraisers")):
            os.makedirs(os.path.join(self.__location__, "_data", "_appraisers"))