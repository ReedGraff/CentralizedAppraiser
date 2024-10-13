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
        url = "https://web.bcpa.net/BcpaClient/search.aspx/getParcelInformation"

        headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-language': 'en-US,en;q=0.9,es;q=0.8',
            'content-type': 'application/json; charset=UTF-8',
            'origin': 'https://web.bcpa.net',
            'referer': 'https://web.bcpa.net/BcpaClient/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }

        payload = {
            "folioNumber": folio,
            "taxyear": "2025",
            "action": "CURRENT",
            "use": ""
        }

        async with self.semaphore:
            for attempt in range(max_tries):
                proxy = self.proxy.get()
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                        async with session.post(url, proxy=proxy, json=payload, headers=headers) as response:
                            if response.status == 200:
                                responseText = await response.text()
                                dictResponse = json.loads(responseText)
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
        """Appraiser Info Translation"""
        # Extract mailing address information
        if data['d']['parcelInfok__BackingField'] is None:
            raise TranslationError("No data found for folio")
        
        # Address Info
        try:
            address = f"{data['d']['parcelInfok__BackingField'][0]['situsAddress1']}, {data['d']['parcelInfok__BackingField'][0]['situsCity']}, {data['d']['parcelInfok__BackingField'][0]['situsZipCode']}"
            addressInfo = client.getByAddress(address, **data.get("kwargs", {}))
            addressInfo = addressInfo.get()
        except Exception as e:
            print(e.with_traceback(e.__traceback__))
            raise TranslationError("Error translating mailing address")

        # Mailing Address Info
        try:
            mailing_address = f"{data['d']['parcelInfok__BackingField'][0]['mailingAddress1']}, {data['d']['parcelInfok__BackingField'][0]['mailingAddress2']}"
            mailAddressInfo = client.getByAddress(mailing_address)
            mailAddressInfo = mailAddressInfo.get()
        except Exception as e:
            print(e.with_traceback(e.__traceback__))
            raise TranslationError("Error translating mailing address")

        from datetime import date
        # Extract assessments
        assessments = [
            {
                "assessedValue": convert_to_int(data['d']['parcelInfok__BackingField'][0]['sohValue']),
                "buildingValue": convert_to_int(data['d']['parcelInfok__BackingField'][0]['bldgValue']),
                "landValue": convert_to_int(data['d']['parcelInfok__BackingField'][0]['landValue']),
                "totalValue": convert_to_int(data['d']['parcelInfok__BackingField'][0]['totalValue']),
                "year": date.today().year
            },
            {
                "assessedValue": convert_to_int(data['d']['parcelInfok__BackingField'][0]['sohLastYearValue']),
                "buildingValue": convert_to_int(data['d']['parcelInfok__BackingField'][0]['bldgLastYearValue']),
                "landValue": convert_to_int(data['d']['parcelInfok__BackingField'][0]['landLastYearValue']),
                "totalValue": convert_to_int(data['d']['parcelInfok__BackingField'][0]['totalValue']),
                "year": date.today().year-1
            }
        ]

        # Extract property info
        if lotSize := data['d']['parcelInfok__BackingField'][0]['landCalcFact1']:
            lotSize = data['d']['parcelInfok__BackingField'][0]['landCalcFact1'].split(" ")[0]
            lotSize = convert_to_int(lotSize)


        def parse_property_info(text):
            # Patterns to match subdivision, pb, pg, lot, and blk
            pattern = re.compile(r'([A-Z\s]+)\s(\d+)-(\d+)\sB(?:\sLOT\s(\d+))?(?:\sBLK\s(\d+))?')

            match = pattern.search(text)
            
            if match:
                subdivision, pb, pg, lot, blk = match.groups()
                return {
                    "subdivision": subdivision.strip(),
                    "pb": int(pb),
                    "pg": int(pg),
                    "lot": lot if lot else None,
                    "blk": blk if blk else None
                }
            else:
                return {
                    "subdivision": None,
                    "pb": None,
                    "pg": None,
                    "lot": None,
                    "blk": None
                }

        
        lot_blk_info = parse_property_info(data['d']['parcelInfok__BackingField'][0]["legal"])

        property_info = {
            "parentFolio": data['d']['parcelInfok__BackingField'][0].get("parentFolio", ""),
            "legal": data['d']['parcelInfok__BackingField'][0]["legal"],
            "use": data['d']['parcelInfok__BackingField'][0]["useCode"],
            "subdivision": lot_blk_info["subdivision"],
            "blk": convert_to_int(lot_blk_info["blk"]),
            "lot": convert_to_int(lot_blk_info["lot"]),
            "lotSize": lotSize, #TODO: Just calculate this from parcel border
            "records": [
                {
                    "type": "plat",
                    "book": convert_to_int(lot_blk_info["pb"]),
                    "page": convert_to_int(lot_blk_info["pg"])
                }
            ]
        }
        
        # Extract owners
        owners = [
            {
                "name": data['d']['parcelInfok__BackingField'][0]['ownerName1'],
                "mailingAddresses": [
                    mailAddressInfo
                ]
            }
        ]
        
        # Return structured data
        return {
            "locationInfo": addressInfo,
            "assessments": assessments,
            "propertyInfo": property_info,
            "owners": owners,
            "unStructured": data
        }