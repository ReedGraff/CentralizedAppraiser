from ...Florida import Florida
from CentralizedAppraiser import AddressInfo, AppraiserInfo, Client
from CentralizedAppraiser.utils import convert_to_int

import re
import json
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
                # Extract assessments
                assessments = [
                    {
                        "assessedValue": convert_to_int(data['d']['parcelInfok__BackingField'][0]['assessedLastYearValue']),
                        "buildingValue": convert_to_int(data['d']['parcelInfok__BackingField'][0]['bldgLastYearValue']),
                        "landValue": convert_to_int(data['d']['parcelInfok__BackingField'][0]['landLastYearValue']),
                        "totalValue": convert_to_int(data['d']['parcelInfok__BackingField'][0]['totalValue']),
                        "year": int(data['d']['millageRatek__BackingField'][0]['millageYear']),
                    }
                ]

                # Extract property info
                if lotSize := data['d']['parcelInfok__BackingField'][0]['landCalcFact1']:
                    lotSize = data['d']['parcelInfok__BackingField'][0]['landCalcFact1'].split(" ")[0]
                    lotSize = convert_to_int(lotSize)

                property_info = {
                    "folio": data['d']['parcelInfok__BackingField'][0]['folioNumber'],
                    "parentFolio": data['d']['parcelInfok__BackingField'][0].get("parentFolio", ""),
                    "subdivision": data['d']['parcelInfok__BackingField'][0]['legal'],
                    "blk": convert_to_int(data['d']['parcelInfok__BackingField'][0]['bookAndPageOrCin1']),
                    "lot": convert_to_int(data['d']['parcelInfok__BackingField'][0]['bookAndPageOrCin2']),
                    "plat": {
                        "book": convert_to_int(data['d']['parcelInfok__BackingField'][0]['bookAndPageOrCin1']),
                        "page": convert_to_int(data['d']['parcelInfok__BackingField'][0]['bookAndPageOrCin2']),
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