from ...Florida import Florida
from CentralizedAppraiser import AddressInfo, AppraiserInfo, Client
from CentralizedAppraiser.utils import convert_to_int

import re
import json
import pyproj
import requests

class Broward(Florida, Florida.County):
    
    @classmethod
    def folioByAddressInfo(cls, search:AddressInfo) -> set[str, dict]:
        """just returns the folio for an address"""
        address, errorHandler = search.get()

        if errorHandler["status"] == "error":
            return None, errorHandler
        
        else:
            address = address["addressComponents"]
            addressString = f"{address['streetNumber']} {address['streetDirection']} {address['street']}"

            url = "https://web.bcpa.net/BcpaClient/search.aspx/GetData"

            payload = "{value: \"" + addressString + "\",cities: \"\",orderBy: \"NAME\",pageNumber:\"1\",pageCount:\"5000\",arrayOfValues:\"\", selectedFromList: \"false\",totalCount:\"Y\"}"
            headers = {
                "host": "web.bcpa.net",
                "connection": "keep-alive",
                "sec-ch-ua": "\"Google Chrome\";v=\"123\", \"Not:A-Brand\";v=\"8\", \"Chromium\";v=\"123\"",
                "accept": "application/json, text/javascript, */*; q=0.01",
                "content-type": "application/json; charset=UTF-8",
                "x-requested-with": "XMLHttpRequest",
                "sec-ch-ua-mobile": "?0",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "sec-ch-ua-platform": "\"Windows\"",
                "origin": "https://web.bcpa.net",
                "sec-fetch-site": "same-origin",
                "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty",
                "referer": "https://web.bcpa.net/BcpaClient/",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "en-US,en;q=0.9",
                # "cookie": "_ga_MR45PG8FRP=GS1.1.1712895245.1.0.1712895245.0.0.0; _ga=GA1.1.2105266168.1712895245"
            }

            response = requests.post(url, data=payload, headers=headers)

            data = response.json()
            
            folio = cls.safe_list_get(data.get("d", {}).get("resultListk__BackingField", [{}]), 0).get("folioNumber", "")
            if folio:
                return folio, errorHandler
            else:
                return None, {"status": "error", "message": f"Cannot find a folio for {address['streetNumber']} {address['streetDirection']} {address['street']}"}
    
    @classmethod
    def appraiserInfoByFolio(cls, folio:str, client:Client) -> set[AppraiserInfo, dict]:
        """just returns the appraiser info for a folio. We use the Client to validate mailing addresses"""
        url = "https://web.bcpa.net/BcpaClient/search.aspx/getParcelInformation"

        payload = "{folioNumber: \"" + folio + "\",taxyear: \"2024\",action: \"CURRENT\",use:\"\"}"
        headers = {
            "host": "web.bcpa.net",
            "connection": "keep-alive",
            "sec-ch-ua": "\"Google Chrome\";v=\"123\", \"Not:A-Brand\";v=\"8\", \"Chromium\";v=\"123\"",
            "accept": "application/json, text/javascript, */*; q=0.01",
            "content-type": "application/json; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "sec-ch-ua-mobile": "?0",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "sec-ch-ua-platform": "\"Windows\"",
            "origin": "https://web.bcpa.net",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "referer": "https://web.bcpa.net/BcpaClient/",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9",
            "cookie": "_ga_MR45PG8FRP=GS1.1.1712895245.1.0.1712895245.0.0.0; _ga=GA1.1.2105266168.1712895245"
        }

        response = requests.post(url, data=payload, headers=headers)

        data = response.json()
        return AppraiserInfo(data, client, cls.__translate), {"status": "success", "message": ""}
    
    @classmethod
    def appraiserInfoByAddressInfo(cls, search:AddressInfo, client:Client) -> set[AppraiserInfo, dict]:
        """just implements the appraiser info by folio with the address info. We use the Client to validate mailing addresses"""
        folio, errorHandler = cls.folioByAddressInfo(search)
        
        if errorHandler["status"] == "error":
            return None, errorHandler
        
        else:
            return cls.appraiserInfoByFolio(folio, client)
        
    @classmethod
    def getPropertyLinesByFolio(cls, folio:str) -> set[bool, dict]:
        """just returns the property lines for an address"""

        cookies = {
            'ASP.NET_SessionId': 's5mugupueegqdicbiquhzldy',
            '_gid': 'GA1.2.1787727042.1725253629',
            '_gat': '1',
            '_ga_VTXRBF0C53': 'GS1.2.1725253629.11.0.1725253629.0.0.0',
            '_ga': 'GA1.1.117651107.1723498703',
            '_ga_MR45PG8FRP': 'GS1.1.1725253632.17.0.1725253640.0.0.0',
        }

        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            # 'Cookie': 'ASP.NET_SessionId=s5mugupueegqdicbiquhzldy; _gid=GA1.2.1787727042.1725253629; _gat=1; _ga_VTXRBF0C53=GS1.2.1725253629.11.0.1725253629.0.0.0; _ga=GA1.1.117651107.1723498703; _ga_MR45PG8FRP=GS1.1.1725253632.17.0.1725253640.0.0.0',
            'Pragma': 'no-cache',
            'Referer': 'https://gisweb-adapters.bcpa.net/bcpawebmap_ex/bcpawebmap.aspx',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }

        params = {
            'f': 'json',
            'searchText': folio,
            'contains': 'true',
            'returnGeometry': 'true',
            'layers': '16',
            'searchFields': 'FOLIO',
        }

        response = requests.get(
            'https://gisweb-adapters.bcpa.net/arcgis/rest/services/BCPA_EXTERNAL_JAN24/MapServer/find',
            params=params,
            cookies=cookies,
            headers=headers,
        )

        try:
            data = response.json()

            # Extract the rings from the geometry
            rings = data['results'][0]['geometry']['rings']

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
    def __translate(cls, data: dict, client: Client) -> tuple[dict, dict]:
        # Extract mailing address information
        mailing_address = f"{data['d']['parcelInfok__BackingField'][0]['mailingAddress1']}, {data['d']['parcelInfok__BackingField'][0]['mailingAddress2']}"
        mailAddressInfo, errorHandler = client.getByAddress(mailing_address)
        
        if errorHandler["status"] == "error":
            return None, errorHandler
        
        else:
            mailAddressInfo, errorHandler = mailAddressInfo.get()
            
            if errorHandler["status"] == "error":
                return None, errorHandler
            
            else:
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
                    "folio": data['d']['parcelInfok__BackingField'][0]['folioNumber'],
                    "parentFolio": data['d']['parcelInfok__BackingField'][0].get("parentFolio", ""),
                    "legal": data['d']['parcelInfok__BackingField'][0]["legal"],
                    "use": data['d']['parcelInfok__BackingField'][0]["useCode"],
                    "subdivision": lot_blk_info["subdivision"],
                    "blk": convert_to_int(lot_blk_info["blk"]),
                    "lot": convert_to_int(lot_blk_info["lot"]),
                    "plat": {
                        "book": convert_to_int(lot_blk_info["pb"]),
                        "page": convert_to_int(lot_blk_info["pg"]),
                    },
                    "lotSize": lotSize, #TODO: Just calculate this from parcel border
                    "otherRecords": []
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
                    "assessments": assessments,
                    "propertyInfo": property_info,
                    "owners": owners,
                    "unStructured": data
                }, {"status": "success", "message": ""}