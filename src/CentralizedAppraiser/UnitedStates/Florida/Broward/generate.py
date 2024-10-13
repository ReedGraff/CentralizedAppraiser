import os
from typing import AsyncGenerator, Dict, List
import pandas as pd
from pymongo import InsertOne, MongoClient, UpdateOne
from pymongo.errors import AutoReconnect
from CentralizedAppraiser.utils import esri_to_geojson, make_grid, project_coordinates
from .. import Florida
from .collect import Collect

# Localized Imports
import json
import asyncio
import pyproj
import aiohttp
import shapely
import geopandas as gpd
import aiofiles

class Generate:
    def __init__(self, **kwargs):
        raise NotImplementedError



    async def generate(self):
        """gets the lines for the county, and runs __getGeoDataFrame for the whole county"""
        # Get the county property lines
        geoJ = Florida.getGeometryFeature("Broward")
        shapeJ = shapely.geometry.shape(geoJ["geometry"])
        # shapeJ = shapely.geometry.shape({
        #     "type": "MultiPolygon",
        #     "coordinates": [ [ [ 
        #         [ -80.1870221248645, 26.170591170872424 ],  # bl
        #         [ -80.18709157357678, 26.17404755264814 ], # tl
        #         [ -80.17929170991484, 26.173190596742863 ], # tr
        #         [ -80.17966721915607, 26.17012861303484 ], # br
        #         [ -80.1870221248645, 26.170591170872424 ], # bl
        #     ] ] ]
        #     # "coordinates": [ [ [ # whole city block
        #     #     [ -80.31292651623156, 26.04413847907943 ],  # bl
        #     #     [ -80.3132782672325, 26.063552091888823 ], # tl
        #     #     [ -80.25234239901881, 26.064633056569406 ], # tr
        #     #     [ -80.25178069187123, 26.045455007308075 ], # br
        #     #     [ -80.31292651623156, 26.04413847907943 ], # bl
        #     # ] ] ]
        # })
        # grid = [
        #     ((26.17313278850428, -80.20330192811147),
        #     (26.180352448742266, -80.19554944996895))
        # ]

        # Save the grid to a json file
        grid = make_grid(shapeJ, 1*1609.34)  # 1 mile for property search
        gridDict = [
            {
                "searched": False,
                "enriched": False,
                "sw": {
                    "lat": box[0][0],
                    "lng": box[0][1]
                },
                "ne": {
                    "lat": box[1][0],
                    "lng": box[1][1]
                },
                "apns": []
            } for box in grid
        ]
        # json.dump(gridDict, open(os.path.join(self.__location__, '_data/_grids.json'), 'w'), indent=2)
        
        ### Search and save each grid to its own file.
        tasks = []
        for index, gridObj in enumerate(gridDict):
            task = asyncio.create_task(self.collectGrid(gridObj, index))
            tasks.append(task)
        
        gridDict = await asyncio.gather(*tasks)
        json.dump(gridDict, open(os.path.join(self.__location__, '_data/_grids.json'), 'w'), indent=2)

        ### Clean DB and remove duplicate apns
        gridDict = await self.cleanGrids(gridDict)
        json.dump(gridDict, open(os.path.join(self.__location__, '_data/_grids.json'), 'w'), indent=2)
        
        ### Enrich the data # BLOCKING #
        tasks = []
        for index, gridObj in enumerate(gridDict):
            print(f"Enriching grid: {index}")
            task = await self.enrichGrid(gridObj, index)
            tasks.append(task)
        
        gridDict = tasks
        json.dump(gridDict, open(os.path.join(self.__location__, '_data/_grids.json'), 'w'), indent=2)

        raise Exception("Done")
        
        ### Upload the data to MongoDB
        for index, gridObj in enumerate(gridDict):
            print(f"Enriching grid: {index}")
            await self.uploadGridFiles(gridObj, index)



    async def collectGrid(self, grid_obj: Dict, name: str) -> Dict:
        """
        1. Collects the grid data and saves it to a file.
        2. Returns the grid object with the APNs collected.
        """
        print(f"Collecting grid: {name}")
        
        file_path = os.path.join(self.__location__, f'_data/_grids/{name}.json')
        apns: List[str] = []

        async with aiofiles.open(file_path, 'a') as file:
            async for chunk in self.get_geo_data(grid_obj["sw"], grid_obj["ne"]):
                geo_chunk = esri_to_geojson(chunk)
                filtered_chunk = Generate.filterJson(geo_chunk)

                for feature in filtered_chunk["features"]:
                    # Write each feature as a separate line in the file
                    await file.write(json.dumps(feature) + '\n')
                    
                    # Collect APNs
                    apn = feature["properties"].get("apn")
                    if apn:
                        apns.append(apn)

        # Update grid object
        grid_obj["apns"] = list(apns)
        grid_obj["searched"] = True

        return grid_obj



    async def enrichGrid(self, grid_obj: Dict, name: str) -> Dict:
        """
        1. Iterate through each apn object in the grid.
        2. Collect the appraiser info for each apn.
        3. Save the appraiser info into a variable.
        4. Save the appraiser info into a file line by line maintaining the order of the apns.
        """
        print(f"Collecting grid: {name}")
        
        file_path = os.path.join(self.__location__, f'_data/_grids/{name}.json')

        geojsonObjs = []
        appraiserInfo = []
        for index, apn in enumerate(grid_obj["apns"]):
            async with aiofiles.open(file_path, 'r') as file:
                lines = await file.readlines()
                geojsonObj = json.loads(lines[index])

            # convert the coordinates to longitute and latitude
            src_proj = pyproj.CRS('EPSG:2236')  # WKID 2236 (Florida East)
            dst_proj = pyproj.CRS('EPSG:4326')  # WGS84 (longitude, latitude)
            transformer = pyproj.Transformer.from_crs(src_proj, dst_proj, always_xy=True)
            transformed_rings = list(map(lambda ring: list(map(lambda coord: transformer.transform(coord[0], coord[1]), ring)), geojsonObj["geometry"]["coordinates"]))
            geojsonObj["geometry"]["coordinates"] = transformed_rings

            # append the geojson object to the list
            geojsonObjs.append(geojsonObj)
            
            # Get the centroid of the geometry
            centroid = shapely.geometry.shape(geojsonObj["geometry"]).centroid
            referencePoint = [centroid.y, centroid.x]

            # Get appraiser info
            appraiserInfo.append(asyncio.create_task(self.appraiserInfoByFolio(apn, coords=referencePoint)))

        # Save the appraiser info into a file
        appraiserInfo = await asyncio.gather(*appraiserInfo)
        async with aiofiles.open(os.path.join(self.__location__, f'_data/_appraisers/{name}.json'), 'a') as f:
            for appraiserDictIndex in range(len(appraiserInfo)):
                appraiserDict = appraiserInfo[appraiserDictIndex]
                template = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": geojsonObjs[appraiserDictIndex]["geometry"]["coordinates"]
                    },
                    "properties": {
                        "apn": geojsonObjs[appraiserDictIndex]["properties"]["apn"],
                        "locationInfo": None,
                        "assessments": None,
                        "propertyInfo": None,
                        "owners": None,
                        "unStructured": None
                    }
                }

                try:
                    template["properties"].update(appraiserDict.get())
                except Exception as e:
                    print("Error updating template properties: ", e)
                    pass
                await f.write(json.dumps(template) + '\n')

        # Update grid object
        grid_obj["enriched"] = True

        return grid_obj
    
    async def uploadGridFiles(self, grid_obj: Dict, name: str, client: MongoClient, batch_size: int = 1000) -> None:
        if len(grid_obj["apns"]) > 0:
            db = client['UnitedStates+Florida']
            collection = db['Broward']

            # Disable index creation since you're not checking for duplicates
            # You can also remove any existing indexes if needed to improve performance
            
            async with aiofiles.open(os.path.join(self.__location__, f'_data/_appraisers/{name}.json'), 'r') as file:
                operations = []
                async for line in file:
                    geojson_obj = json.loads(line)

                    operations.append(geojson_obj)  # Just append the GeoJSON for insertion

                    # Process in larger batches
                    if len(operations) >= batch_size:
                        collection.insert_many(operations, ordered=False)  # Use InsertMany, set ordered=False for faster insertions
                        operations = []  # Clear the operations list after each batch

                # Handle remaining operations
                if operations:
                    collection.insert_many(operations, ordered=False)
                    
            print(f"GeoJSON data has been inserted into MongoDB for grid object {name}")
        else:
            print(f"No APNs found in grid object {name}. Skipping upload to MongoDB.")

    
    async def get_geo_data(self, sw, ne, chunk_size: int = 1000) -> AsyncGenerator[Dict, None]:
        result_offset = 0
        while True:
            chunk = await self.__get_geo_data_chunk(sw, ne, result_offset, chunk_size)
            if len(chunk.get("features", [])) == 0:
                break
            yield chunk
            result_offset += chunk_size

    async def __get_geo_data_chunk(self, sw, ne, result_offset: int, chunk_size: int, max_tries: int = 3, backoff_factor: float = 0.5) -> Dict:
        print(f"Getting GeoDataFrame chunk for {sw} to {ne} on offset {result_offset}")
        swLat, swLng = sw["lat"], sw["lng"]
        neLat, neLng = ne["lat"], ne["lng"]

        projected1x, projected1y = project_coordinates(swLng, swLat, 2236)
        projected2x, projected2y = project_coordinates(neLng, neLat, 2236)

        # https://gisweb-adapters.bcpa.net/arcgis/rest/services/BCPA_EXTERNAL_OCT24/MapServer/export?dpi=96&transparent=true&format=png8&layers=show%3A-1%2C16&bbox=929376.3360024331%2C689087.2022941001%2C931840.9193357663%2C690599.7022941001&bboxSR=102658&imageSR=102658&size=1183%2C726&f=image
        url = (
            # 'https://gisweb-adapters.bcpa.net/arcgis/rest/services/BCPA_EXTERNAL_JAN24/MapServer/16/query'
            'https://gisweb-adapters.bcpa.net/arcgis/rest/services/BCPA_EXTERNAL_OCT24/MapServer/16/query'
            '?f=json'
            '&geometry={"xmin":' + str(projected1x) + ',"ymin":' + str(projected1y) + ',"xmax":' + str(projected2x) + ',"ymax":' + str(projected2y) + '}'
            '&outFields=*'
            '&spatialRel=esriSpatialRelIntersects'
            '&where=1=1'
            '&geometryType=esriGeometryEnvelope'
            # '&resultRecordCount=' + str(chunk_size) +
            # '&resultOffset=' + str(result_offset)
        )
        print(url)
        # 931309.6693357665,693317.4106274332, 933270.0860024332,695144.4939607665

        # the october map throws errors with resultoffset... so we'll just throw an error if there is a resultoffset
        if result_offset > 0:
            return {}

        async with self.semaphore:
            for attempt in range(max_tries):
                proxy = self.proxy.get()
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                        async with session.get(url, proxy=proxy) as response:
                            if response.status == 200:
                                return await response.json()
                            if attempt == max_tries - 1:
                                response.raise_for_status()
                except Exception as e:
                    print(f"Exception on attempt {attempt + 1}: {e}")
                    if attempt < max_tries - 1:
                        await asyncio.sleep(backoff_factor * (2 ** attempt))
                    else:
                        print(f"Failed to fetch appraiser info after {max_tries} attempts")
                        return {}
    


    async def cleanGrids(self, gridDict: List[Dict]) -> Dict:
        """
        Iterate through each grid, delete duplicate APNs, and merge geometries.
        """
        apn_dict = {}
        merged_geometries = {}

        # First pass: collect all APNs and their locations
        for grid_index, grid in enumerate(gridDict):
            for apn_index, apn in enumerate(grid['apns']):
                if apn not in apn_dict:
                    apn_dict[apn] = []
                apn_dict[apn].append((grid_index, apn_index))

        # Save APN dictionary for reference
        with open(os.path.join(self.__location__, '_data/_apn_dict.json'), 'w') as f:
            json.dump(apn_dict, f, indent=2)

        # Second pass: merge geometries and update files
        for apn, locations in apn_dict.items():
            if len(locations) > 1:
                print(f"Merging APN: {apn}")
                geometries_to_merge = []

                for grid_index, apn_index in locations:
                    file_path = os.path.join(self.__location__, f'_data/_grids/{grid_index}.json')
                    
                    async with aiofiles.open(file_path, 'r') as file:
                        lines = await file.readlines()
                        geometry = json.loads(lines[apn_index])
                        geometries_to_merge.append(geometry)

                # Merge geometries
                merged_geometry = await self.mergeObjects(*geometries_to_merge)
                merged_geometries[apn] = merged_geometry

        # Third pass: update grid files and gridDict
        for grid_index, grid in enumerate(gridDict):
            file_path = os.path.join(self.__location__, f'_data/_grids/{grid_index}.json')
            new_apns = []
            new_lines = []

            async with aiofiles.open(file_path, 'r') as file:
                lines = await file.readlines()

            for apn_index, apn in enumerate(grid['apns']):
                if apn in merged_geometries:
                    if apn_dict[apn][0] == (grid_index, apn_index):  # First occurrence
                        new_apns.append(apn)
                        new_lines.append(json.dumps(merged_geometries[apn]) + '\n')
                else:
                    new_apns.append(apn)
                    new_lines.append(lines[apn_index])

            # Update gridDict
            grid['apns'] = new_apns

            # Write updated lines to file
            async with aiofiles.open(file_path, 'w') as file:
                await file.writelines(new_lines)

        return gridDict



    async def mergeObjects(self, *objects) -> Dict:
        # Create a new object with the desired structure
        consolidated_object = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": []
            },
            "properties": {
                "apn": objects[0]["properties"]["apn"]
            }
        }

        # Create a set to track unique rings
        unique_rings = set()

        # Extract coordinates from each object
        for obj in objects:
            if "geometry" in obj and "coordinates" in obj["geometry"]:
                for ring in obj["geometry"]["coordinates"]:
                    # Convert the ring to a tuple of tuples for hashability
                    ring_tuple = tuple(map(tuple, ring))
                    # Check if the ring is unique
                    if ring_tuple not in unique_rings:
                        unique_rings.add(ring_tuple)
                        consolidated_object["geometry"]["coordinates"].append(ring)

        return consolidated_object



    @classmethod
    def filterJson(cls, obj: dict) -> dict:
        """Rename according to structure of this specific esri geojson"""
        keysToKeep = ["FOLIO"]
        KeysToRename = {
            "FOLIO": "apn"
        }

        for feature in obj['features']:
            # Keep only specified keys
            keys_to_remove = [key for key in feature['properties'] if key not in keysToKeep]
            for key in keys_to_remove:
                del feature['properties'][key]
            
            # Rename keys according to KeysToRename
            for old_key, new_key in KeysToRename.items():
                if old_key in feature['properties']:
                    feature['properties'][new_key] = feature['properties'].pop(old_key)

        return obj