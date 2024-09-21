import re
import requests
import usaddress
from geopy.geocoders import Nominatim
import reverse_geocode

from ._address import AddressInfo
from ._exceptions import AddressClientError



# Client
class Client(dict):
    """
    This is an abstract class that should be inhereted by any other clients used for this library.
    """
    def __init__(self) -> None:
        raise NotImplementedError

    def __str__(self):
        return f"Client(key={self.key})"
    
    def getByAddress(self, location: str, **kwargs) -> AddressInfo:
        raise NotImplementedError
    
    def getByID(self, placeID:str) -> set[AddressInfo, dict]:
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
        
    def getByAddress(self, location: str, **kwargs) -> AddressInfo:
        """returns an AddressInfo object from the placeID"""
        params = {
            'address': location,
            'key': self.key,
        }

        response = requests.get('https://maps.googleapis.com/maps/api/geocode/json', params=params)
        data = response.json()
        
        if "error_message" in data or "results" not in data:
            raise AddressClientError(f"Internal Error. Google API returned: {data}")
        else:
            return AddressInfo(data["results"][0], self.__translate)
    
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
        addressComponents = {comp["types"][0]: comp["long_name"] for comp in data["address_components"]}
        
        # subpremise
        return {
            "formattedAddress": data["formatted_address"],
            "addressComponents": {
                "streetNumber": addressComponents.get("street_number", ""),
                "street": addressComponents.get("route", ""),
                "unit": addressComponents.get("subpremise", ""),
                "city": addressComponents.get("locality", ""),
                "county": addressComponents.get("administrative_area_level_2", ""),
                "state": addressComponents.get("administrative_area_level_1", ""),
                "country": addressComponents.get("country", ""),
                "zip": addressComponents.get("postal_code", ""),
            },
            "geo": {
                "lat": data["geometry"]["location"]["lat"],
                "lng": data["geometry"]["location"]["lng"],
            },
        }



# USPS Client
class USPSClient(Client):
    pass



# Nominatim Client
class NominatimClient(Client):
    def __init__(self):
        self.geolocator = Nominatim(user_agent="address_geocoder")

    def __str__(self):
        return "NominatimClient()"
    
    def getByAddress(self, location: str, **kwargs) -> AddressInfo:
        """Returns an AddressInfo object from the location string"""
        try:
            location_data = self.geolocator.geocode(location, addressdetails=True)
        except Exception as e:
            raise AddressClientError(f"Internal Error. Nominatim API returned no data for location: {location}")
        if not location_data:
            raise AddressClientError(f"Internal Error. Nominatim API returned no data for location: {location}")
        
        return AddressInfo(location_data, self.__translate)
    
    def getByID(self, placeID: str) -> set[AddressInfo]:
        raise NotImplementedError # don't change this part...
    
    @classmethod
    def __translate(cls, data: dict) -> dict:
        addrData = data.raw
        address = data.raw.get("address", {})
        return {
            "formattedAddress": addrData.get("display_name", ""),
            "addressComponents": {
                "streetNumber": address.get("house_number", ""),
                "street": address.get("road", ""),
                "unit": address.get("subpremise", ""),
                "city": address.get("city", ""),
                "county": address.get("county", ""),
                "state": address.get("state", ""),
                "country": address.get("country", ""),
                "zip": address.get("postcode", ""),
            },
            "geo": {
                "lat": data.latitude,
                "lng": data.longitude,
            },
        }



# OSM Simple Client provided VIA Nominatim requests from the website [DEPRECATED, USE NOMINATIM CLIENT INSTEAD]
class OSMSimpleClient(Client):
    """
    This client is used as a wrapper for the OpenStreetMap Nominatim API
    """
    def __init__(self) -> None:
        """
        Initialize the OSMClient. No API key is required for Nominatim.
        """
        self.search_url = "https://nominatim.openstreetmap.org/search.php"
        self.details_url = "https://nominatim.openstreetmap.org/details.php"
        self.headers = {
            'User-Agent': 'AddressInfoApp/1.0',
            'Accept-Language': 'en-US,en;q=0.9'
        }

    def __str__(self):
        return "OSMSimpleClient()"

    def getByAddress(self, location: str, **kwargs) -> AddressInfo:
        """Returns an AddressInfo object from the location string"""
        params = {
            'q': location,
            'format': 'jsonv2',
            'polygon_geojson': 1,
            'addressdetails': 1
        }

        response = requests.get(self.search_url, params=params, headers=self.headers)
        data = response.json()

        if not data:
            raise AddressClientError(f"No results found for address: {location}")

        # Use the first result
        result = data[0]
        
        # Get additional details
        details = self._get_details(result['osm_type'], result['osm_id'], result['category'])

        return AddressInfo(details, self.__translate)

    def getByID(self, placeID: str) -> set[AddressInfo, dict]:
        """Returns an AddressInfo object from the placeID"""
        # OSM doesn't have a direct equivalent to Google's placeID
        # We'll assume the placeID is in the format "osmtype:osmid:category"
        try:
            osm_type, osm_id, category = placeID.split(':')
        except ValueError:
            return None, {"status": "error", "message": "Invalid placeID format"}

        details = self._get_details(osm_type, osm_id, category)

        if not details:
            return None, {"status": "error", "message": f"No results found for placeID: {placeID}"}

        return AddressInfo(details, self.__translate), {"status": "success"}

    def _get_details(self, osm_type, osm_id, category):
        """Helper method to get detailed information about a place"""
        params = {
            'osmtype': osm_type[0].upper(),  # Convert 'way' to 'W', 'node' to 'N', etc.
            'osmid': osm_id,
            'class': category,
            'format': 'json',
            'addressdetails': 1,
            'hierarchy': 0,
            'group_hierarchy': 1,
            'polygon_geojson': 1
        }

        response = requests.get(self.details_url, params=params, headers=self.headers)
        return response.json()

    @classmethod
    def __translate(cls, data: dict) -> dict:
        """Translate OSM data to a standardized format"""
        address_parts = data.get('address', [])
        
        # Find the most specific address components
        street = next((item['localname'] for item in address_parts if item['type'] in ['street', 'road', 'path']), '')
        city = next((item['localname'] for item in address_parts if item['type'] in ['city', 'town', 'village']), '')
        county = next((item['localname'] for item in address_parts if item['type'] == 'county'), '')
        state = next((item['localname'] for item in address_parts if item['type'] == 'state'), '')
        country = next((item['localname'] for item in address_parts if item['type'] == 'country'), '')
        postcode = next((item['localname'] for item in address_parts if item['type'] == 'postcode'), '')

        return {
            "formattedAddress": data.get('calculated_postcode', ''),
            "addressComponents": {
                "streetNumber": "",  # OSM doesn't typically provide this separately
                "street": street,
                "unit": "",  # OSM doesn't typically provide this
                "city": city,
                "county": county,
                "state": state,
                "country": country,
                "zip": postcode,
            },
            "geo": {
                "lat": data['centroid']['coordinates'][1],
                "lng": data['centroid']['coordinates'][0],
            },
        }



# OSM structured Client using Nominatim
class OSMAndUSAClient(OSMSimpleClient):
    """
    This client is used as a wrapper for the OpenStreetMap Nominatim API
    """
    def __init__(self) -> None:
        """
        Initialize the OSMClient. No API key is required for Nominatim.
        """
        self.search_url = "https://nominatim.openstreetmap.org/search.php"
        self.details_url = "https://nominatim.openstreetmap.org/details.php"
        self.headers = {
            'User-Agent': 'AddressInfoApp/1.0',
            'Accept-Language': 'en-US,en;q=0.9'
        }

    def __str__(self):
        return "OSMAndUSAClient()"

    def getByAddress(self, location: str, **kwargs) -> AddressInfo:
        """Returns an AddressInfo object from the location string"""
        dataUSA = USAAddressClient().getByAddress(location).get()
        dataComp = dataUSA["addressComponents"]

        def ordinal(n):
            if 10 <= n % 100 <= 20:
                suffix = 'th'
            else:
                suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
            return str(n) + suffix

        street_name = dataComp.get('street', '')
        match = re.search(r'(\d+)', street_name)
        if match:
            number = int(match.group(1))
            street_name = street_name.replace(str(number), ordinal(number))

        params = {
            "street": dataComp.get('streetNumber', '') + " " + street_name,
            "city": dataComp.get('city', ''),
            "state": dataComp.get('state', ''),
            "country": "USA",
            'format': 'jsonv2',
            'polygon_geojson': 1,
            'addressdetails': 1
        }

        response = requests.get(self.search_url, params=params, headers=self.headers)
        data = response.json()

        if not data:
            raise AddressClientError(f"No results found for address: {location}")

        # Use the first result
        result = data[0]
        
        # Get additional details
        details = self._get_details(result['osm_type'], result['osm_id'], result['category'])
        details["usaData"] = dataUSA

        return AddressInfo(details, self.__translate)
    
    def getByID(self, placeID: str) -> set[AddressInfo, dict]:
        """Returns an AddressInfo object from the placeID"""
        # OSM doesn't have a direct equivalent to Google's placeID
        # We'll assume the placeID is in the format "osmtype:osmid:category"
        try:
            osm_type, osm_id, category = placeID.split(':')
        except ValueError:
            return None, {"status": "error", "message": "Invalid placeID format"}

        details = self._get_details(osm_type, osm_id, category)

        if not details:
            return None, {"status": "error", "message": f"No results found for placeID: {placeID}"}

        return AddressInfo(details, self.__translate), {"status": "success"}

    def _get_details(self, osm_type, osm_id, category):
        """Helper method to get detailed information about a place"""
        params = {
            'osmtype': osm_type[0].upper(),  # Convert 'way' to 'W', 'node' to 'N', etc.
            'osmid': osm_id,
            # 'class': category,
            'format': 'json',
            'addressdetails': 1,
            'hierarchy': 0,
            'group_hierarchy': 1,
            'polygon_geojson': 1
        }

        response = requests.get(self.details_url, params=params, headers=self.headers)
        return response.json()

    @classmethod
    def __translate(cls, data: dict) -> dict:
        """Translate OSM data to a standardized format"""
        usaData = data["usaData"]["addressComponents"]
        address_parts = data.get('address', [])
        
        # Find the most specific address components
        street = next((item['localname'] for item in address_parts if item['type'] in ['street', 'road', 'path', 'residential']), '')
        city = next((item['localname'] for item in address_parts if item['type'] in ['city', 'town', 'village', 'administrative'] and item['admin_level'] == 8), '')
        county = next((item['localname'] for item in address_parts if item['type'] == 'administrative' and item['admin_level'] == 6), '')
        state = next((item['localname'] for item in address_parts if item['type'] == 'administrative' and item['admin_level'] == 4), '')
        country = next((item['localname'] for item in address_parts if item['type'] == 'country'), '')
        postcode = next((item['localname'] for item in address_parts if item['type'] == 'postcode'), '')

        return {
            "formattedAddress": data.get('calculated_postcode', usaData.get('calculated_postcode', '')),
            "addressComponents": {
                "streetNumber": data.get('streetNumber', '') if data.get('streetNumber', '') != '' else usaData.get('streetNumber', ''),
                "street": street if street else usaData.get('street', ''),
                "unit": data.get('unit', usaData.get('unit', '')),
                "city": city if city else usaData.get('city', ''),
                "county": county if county else usaData.get('county', ''),
                "state": state if state else usaData.get('state', ''),
                "country": country if country else usaData.get('country', ''),
                "zip": postcode if postcode else usaData.get('zip', ''),
            }
        }


# usaaddress "Client" (this is just a dumb parser)
class USAAddressClient(Client):
    """
    This client is used as a wrapper for the Google Maps Places API as of (August 2024)
    """
    def __init__(self) -> None:
        """
        Args:
            key (str): The API key to use for the Google API client.
        """
        pass

    def __str__(self):
        return f"USAAddressClient(key={self.key})"
        
    def getByAddress(self, location: str, **kwargs) -> AddressInfo:
        """returns an AddressInfo object from the location string"""
        return AddressInfo(usaddress.tag(location), self.__translate)
    
    def getByID(self, placeID:str) -> set[AddressInfo, dict]: #TODO: This should be a more specific address schema
        """returns an AddressInfo object from the placeID"""
        raise NotImplementedError
    
    @classmethod
    def __translate(cls, data: usaddress.OrderedDict) -> dict:
        # Extract address components from OrderedDict
        data = data[0]

        addressComponents = {
            "street_number": data.get("AddressNumber", ""),
            "route": f"{data.get('StreetNamePreDirectional', '')} {data.get('StreetName', '')} {data.get('StreetNamePostType', '')}".strip(),
            "subpremise": f"{data.get('OccupancyType', '')} {data.get('OccupancyIdentifier', '')}".strip(),
            "locality": data.get("PlaceName", ""),
            "administrative_area_level_2": "",  # Not available in provided data
            "administrative_area_level_1": data.get("StateName", ""),
            "country": "",  # Not available in provided data
            "postal_code": data.get("ZipCode", "")
        }
        
        # Return the formatted address dictionary
        return {
            "formattedAddress": f"{addressComponents['street_number']} {addressComponents['route']}, {addressComponents['locality']}, {addressComponents['administrative_area_level_1']} {addressComponents['postal_code']}".strip(),
            "addressComponents": {
                "streetNumber": addressComponents.get("street_number", ""),
                "street": addressComponents.get("route", ""),
                "unit": addressComponents.get("subpremise", ""),
                "city": addressComponents.get("locality", ""),
                "county": addressComponents.get("administrative_area_level_2", ""),
                "state": addressComponents.get("administrative_area_level_1", ""),
                "country": addressComponents.get("country", ""),
                "zip": addressComponents.get("postal_code", "")
            }
            # "geo": {
            #     "lat": "",  # Not available in provided data
            #     "lng": "",  # Not available in provided data
            # },
        }



# USA Reverse Client
class USAReverseClient(Client):
    """
    This client is used as a wrapper for the usaAddress library and the reverse_geocode library to get address information from coordinates.

    For large batch jobs, this should be the defacto client to use.
    """
    def __init__(self) -> None:
        """
        Args:
            key (str): The API key to use for the Google API client.
        """
        pass

    def __str__(self):
        return f"USAAddressClient(key={self.key})"
        
    def getByAddress(self, location: str, **kwargs) -> AddressInfo:
        """returns an AddressInfo object from the location string.. coords is in the format (lat, lng)"""
        coords: set[float, float] = kwargs.get("coords", None)
        if not coords:
            data = {
                "comps": usaddress.tag(location)[0], # has errors... should catch with .parse() instead...
                # "lat": coords[0],
                # "lng": coords[1]
            }
        else:
            data = {
                "comps": usaddress.tag(location)[0], # has errors... should catch with .parse() instead...
                "coords": coords
            }

        return AddressInfo(data, self.__translate)
    
    def getByID(self, placeID:str) -> set[AddressInfo, dict]: #TODO: This should be a more specific address schema
        """returns an AddressInfo object from the placeID"""
        raise NotImplementedError
    
    @classmethod
    def __translate(cls, data: usaddress.OrderedDict) -> dict:
        # coordinate data components
        if "coords" not in data:
            coords = None
            coordinateDataComponents = {}
        else:
            coords = data["coords"]
            # print(coords)
            coordinateData = reverse_geocode.get(coords, min_population=0)
            coordinateDataComponents = {
                "city": coordinateData.get("city", ""),
                "county": coordinateData.get("county", ""),
                "state": coordinateData.get("state", ""),
                "country": coordinateData.get("country_code", ""),
            }

        # usa address components
        data = data["comps"]
        addressDataComponents = {
            "streetNumber": data.get("AddressNumber", ""),
            "street": f"{data.get('StreetNamePreDirectional', '')} {data.get('StreetName', '')} {data.get('StreetNamePostType', '')}".strip(),
            "unit": f"{data.get('OccupancyType', '')} {data.get('OccupancyIdentifier', '')}".strip(),
            "city": data.get("PlaceName", ""),
            "county": "", # not accurate
            "state": data.get("StateName", ""),
            "country": data.get("CountryName", ""),
            "zip": data.get("ZipCode", "")
        }
        
        # Return the formatted address dictionary
        finalComponents = addressDataComponents | coordinateDataComponents
        return {
            "formattedAddress": f"{finalComponents['streetNumber']} {finalComponents['street']}, {finalComponents['city']} {finalComponents['state']} {finalComponents['zip']}".strip(),
            "addressComponents": finalComponents
        }



# Regrid Client
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
    
    def getByAddress(self, location: str, **kwargs) -> AddressInfo:
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
    
    def getByAddress(self, location) -> AddressInfo:
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

"""
address = Address(
    name='Tobin Brown',
    address_1='1234 Test Ave.',
    city='Test',
    state='NE',
    zipcode='55555'
)

usps = USPSApi('39V4COMPL3373', test=True)
validation = usps.validate_address(address)
print(validation.result)
"""

"""
# Non Legacy USPS API
url = "https://apis.usps.com/oauth2/v3/token"
payload = {
    "grant_type": "client_credentials",
    "client_id": "mKgu4ZeDiyjjYhwzIEp35JwHqo8PSvvV",
    "client_secret": "9JWTqb0DiLcCQcB5",
    "scope": "ResourceA ResourceB ResourceC"
}
headers = {
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
"""

"""
OSM:
url = "https://nominatim.openstreetmap.org/search?"
payload = {
    "q": "123 Main St., Miami, FL",
}
headers = {
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)
print(response.text)
"""

if __name__ == "__main__":
    # print("Running tests...")
    osmClient = OSMAndUSAClient()
    print(osmClient.getByAddress("1234 Main St, Orlando, FL 32801"))
