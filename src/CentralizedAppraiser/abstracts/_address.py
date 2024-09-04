import json
from ..utils import strict_types
from schema import Schema, And, Use, Or, Optional, SchemaError
# from schema import Schema, And, Use, Optional, SchemaError

class AddressSchematic(object):
    """Passed from the counties"""
    @strict_types
    def __init__(self, data:dict, translateStrategy) -> None:
        raise NotImplementedError

    def __str__(self):
        raise NotImplementedError
    
    def get(self) -> set[dict, dict]:
        """return the formatted data and an error message if the data is not valid"""
        raise NotImplementedError



# Address Info (IK this is not abstract)
class AddressInfo(AddressSchematic):
    """Passed to the counties from the client"""
    @strict_types
    def __init__(self, data:dict, translateStrategy) -> None:
        self.__data = data # this is the raw data from the appraiser
        self.__formattedData = translateStrategy(data) # this is the translated data into consistent format

        self.__schema = Schema(
            {
                "formattedAddress": And(str, len),
                "folio": Or(None, And(str, Use(len))),
                "addressComponents": {
                    "streetNumber": str,
                    "street": str,
                    "streetDirection": str,
                    "city": str,
                    "county": str,
                    "state": And(str, len),
                    "country": And(str, len),
                    "zip": And(str, len)
                },
                "geo": {
                    "lat": And(Use(float), lambda n: -90 <= n <= 90),
                    "lng": And(Use(float), lambda n: -180 <= n <= 180)
                }
            }
        )

    def __str__(self):
        return f"AddressInfo(data={self.__data})"
    
    def get(self) -> set[dict, dict]:
        """return the formatted data and an error message if the data is not valid"""
        if self.__schema.is_valid(self.__formattedData):
            return self.__formattedData, {"status": "success", "message": ""}
        else:
            return None, {"status": "error", "message": f"Internal Error. Data is not valid for AddressInfo: {self.__formattedData}"}



# Address Info (IK this is not abstract)
class AppraiserInfo(AddressSchematic):
    """Passed from the counties"""
    @strict_types
    def __init__(self, data:dict, client, translateStrategy) -> None:
        self.__data = data # this is the raw data from the appraiser
        self.__formattedData, self.__errorHandler = translateStrategy(data, client) # this is the translated data into consistent format

        self.__schema = Schema(
            {
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
                    "folio": And(str, len),
                    "parentFolio": str,
                    "legal": str,
                    "use": str,
                    "subdivision": Or(None, str),
                    "blk": Or(None, int),
                    "lot": Or(None, int),
                    "plat": {
                        "book": Or(None, int),
                        "page": Or(None, int)
                    },
                    "lotSize": Or(None, int, float),
                    "otherRecords": [
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
                        # "type": str, Should be used for sole proprietorship, partnership, LLC, etc
                        "mailingAddresses": [
                            {
                                "formattedAddress": And(str, len),
                                'folio': Or(None, And(str, Use(len))),
                                "addressComponents": {
                                    "streetNumber": str,
                                    "street": str,
                                    "streetDirection": str,
                                    "city": str,
                                    "county": str,
                                    "state": And(str, len),
                                    "country": And(str, len),
                                    "zip": And(str, len)
                                },
                                "geo": {
                                    "lat": And(Use(float), lambda n: -90 <= n <= 90),
                                    "lng": And(Use(float), lambda n: -180 <= n <= 180)
                                }
                            }
                        ]
                    }
                ],
                Optional("unStructured"): dict
            }
        )

    def __str__(self):
        return f"AppraiserInfo(data={self.__data})"
    
    def get(self) -> set[dict, dict]:
        """return the formatted data and an error message if the data is not valid"""
        if self.__errorHandler["status"] == "error":
            return None, self.__errorHandler
        else:
            if self.__schema.is_valid(self.__formattedData):
                return self.__formattedData, {"status": "success", "message": ""}
            else:
                json.dump(self.__formattedData, open("warning.json", "w"), indent=4)
                self.__schema.validate(self.__formattedData)
                return None, {"status": "error", "message": f"Internal Error. Data is not valid for AppraiserInfo: {self.__formattedData}"}
