import asyncio
from CentralizedAppraiser.abstracts._address import AppraiserInfo
from CentralizedAppraiser.abstracts._client import Client
from CentralizedAppraiser.abstracts._exceptions import AppraiserRequestError, TranslationError
from CentralizedAppraiser.abstracts._proxy import Proxy
from CentralizedAppraiser.utils import convert_to_int
from .. import Florida

# 
import re
import json
import logging
import aiohttp

# for all of the appraiser info collection
class Collect:
    def __init__(self, **kwargs):
        raise NotImplementedError

    async def appraiserInfoByFolio(self, folio: str, max_tries=3, backoff_factor=0.3, **kwargs):
        """Just returns the appraiser info for a folio. We use the Client to validate mailing addresses"""
        url = "https://www.miamidade.gov/Apps/PA/PApublicServiceProxy/PaServicesProxy.ashx"

        querystring = {
            "Operation": "GetPropertySearchByFolio",
            "clientAppName": "PropertySearch",
            "folioNumber": folio.replace("-", "")
        }

        async with self.semaphore:
            for attempt in range(max_tries):
                proxy = self.proxy.get()
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                        async with session.get(url, proxy=proxy, params=querystring) as response:
                            if response.status == 200:
                                dictResponse = json.loads(await response.text())
                                dictResponse["kwargs"] = kwargs
                                return AppraiserInfo(dictResponse, self.addressClient, Collect.__translate)
                            if attempt == max_tries - 1:
                                response.raise_for_status()
                except Exception as e:
                    print(f"Exception on attempt {attempt + 1}: {e}")
                    if attempt < max_tries - 1:
                        await asyncio.sleep(backoff_factor * (2 ** attempt))
                    else:
                        print(f"Failed to fetch appraiser info after {max_tries} attempts")
                        return AppraiserInfo({}, self.addressClient, Collect.__translate)



    
    async def getPropertyLinesByFolio(self, folio:str) -> list:
        """just returns the property lines for an address"""
        # list is just a list of lists of coordinates [[(lon, lat), (lon, lat), ...], [(lon, lat), (lon, lat), ...], ...]
        raise NotImplementedError
    
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