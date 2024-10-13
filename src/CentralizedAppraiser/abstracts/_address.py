import json
from ._exceptions import TranslationInvalid
from schema import Schema, And, Use, Or, Optional



class AddressSchematic(object):
    """Passed from the counties"""
    
    def __init__(self, data: dict, translateStrategy) -> None:
        raise NotImplementedError

    def __str__(self):
        raise NotImplementedError
    
    def get(self) -> dict:
        """return the formatted data and an error message if the data is not valid"""
        raise NotImplementedError
    
    @classmethod
    def getSchema(cls) -> dict:
        """Return the schema for the class"""
        raise NotImplementedError



class AddressInfo(AddressSchematic):
    """Passed to the counties from the client"""
    
    def __init__(self, data: dict, translateStrategy) -> None:
        self.__data = data
        self.__formattedData = translateStrategy

    @classmethod
    def getSchema(cls) -> dict:
        return {
            "formattedAddress": And(str, len),
            "addressComponents": {
                "streetNumber": str,
                "street": str,
                "unit": str,
                "city": str,
                "county": str,
                "state": str,
                "country": str,
                "zip": str
            },
            Optional("geo"): {
                "lat": And(Use(float), lambda n: -90 <= n <= 90),
                "lng": And(Use(float), lambda n: -180 <= n <= 180)
            }
        }

    def __str__(self):
        return f"AddressInfo(data={self.__data})"
    
    def get(self) -> dict:
        schema = Schema(self.getSchema())
        formattedData = self.__formattedData(self.__data)
        if schema.is_valid(formattedData):
            return formattedData
        else:
            print(schema.validate(formattedData))
            raise TranslationInvalid(f"Internal Error. Data is not valid for AddressInfo: {formattedData}")



class AppraiserInfo(AddressSchematic):
    """Passed from the counties"""
    
    def __init__(self, data: dict, client, translateStrategy) -> None:
        self.__data = data
        self.__client = client
        self.__translateStrategy = translateStrategy

    @classmethod
    def getSchema(cls) -> dict:
        return {
            "locationInfo": dict,
            "assessments": [
                {
                    "assessedValue": And(int, lambda n: n >= 0),
                    "buildingValue": And(int, lambda n: n >= 0),
                    "landValue": And(int, lambda n: n >= 0),
                    "totalValue": And(int, lambda n: n >= 0),
                    "year": int
                },
            ],
            "propertyInfo": {
                "parentFolio": str,
                "legal": str,
                "use": str,
                "subdivision": Or(None, str),
                "blk": Or(None, int),
                "lot": Or(None, int),
                "lotSize": Or(None, int, float),
                "records": [
                    {
                        "type": str,
                        "book": int,
                        "page": int
                    }
                ]
            },
            "owners": [
                {
                    "name": And(str, len),
                    "mailingAddresses": [
                        AddressInfo.getSchema()
                    ]
                }
            ],
            Optional("unStructured"): dict
        }

    def __str__(self):
        return f"AppraiserInfo(data={self.__data})"
    
    def get(self) -> dict:
        schema = Schema(self.getSchema())
        formattedData = self.__translateStrategy(self.__data, self.__client)
        if schema.is_valid(formattedData):
            return formattedData
        else:
            print(schema.validate(formattedData))
            raise TranslationInvalid(f"Internal Error. Data is not valid for AppraiserInfo: {formattedData}")



class MongoInfo(AddressSchematic):
    """
    Should be globally standard. translateStrategy should be the same for all counties, and should not really change.
    
    This builds the base to geojson, which is {
        "type": "FeatureCollection",
        "name": "larger",
        "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },
        "features": mongoInfo.getSchema()
    }"""
    def __init__(self, data: dict, translateStrategy) -> None:
        raise NotImplementedError
        self.__data = data
        self.__formattedData = translateStrategy(data)

    @classmethod
    def getSchema(cls) -> dict:
        return {
            "_id": str,
            "type": str,
            "properties": {
                "uuid": str,
                "path": list[str],
                "apn": str,
                **AppraiserInfo.getSchema()
            },
            "geometry": {
                "type": str,
                "coordinates": list[list[list[float, float]]]
            }
        }

    def __str__(self):
        return f"MongoInfo(data={self.__data})"
    
    def get(self) -> dict:
        schema = Schema(self.getSchema())
        if schema.is_valid(self.__formattedData):
            return self.__formattedData
        else:
            print(schema.validate(self.__formattedData))
            raise TranslationInvalid(f"Internal Error. Data is not valid for MongoInfo: {self.__formattedData}")