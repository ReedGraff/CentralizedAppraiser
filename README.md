# CentralizedAppraiser
A new form of accessing real estate data because nobody wants to pay >$80,000 for Regrid and still not have access to up to date information.

TRY IT WITH ANY ADDRESS IN MIAMIDADE/BROWARD COUNTY.



## Installation
```bash
pip install CentralizedAppraiser
```






## This may be used in unison with regrid, however, it is distinguished in a few ways:
* It dynamically accesses property appraiser data (meaning it is always up to date)
* It enables you to access all the additional county specific data
* It enables you to interact with the county website (for example, to screenshot the property appraiser website)
* It is free
* It is open source (please contribute)








## Below are the steps explaining how this library works:
1. Create a client of a map provider (for example, google maps, regrid, apple maps, etc.)
2. Geocode the address and get the address components (no matter what client you use CentralizedAppraiser will ensure the address components are standardized)
3. Determine the county which the address is in
4. Determine the folio if not provided
5. Request the data from the county (this is similarly standardized so that all municipalities/cities can be accessed in the same way)







## Usage Examples
Using the Google Maps client, get the appraiser info for an address given the Google Place ID. Also refer to the examples directory for more examples in the github repository.

#### Regrid Client
This is a simple implementation which when given an address, it will return the appraiser information.
```python
import CentralizedAppraiser
from CentralizedAppraiser.clients import RegridClient

client = RegridClient("YOUR_REGRID_API_KEY")
addressInfo, errorHandler = client.getByAddress("6760 SW 48TH ST")
appraiserInfo, errorHandler = CentralizedAppraiser.appraiserInfoByAddressInfo(addressInfo, client)

print(appraiserInfo.get())
```

This is a more complex implementation which accomplishes the same thing as the above code, however it is more verbose and shows each step of the process.
```python
import CentralizedAppraiser
from CentralizedAppraiser.clients import RegridClient

client = RegridClient("YOUR_REGRID_API_KEY") # API KEY
addressInfo, errorHandler = client.getByAddress("6760 SW 48TH ST")
classPointer, errorHandler = CentralizedAppraiser.classByAddressInfo(addressInfo)
data, errorHandler = addressInfo.get()
# folio, errorHandler = classPointer.folioByAddressInfo(addressInfo) # commented out because Regrid already provides the folio
appraiserInfo, errorHandler = classPointer.appraiserInfoByFolio(data["folio"], client)

print(appraiserInfo.get())
```

#### Google Client
This is a simple implementation which when given an address, it will return the appraiser information.
```python
import CentralizedAppraiser
from CentralizedAppraiser.clients import GoogleClient

client = GoogleClient("YOUR_GOOGLE_API_KEY")
addressInfo, errorHandler = client.getByAddress("6760 SW 48TH ST")
appraiserInfo, errorHandler = CentralizedAppraiser.appraiserInfoByAddressInfo(addressInfo, client)

print(appraiserInfo.get())
```

This is a more complex implementation which accomplishes the same thing as the above code, however it is more verbose and shows each step of the process.
```python
import CentralizedAppraiser
from CentralizedAppraiser.clients import GoogleClient

client = GoogleClient("YOUR_GOOGLE_API_KEY") # API KEY
addressInfo, errorHandler = client.getByAddress("6760 SW 48TH ST")
classPointer, errorHandler = CentralizedAppraiser.classByAddressInfo(addressInfo)
folio, errorHandler = classPointer.folioByAddressInfo(addressInfo)
appraiserInfo, errorHandler = classPointer.appraiserInfoByFolio(folio, client)

print(appraiserInfo.get())
```






## Functions

#### CentralizedAppraiser
* `appraiserInfoByAddressInfo(addressInfo:AddressInfo, client:Client) -> set[AppraiserInfo, dict]`
    * Returns the appraiser info by the address info
* `classByAddressInfo(addressInfo:AddressInfo) -> set[Country, dict]`
    * Returns the class pointer by the address info
* `classByPath(path:list) -> set[Country, dict]`
    * Returns the class pointer by the path to the county website
* `pathByAddressInfo(addressInfo:AddressInfo) -> set[list, dict]`
    * Returns the path to the county website as a list of strings

#### AddressSchematic (extended by AddressInfo, and AppraiserInfo)
* `__init__(self, data:dict, client, translateStrategy) -> None`
    * Initializes the AddressSchematic object
* `get(self) -> set[dict, dict]`
    * Returns the standardized address components and the error handler

#### Client (extended by GoogleClient, and RegridClient)
* `__init__(self, key:str="") -> None`
    * Initializes the client object with an api key
* `getByAddress(self, location:str) -> set[AddressInfo, dict]`
    * Returns the address info by the location as a string
* `getByID(self, placeID:str) -> set[AddressInfo, dict]`
    * Returns the address info by the place id as a string
* `__translate(cls, data: dict) -> dict`
    * Translates the data to the standardized format from the client's format

#### Country (*extended by all other locations)
* `def getDefiningGeometryKey(cls) -> str:`
    * Returns the key for the geometry json parameters
* `def folioByAddressInfo(cls, search:AddressInfo) -> set[str, dict]:`
    * Returns the folio by the address info
* `def appraiserInfoByFolio(cls, folio:str, client:Client) -> set[AppraiserInfo, dict]:`
    * Returns the appraiser info by the folio
* `def appraiserInfoByAddressInfo(cls, search:AddressInfo, client:Client) -> set[AppraiserInfo, dict]:`
    * Returns the appraiser info by the address info. This just implements the folioByAddressInfo and appraiserInfoByFolio functions
* `def getScreenshotByFolio(cls, folio:str) -> set[bool, dict]:`
    * Returns the screenshot of the property appraiser website by the folio with selenium



## Schemas
The following are various schemas used by different parts of the program. These schemas are used to ensure that the data is standardized and that the data is correct. The schemas are written with the [schema](https://pypi.org/project/schema/) library.

#### AddressInfo Schema
```python
Schema({
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
})
```

#### AppraiserInfo Schema
```python
Schema({
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
        "use": int,
        "subdivision": str,
        "blk": int,
        "lot": int,
        "plat": {
            "book": int,
            "page": int
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
})
```

#### Error Schema
```python
Schema({
    "status": Or("error", "success"), # "error" or "success"
    "message": str,
})
```





<!--
Notes for the author because he doesn't know what he's doing:

## Beginning:
```bash
python -m pip install --upgrade pip
python -m pip --version

python -m venv <myenvname>
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## process to update pip:
```bash
pip freeze > requirements.txt 
# add this to the toml
# clear dist folder

python -m build
python -m twine upload --repository testpypi dist/*
```
View the package on testpypi: https://test.pypi.org/project/CentralizedAppraiser/

-->
