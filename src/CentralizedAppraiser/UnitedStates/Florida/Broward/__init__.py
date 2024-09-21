from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import shapely
from ...Florida import Florida
from CentralizedAppraiser import AddressInfo, AppraiserInfo, Client, TranslationError, TranslationInvalid
from CentralizedAppraiser.utils import convert_to_int, esri_to_geojson, make_grid, project_coordinates
from tenacity import retry, stop_after_attempt, wait_exponential

import re
import json
import pyproj
import requests
import geopandas as gpd

class Broward(Florida, Florida.County):

    @classmethod
    def appraiserInfoByFolio(cls, folio:str, client:Client, **kwargs) -> AppraiserInfo:
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

        response = requests.post(url, data=payload, headers=headers, timeout=15)

        data = response.json()
        data["kwargs"] = kwargs
        return AppraiserInfo(data, client, cls.__translate)
        
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
    def getScreenshotByFolio(cls, folio:str) -> str:
        """just returns the screenshot for an address"""
        raise NotImplementedError

    @classmethod
    def __translate(cls, data: dict, client: Client) -> tuple[dict, dict]:
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

    @classmethod
    def generate(cls, addressClient) -> gpd.GeoDataFrame:
        """gets the lines for the county, and runs __getGeoDataFrame for the whole county"""
        concurrent = 200  # Number of concurrent threads

        # Get the county property lines
        geoJ = Florida.getGeometryFeature("Broward")
        shapeJ = shapely.geometry.shape(geoJ["geometry"])
        grid = make_grid(shapeJ, 1609.34)  # 1 mile for property search
        # grid = [
        #     ((26.17313278850428, -80.20330192811147),
        #     (26.180352448742266, -80.19554944996895))
        # ]

        results = gpd.GeoDataFrame()
        unique_objectids = set()

        @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10))
        def fetch_property_info(folio, addressClient, **kwargs):
            info = cls.appraiserInfoByFolio(folio, addressClient, **kwargs)
            info = info.get()
            info['folio'] = folio
            return info

        def process_folio(folio, **kwargs):
            try:
                return fetch_property_info(folio, addressClient, **kwargs)
            except (TranslationError, TranslationInvalid) as e:
                print(f"Error processing folio {folio}: {e}")
                return None
            except Exception as e:
                print(f"Unhandled error processing folio {folio}: {e}")
                return None

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

                # Use ThreadPoolExecutor to process folios concurrently
                with ThreadPoolExecutor(max_workers=concurrent) as executor:
                    future_to_folio = {}
                    transformer = pyproj.Transformer.from_crs('EPSG:2236', 'EPSG:4326', always_xy=True)
                    
                    for folio, geometry in zip(Data['FOLIO'], Data['geometry']):
                        # Get unique reference point for each item
                        referencePoint = geometry.centroid
                        referencePoint = transformer.transform(referencePoint.x, referencePoint.y)
                        referencePoint = (referencePoint[1], referencePoint[0])
                        
                        # Submit task with unique reference point
                        future = executor.submit(process_folio, folio, coords=referencePoint)
                        future_to_folio[future] = folio
                    
                    additional_data = []
                    for future in as_completed(future_to_folio):
                        result = future.result()
                        if result:
                            additional_data.append(result)

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
            'https://gisweb-adapters.bcpa.net/arcgis/rest/services/BCPA_EXTERNAL_JAN24/MapServer/16/query'
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