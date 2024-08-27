import re
from ..utils import strict_types
import requests

from ._address import AddressInfo



# Client
class Client(dict):
    """
    This is an abstract class that should be inhereted by any other clients used for this library.
    """
    def __init__(self) -> None:
        raise NotImplementedError

    def __str__(self):
        return f"Client(key={self.key})"
    
    def getByAddress(self, location:str) -> set[AddressInfo, dict]: #TODO: This should be a more specific address schema
        raise NotImplementedError
    
    def getByID(self, placeID:str) -> set[AddressInfo, dict]: #TODO: This should be a more specific address schema
        raise NotImplementedError
    
    @classmethod
    def __translate(cls, data:dict) -> dict:
        raise NotImplementedError



# Google Client
class GoogleClient(Client):
    """
    This client is used as a wrapper for the Google Maps Places API as of (August 2024)
    """
    def __init__(self, key:str="") -> None:
        """
        
        Args:
            key (str): The API key to use for the Google API client.
        """
        # Throw errors for un-met type requirements
        assert type(key) == str, "key must be a string"

        self.key = key

    def __str__(self):
        return f"GoogleClient(key={self.key})"
    
    def getByAddress(self, location:str) -> set[AddressInfo, dict]:
        """returns an AddressInfo object from the placeID"""
        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': self.key,
            'X-Goog-FieldMask': 'places.location,places.addressComponents,places.formattedAddress',
        }

        json_data = {
            'textQuery': location,
        }

        response = requests.post('https://places.googleapis.com/v1/places:searchText', headers=headers, json=json_data)
        data = response.json()

        if "error" in data or "places" not in data:
            return None, {"status": "error", "message": f"Internal Error. Google API returned: {data}"}
        else:
            return AddressInfo(data["places"][0], self.__translate), {"status": "success"}
    
    def getByID(self, placeID:str) -> set[AddressInfo, dict]: #TODO: This should be a more specific address schema
        """returns an AddressInfo object from the placeID"""
        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': self.key,
            'X-Goog-FieldMask': 'location,addressComponents,formattedAddress' # 'address_component,formatted_address,geometry'
        }

        response = requests.get(f'https://places.googleapis.com/v1/places/{placeID}', headers=headers)
        data = response.json()
        
        if "error" in data or "addressComponents" not in data:
            return None, {"status": "error", "message": f"Internal Error. Google API returned: {data}"}
        else:
            return AddressInfo(data, self.__translate), {"status": "success"}
    
    @classmethod
    def __translate(cls, data: dict) -> dict:
        # convert list to dict
        addressComponents = {comp["types"][0]: comp["longText"] for comp in data["addressComponents"]}

        # convert long directions to short directions
        directionMapping = {
            "North": "N",
            "South": "S",
            "East": "E",
            "West": "W",
            "Northeast": "NE",
            "Northwest": "NW",
            "Southeast": "SE",
            "Southwest": "SW"
        }

        streetTypeMapping = {
            "Street": "ST",
            "Avenue": "AVE",
            "Road": "RD",
            "Boulevard": "BLVD",
            "Drive": "DR",
            "Lane": "LN",
            "Court": "CT",
            "Place": "PL",
            "Square": "SQ",
            "Terrace": "TER",
            "Trail": "TRL",
            "Parkway": "PKWY",
            "Commons": "CMNS",
            "Highway": "HWY"
        }

        def removeOrdinalSuffix(street_name: str) -> str:
            return re.sub(r'(\d+)(st|nd|rd|th)\b', r'\1', street_name)

        streetDirection = addressComponents.get("route", "").split(" ")[0]
        streetDirectionAbbr = directionMapping.get(streetDirection, streetDirection)
        street = " ".join(addressComponents.get("route", "").split(" ")[1:])
        street = removeOrdinalSuffix(street)

        for longType, shortType in streetTypeMapping.items():
            if longType in street:
                street = street.replace(longType, shortType)
                break

        return {
            "formattedAddress": data["formattedAddress"],
            "folio": None,
            "addressComponents": {
                "streetNumber": addressComponents.get("street_number", ""),
                "streetDirection": streetDirectionAbbr,  # always NE, NW, SE, SW, N, S, E, W
                "street": street, # street = ST, AVE, RD, BLVD, etc. if its a number, remove the suffix
                "city": addressComponents.get("locality", ""),
                "county": addressComponents.get("administrative_area_level_2", ""),
                "state": addressComponents.get("administrative_area_level_1", ""),
                "country": addressComponents.get("country", ""),
                "zip": addressComponents.get("postal_code", ""),
            },
            "geo": {
                "lat": data["location"]["latitude"],
                "lng": data["location"]["longitude"],
            },
        }



# Google Client
class RegridClient(Client):
    """
    This client is used as a wrapper for the Google Maps Places API as of (August 2024)
    """
    def __init__(self, key:str="") -> None:
        """
        
        Args:
            key (str): The API key to use for the Google API client.
        """
        # Throw errors for un-met type requirements
        assert type(key) == str, "key must be a string"

        self.key = key

    def __str__(self):
        return f"RegridClient(key={self.key})"
    
    def getByAddress(self, location:str) -> set[AddressInfo, dict]:
        """returns an AddressInfo object from the placeID"""
        url = f"https://app.regrid.com/api/v2/parcels/address?query={location}&path={"/us/fl"}&limit={"1"}&token={self.key}"

        headers = {"accept": "application/json"}

        response = requests.get(url, headers=headers)
        data = response.json()

        if "status" in data and data["status"] == "error":
            return None, {"status": "error", "message": f"Internal Error. Regrid API returned: {data}"}
        
        else:
            return AddressInfo(data, self.__translate), {"status": "success", "message": "Success"}
    
    def getByID(self, placeID:str) -> set[AddressInfo, dict]: #TODO: This should be a more specific address schema
        """returns an AddressInfo object from the placeID"""
        url = f"https://app.regrid.com/api/v2/parcels/{placeID}?token={self.key}"

        headers = {"accept": "application/json"}

        response = requests.get(url, headers=headers)
        data = response.json()

        if "status" in data and data["status"] == "error":
            return None, {"status": "error", "message": f"Internal Error. Regrid API returned: {data}"}
        
        else:
            return AddressInfo(data, self.__translate), {"status": "success", "message": "Success"}
    
    @classmethod
    def __translate(cls, data: dict) -> dict:
        feature = data['parcels']['features'][0]
        properties = feature['properties']['fields']
        geometry = feature['geometry']['coordinates'][0][0]
        
        def removeOrdinalSuffix(street_name: str) -> str:
            return re.sub(r'(\d+)(st|nd|rd|th)\b', r'\1', street_name)

        return {
            "formattedAddress": properties.get('address', ''),
            "folio": properties.get('parcelnumb', None),
            "addressComponents": {
                "streetNumber": properties.get('saddno', ''),
                "streetDirection": properties.get('saddpref', ''),
                "street": removeOrdinalSuffix(properties.get('saddstr', '')),
                "city": properties.get('scity', ''),
                "county": properties.get('county', ''),
                "state": properties.get('state2', ''),
                "country": "USA",  # Assuming country is USA
                "zip": properties.get('szip5', ''),
            },
            "geo": {
                "lat": geometry[1],
                "lng": geometry[0],
            },
        }



# Google Client
class AppleClient(Client):
    """
    This client is used as a wrapper for the Apple Maps API
    """
    def __init__(self, key:str="") -> None:
        """
        
        Args:
            key (str): The API key to use for the Google API client.
        """
        assert type(key) == str, "key must be a string"

        self.key = key

    def __str__(self):
        return f"AppleClient(key={self.key})"
    
    def getByAddress(self, location) -> set[AddressInfo, dict]:
        """returns an AddressInfo object from the address"""
        raise NotImplementedError
    
    def getByID(self, placeID:str) -> set[AddressInfo, dict]: #TODO: This should be a more specific address schema
        raise NotImplementedError
    
    @classmethod
    def __translate(cls, data:dict) -> dict:
        return {
            "address": {
                "street": data["address"]["name"] + " " + data["address"]["streetNumber"],
                "direction": data["address"]["direction"],
                "city": data["address"]["city"]
            },
            "time": data["time"]
        }
    
if __name__ == "__main__":
    # print("Running tests...")
    googleClient = GoogleClient()
    print(googleClient.getByAddress("1234 Main St, Orlando, FL 32801")._data)
    print(googleClient.getByAddress("1234 Main St, Orlando, FL 32801").data)