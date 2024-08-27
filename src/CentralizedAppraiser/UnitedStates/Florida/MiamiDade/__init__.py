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
                "myAddress": f"{address["streetNumber"]} {address["streetDirection"]} {address["street"]}",
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
            return None, {"status": "error", "message": f"Unable to find Appraiser Info"}
    
    @classmethod
    def appraiserInfoByAddressInfo(cls, search:AddressInfo, client:Client) -> set[AppraiserInfo, dict]:
        """just implements the appraiser info by folio with the address info. We use the Client to validate mailing addresses"""
        folio, error = cls.folioByAddressInfo(search)
        if error["status"] == "error":
            return None, error
        
        else:
            return cls.appraiserInfoByFolio(folio, client)

    @classmethod
    def getScreenshotByFolio(cls, folio:str) -> set[bool, dict]:
        """just returns the screenshot for an address"""
        raise NotImplementedError
    
    @classmethod
    def __translate(cls, data:dict, client:Client) -> set[dict, dict]:
        mailAddressInfo, errorHandler = client.getByAddress(f"{data["MailingAddress"]["Address1"]}, {data["MailingAddress"]["City"]}, {data["MailingAddress"]["State"]}")
        if errorHandler["status"] == "error":
            return None, errorHandler
        
        else:
            mailAddressInfo, errorHandler = mailAddressInfo.get()

            if errorHandler["status"] == "error":
                return None, errorHandler
            
            else:

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
                        "subdivision": data["PropertyInfo"]["SubdivisionDescription"],
                        "blk": convert_to_int(data["PropertyInfo"]["PlatBook"]),
                        "lot": convert_to_int(data["PropertyInfo"]["PlatPage"]),
                        "plat": {
                            "book": convert_to_int(data["PropertyInfo"]["PlatBook"]),
                            "page": convert_to_int(data["PropertyInfo"]["PlatPage"]),
                        },
                        "lotSize": data["PropertyInfo"]["LotSize"],
                        "otherRecords": [
                            {
                                "type": "Legal",
                                "book": convert_to_int(data["PropertyInfo"]["PlatBook"]),
                                "page": convert_to_int(data["PropertyInfo"]["PlatPage"]),
                            }
                        ]
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