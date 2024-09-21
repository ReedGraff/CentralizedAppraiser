import asyncio
import pandas as pd
import geopandas as gpd
import pyproj
import shapely
from CentralizedAppraiser import Client
from CentralizedAppraiser.abstracts._address import AddressInfo, AppraiserInfo
from CentralizedAppraiser.abstracts._exceptions import TranslationError, TranslationInvalid
from CentralizedAppraiser.utils import convert_to_int, esri_to_geojson, make_grid, project_coordinates
from ...Florida import Florida
import collections

import re
import json
import requests

class MiamiDade(Florida, Florida.County):
    """
    Abstract class to define the structure of a county object. This class is inherited by the other materials in the subdirectories.
        - It can be inherited by other classes, but not instantiated directly
    """
    @classmethod
    def appraiserInfoByFolio(cls, folio:str, client:Client, **kwargs) -> AppraiserInfo:
        """just returns the appraiser info for a folio. We use the Client to validate mailing addresses"""
        url = "https://www.miamidade.gov/Apps/PA/PApublicServiceProxy/PaServicesProxy.ashx"

        querystring = {
            "Operation": "GetPropertySearchByFolio",
            "clientAppName": "PropertySearch",
            "folioNumber": folio
        }

        headers = {
            "host": "www.miamidade.gov",
            "connection": "keep-alive",
            "sec-ch-ua": "\"Google Chrome\";v=\"123\", \"Not:A-Brand\";v=\"8\", \"Chromium\";v=\"123\"",
            "accept": "application/json, text/plain, */*",
            "sec-ch-ua-mobile": "?0",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "referer": "https://www.miamidade.gov/Apps/PA/PropertySearch/",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9",
            "cookie": "NSC_xxxy.njbnjebef.hpw_TTM_Efgbvmu=ffffffff09303f0345525d5f4f58455e445a4a42378b; _ga=GA1.1.360752393.1712189474; _ga_S336V3M935=GS1.1.1712189474.1.1.1712191060.0.0.0"
        }

        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        data = response.json()
        data["kwargs"] = kwargs
        return AppraiserInfo(data, client, cls.__translate)
        
    @classmethod
    def getPropertyLinesByFolio(cls, folio:str) -> list:
        """just returns the property lines for an address"""
        # list is just a list of lists of coordinates [[(lon, lat), (lon, lat), ...], [(lon, lat), (lon, lat), ...], ...]
        folio = re.sub(r'[^0-9]', '', folio)
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Origin': 'https://www.miamidade.gov',
            'Pragma': 'no-cache',
            'Referer': 'https://www.miamidade.gov/Apps/PA/PropertySearch/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }

        params = {
            'f': 'json', # typically "pbf" or "json"
            'spatialRel': 'esriSpatialRelIntersects',
            'where': f"FOLIO='{folio}'",
        }

        response = requests.get(
            'https://gisfs.miamidade.gov/mdarcgis/rest/services/MD_PA_PropertySearch/MapServer/6/query',
            params=params,
            headers=headers,
            timeout=5
        )

        try:
            data = response.json()

            # Extract the rings from the geometry
            rings = data['features'][0]['geometry']['rings']

            # Define the source and target coordinate systems
            src_proj = pyproj.CRS('EPSG:2236')  # WKID 2236
            dst_proj = pyproj.CRS('EPSG:4326')  # WGS84

            # Create a transformer object
            transformer = pyproj.Transformer.from_crs(src_proj, dst_proj, always_xy=True)

            # Transform the coordinates using map
            transformed_rings = list(map(lambda ring: list(map(lambda coord: transformer.transform(coord[0], coord[1]), ring)), rings))
            
            # Print the transformed coordinates
            return transformed_rings
        
        except:
            raise Exception("Cannot find property lines for folio")
    
    @classmethod
    def getScreenshotByFolio(cls, folio:str) -> set[bool, dict]:
        """just returns the screenshot for an address"""
        raise NotImplementedError
    
    @classmethod
    def __translate(cls, data:dict, client:Client) -> set[dict, dict]:
        # Address Info
        try:
            address = data["SiteAddress"][0]["Address"]
            # print(address)
            addressInfo = client.getByAddress(address, **data.get("kwargs", {}))
            addressInfo = addressInfo.get()
        except Exception as e:
            print(e.with_traceback(e.__traceback__))
            raise TranslationError("Error translating site address")
        
        try:
            mailAddress = f"{data['MailingAddress']['Address1']}, {data['MailingAddress']['City']}, {data['MailingAddress']['State']}"
            # print(mailAddress)
            mailAddressInfo = client.getByAddress(mailAddress)
            mailAddressInfo = mailAddressInfo.get()
        except Exception as e:
            print(e.with_traceback(e.__traceback__))
            raise TranslationError("Error translating mailing address")

        def parse_property_info(text):
            # Patterns to match lot, blk, and other records
            lot_pattern = re.compile(r'LOT\s(\d+)')
            blk_pattern = re.compile(r'BLK\s(\d+)')
            other_records_pattern = re.compile(r'(\w+)\s(\d+)-(\d+)')

            # Extract lot and blk
            lot_match = lot_pattern.search(text)
            blk_match = blk_pattern.search(text)
            
            lot = lot_match.group(1) if lot_match else None
            blk = blk_match.group(1) if blk_match else None

            # Extract other records
            other_records = []
            for match in other_records_pattern.finditer(text):
                record_type, book, page = match.groups()
                other_records.append({
                    "type": record_type,
                    "book": int(book),
                    "page": int(page)
                })

            return {
                "lot": lot,
                "blk": blk,
                "otherRecords": other_records
            }
        
        lot_blk_info = parse_property_info(data["LegalDescription"]["Description"])

        return {
            "locationInfo": addressInfo,
            "assessments": [
                {
                    "assessedValue": info["AssessedValue"],
                    "buildingValue": info["BuildingOnlyValue"],
                    "landValue": info["LandValue"],
                    "totalValue": info["TotalValue"],
                    "year": info["Year"],
                }
                for info in data.get("Assessment", {}).get("AssessmentInfos", [])
            ],
            "propertyInfo": {
                "parentFolio": data["PropertyInfo"].get("ParentFolio", ""),
                "legal": data["LegalDescription"]["Description"],
                "use": data["PropertyInfo"]["DORDescription"],
                "subdivision": data["PropertyInfo"]["SubdivisionDescription"],
                "blk": convert_to_int(lot_blk_info["blk"]),
                "lot": convert_to_int(lot_blk_info["lot"]),
                "lotSize": data["PropertyInfo"]["LotSize"],
                "records": [
                    {
                        "type": "plat",
                        "book": convert_to_int(data["PropertyInfo"]["PlatBook"]),
                        "page": convert_to_int(data["PropertyInfo"]["PlatPage"]),
                    },
                    *lot_blk_info["otherRecords"]
                ],
            },
            "owners": [
                {
                    "name": owner["Name"],
                    "mailingAddresses": [
                        mailAddressInfo
                    ]
                }
                for owner in data.get("OwnerInfos", [])
            ],
            "unStructured": data
        }

    @classmethod
    async def fetch_property_info(cls, folio, addressClient, **kwargs):
        info = await cls.appraiserInfoByFolio(folio, addressClient, **kwargs)
        info['folio'] = folio
        return info

    @classmethod
    async def process_folio(cls, folio, addressClient, **kwargs):
        try:
            return await cls.fetch_property_info(folio, addressClient, **kwargs)
        except (TranslationError, TranslationInvalid) as e:
            print(f"Error processing folio {folio}: {e}")
            return None
        except Exception as e:
            print(f"Unhandled error processing folio {folio}: {e}")
            return None

    @classmethod
    async def generate(cls, addressClient) -> gpd.GeoDataFrame:
        """gets the lines for the county, and runs __getGeoDataFrame for the whole county"""
        # Get the county property lines
        geoJ = Florida.getGeometryFeature("MiamiDade")
        shapeJ = shapely.shape(geoJ["geometry"])
        grid = make_grid(shapeJ, 1609.34)  # 1 mile for property search
        grid = [
            ((25.682028034910136, -80.35161252761796),
            (25.684072277888067, -80.34572545646562))
        ]

        results = gpd.GeoDataFrame()
        unique_objectids = set()

        for index, box in enumerate(grid):
            print(f"Searching square {index + 1} of {len(grid)}")
            result_offset = 0
            while True:
                Data = cls.__getGeoDataFrame(box[0], box[1], result_offset)
                if Data.empty:
                    break

                # Filter out rows with duplicate OBJECTID
                Data = Data[~Data['FOLIO'].isin(unique_objectids)]

                # Update the set of unique OBJECTIDs
                unique_objectids.update(Data['FOLIO'])

                # Select only the geometry and FOLIO columns, and rename FOLIO to apn
                Data = Data[['geometry', 'FOLIO']]

                transformer = pyproj.Transformer.from_crs('EPSG:2236', 'EPSG:4326', always_xy=True)
                tasks = []

                for folio, geometry in zip(Data['FOLIO'], Data['geometry']):
                    # Get unique reference point for each item
                    referencePoint = geometry.centroid
                    referencePoint = transformer.transform(referencePoint.x, referencePoint.y)
                    referencePoint = (referencePoint[1], referencePoint[0])

                    # Create task with unique reference point
                    task = cls.process_folio(folio, addressClient, coords=referencePoint)
                    tasks.append(task)

                additional_data = await asyncio.gather(*tasks)

                additional_data = [result for result in additional_data if result]

                if additional_data:
                    additional_df = pd.DataFrame(additional_data)
                    # Check if 'folio' column exists in additional_df
                    if 'folio' in additional_df.columns:
                        Data = Data.merge(additional_df, left_on='FOLIO', right_on='folio', how='left')
                    else:
                        print("Warning: 'folio' column not found in additional data. Skipping merge.")
                else:
                    print("No additional data found for this batch. Skipping merge.")

                Data = Data.rename(columns={'FOLIO': 'apn'})

                # Concatenate the filtered data
                results = pd.concat([results, Data], ignore_index=True)

                # Increment the offset for the next batch
                result_offset += 1000

        return gpd.GeoDataFrame(results)

    @classmethod
    def __getGeoDataFrame(cls, sw, ne, result_offset=0) -> gpd.GeoDataFrame:
        swLat = sw[0]
        swLng = sw[1]
        neLat = ne[0]
        neLng = ne[1]

        projected1x, projected1y = project_coordinates(swLng, swLat, 2236)
        projected2x, projected2y = project_coordinates(neLng, neLat, 2236)
        cookies = {}
        headers = {}
        result_record_count = 1000  # Number of records to return per request

        url = (
            'https://gisfs.miamidade.gov/mdarcgis/rest/services/MD_PA_PropertySearch/MapServer/8/query'
            '?f=json'
            '&geometry={"xmin":' + str(projected1x) + ',"ymin":' + str(projected1y) + ',"xmax":' + str(projected2x) + ',"ymax":' + str(projected2y) + '}'
            '&outFields=*'
            '&spatialRel=esriSpatialRelIntersects'
            '&where=1=1'
            '&geometryType=esriGeometryEnvelope'
            '&resultRecordCount=' + str(result_record_count) +
            '&resultOffset=' + str(result_offset)
        )

        try:
            response = requests.get(
                url,
                cookies=cookies,
                headers=headers,
                timeout=15
            )
        except Exception as e:
            print(f"Error fetching data: {e}")
            return gpd.GeoDataFrame()

        dictResponse = response.json()
        print("Found ", len(dictResponse.get("features", [])), " \n")

        # Convert Esri JSON to GeoJSON-like format
        geojson_response = esri_to_geojson(dictResponse)

        # Create GeoDataFrame from the converted GeoJSON
        gdf = gpd.GeoDataFrame.from_features(geojson_response["features"])
        return gdf

# can't do on webserver
# def printPropertySearch(self, address, outputPath):
#     # Paths
#     import os
#     dir_path = os.getcwd()

#     import base64
#     from selenium.webdriver.chrome.service import Service
#     from selenium.webdriver import Chrome, ChromeOptions

#     print_settings = {
#         "recentDestinations": [{
#             "id": "Save as PDF",
#             "origin": "local",
#             "account": "",
#         }],
#         "selectedDestinationId": "Save as PDF",
#         "version": 2,
#         "isHeaderFooterEnabled": False,
#         "isLandscapeEnabled": True,
        
#         # 'paperWidth': 8.5,
#         # 'paperHeight': 12
#     }


#     options = ChromeOptions()
#     # options.binary_location = "Storage/Florida/chrome/chrome.exe"
#     options.add_argument("--log-level=3");
#     options.add_argument("--start-maximized")
#     options.add_argument('--window-size=1920,1080')
#     options.add_argument("--headless")
#     options.add_argument('--enable-print-browser')
#     options.add_argument("--kiosk-printing")
#     options.add_experimental_option("prefs", {
#         "printing.print_preview_sticky_settings.appState": json.dumps(print_settings),
#         "savefile.default_directory": dir_path,  # Change default directory for downloads
#         "download.default_directory": dir_path,  # Change default directory for downloads
#         "download.prompt_for_download": False,  # To auto download the file
#         "download.directory_upgrade": True,
#         "profile.default_content_setting_values.automatic_downloads": 1,
#         "safebrowsing.enabled": True
#     })

#     driver = Chrome(service=Service("Storage/Florida/chrome/chromedriver.exe"), options=options)
#     driver.get("https://www.miamidade.gov/Apps/PA/PropertySearch/#/report/detailed")
#     driver.execute_script('window.sessionStorage.currentFolio = ' + self.getFolio(address).replace("-", ""))
#     driver.refresh()
    
#     pdf_data = driver.execute_cdp_cmd("Page.printToPDF", print_settings)
#     with open(outputPath, 'wb') as file:
#         file.write(base64.b64decode(pdf_data['data']))