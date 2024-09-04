import pyproj
from CentralizedAppraiser import Client
from CentralizedAppraiser.abstracts._address import AddressInfo, AppraiserInfo
from CentralizedAppraiser.utils import convert_to_int
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
    def folioByAddressInfo(cls, search:AddressInfo) -> set[str, dict]:
        """just returns the folio for an address"""
        address, error = search.get()
        if error["status"] == "error":
            return None, error
        
        else:
            address = address["addressComponents"]

            url = "https://www.miamidade.gov/Apps/PA/PApublicServiceProxy/PaServicesProxy.ashx"

            # resultRequest = https://www.miamidade.gov/Apps/PA/PApublicServiceProxy/PaServicesProxy.ashx?Operation=GetAddress&clientAppName=PropertySearch&myUnit=&from=1&myAddress=25%20INDIAN%20CREEK%20ISLAND%20RD,%20Indian%20Creek,%20FL&to=200
            querystring = {
                "Operation": "GetAddress",
                "clientAppName": "PropertySearch",
                "myUnit": "",
                "from": "1",
                "myAddress": f"{address['streetNumber']} {address['streetDirection']} {address['street']}",
                "to": "200"
            }

            response = requests.get(url, params=querystring)

            data = response.json()
            if data["Completed"]:
                # print(data)
                # print(data.get("MinimumPropertyInfos", {})[0].get("Strap", None))
                unformatted = cls.safe_list_get(data.get("MinimumPropertyInfos", [{}]), 0).get("Strap", "")
                return "".join(unformatted.split("-")), {"status": "success", "message": ""}
            
            else:
                return None, {"status": "error", "message": f"Unable to find Folio for: {data}"}
    
    @classmethod
    def appraiserInfoByFolio(cls, folio:str, client:Client) -> set[AppraiserInfo, dict]:
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

        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        
        if data["PropertyInfo"]["FolioNumber"]:
            return AppraiserInfo(data, client, cls.__translate), {"status": "success", "message": ""}
        
        else:
            return None, {"status": "error", "message": "Unable to find Appraiser Info"}
    
    @classmethod
    def appraiserInfoByAddressInfo(cls, search:AddressInfo, client:Client) -> set[AppraiserInfo, dict]:
        """just implements the appraiser info by folio with the address info. We use the Client to validate mailing addresses"""
        folio, error = cls.folioByAddressInfo(search)
        if error["status"] == "error":
            return None, error
        
        else:
            return cls.appraiserInfoByFolio(folio, client)
        
    @classmethod
    def getPropertyLinesByFolio(cls, folio:str) -> set[list, dict]:
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
            return transformed_rings, {"status": "success", "message": ""}
        
        except:
            return None, {"status": "error", "message": "Cannot find property lines for folio"}

    @classmethod
    def getScreenshotByFolio(cls, folio:str) -> set[bool, dict]:
        """just returns the screenshot for an address"""
        raise NotImplementedError
    
    @classmethod
    def __translate(cls, data:dict, client:Client) -> set[dict, dict]:
        mailAddressInfo, errorHandler = client.getByAddress(f"{data['MailingAddress']['Address1']}, {data['MailingAddress']['City']}, {data['MailingAddress']['State']}")
        if errorHandler["status"] == "error":
            return None, errorHandler
        
        else:
            mailAddressInfo, errorHandler = mailAddressInfo.get()

            if errorHandler["status"] == "error":
                return None, errorHandler
            
            else:

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
                        "folio": data["PropertyInfo"]["FolioNumber"],
                        "parentFolio": data["PropertyInfo"].get("ParentFolio", ""),
                        "legal": data["LegalDescription"]["Description"],
                        "use": data["PropertyInfo"]["DORDescription"],
                        "subdivision": data["PropertyInfo"]["SubdivisionDescription"],
                        "blk": convert_to_int(lot_blk_info["blk"]),
                        "lot": convert_to_int(lot_blk_info["lot"]),
                        "plat": {
                            "book": convert_to_int(data["PropertyInfo"]["PlatBook"]),
                            "page": convert_to_int(data["PropertyInfo"]["PlatPage"]),
                        },
                        "lotSize": data["PropertyInfo"]["LotSize"],
                        "otherRecords": lot_blk_info["otherRecords"]
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
                }, {"status": "success", "message": ""}


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