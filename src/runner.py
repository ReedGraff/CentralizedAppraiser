import json
import CentralizedAppraiser
import asyncio
import geopandas as gpd

import CentralizedAppraiser.UnitedStates
import CentralizedAppraiser.UnitedStates.Florida
import CentralizedAppraiser.UnitedStates.Florida.Broward

# osmClient = CentralizedAppraiser.OSMAndUSAClient()
usaReverseClient = CentralizedAppraiser.USAReverseClient()
"""
mongoClientCreds = {
    "u": "ReedG",
    "p": "97eJPbuphnqRsIMl",
    "a": "ServerlessInstance0"
}

async def main():
    # Uncomment the lines below to test the functions
    # print(await CentralizedAppraiser.typeahead(mongoClientCreds, "123 Main St.", "UnitedStates.Florida.Broward"))
    # print(await CentralizedAppraiser.requestQueryAtPath(mongoClientCreds, {"$text": {"$search": "123 main"}}, "UnitedStates.Florida.Broward"))
    # print(await CentralizedAppraiser.requestQueryAtPath(mongoClientCreds, {"properties.FOLIO": "513701000000"}, "UnitedStates.Florida.Broward"))
    print(await CentralizedAppraiser.requestQueryAtPath(mongoClientCreds, {"properties.FOLIO": {"$regex": "51370"}}, "UnitedStates.Florida.Broward"))

# Run the main function
asyncio.run(main())
# print(CentralizedAppraiser.typeahead(mongoClientCreds, "123 Main St.", "UnitedStates.Florida.Broward"))
# print(CentralizedAppraiser.requestQueryAtPath(mongoClientCreds, {"$text": {"$search": "123 main"}}, "UnitedStates.Florida.Broward"))
# print(CentralizedAppraiser.requestQueryAtPath(mongoClientCreds, {"properties.FOLIO": "513701000000"}, "UnitedStates.Florida.Broward"))
# print(CentralizedAppraiser.requestQueryAtPath(mongoClientCreds, {"properties.FOLIO": {"$regex": "51370"}}, "UnitedStates.Florida.Broward"))
"""
# print(osmClient.getByAddress("3931 NW 36 TERRACE, LAUDERDALE LAKES, 33309-4803").get())

# async def main():
    # data:gpd.GeoDataFrame = CentralizedAppraiser.generateAtPath("UnitedStates.Florida.Broward", gClient)
CentralizedAppraiser.generateAllAtPath("UnitedStates.Florida.MiamiDade", usaReverseClient)
# asyncio.run(main())
# print(nomClient.getByAddress("9271 SW 94th CT, FL 33176. US", coords=(25.68302063761003, -80.34792602369171)).get())

"""
Unhandled error processing folio 504015010168: Key 'assessments' error:
Or({'assessedValue': And(<class 'int'>, <function AppraiserInfo.getSchema.<locals>.<lambda> at 0x00000154D7B2BF60>), 'buildingValue': And(<class 'int'>, <function AppraiserInfo.getSchema.<locals>.<lambda> at 0x00000154D7B2A840>), 'landValue': And(<class 'int'>, <function AppraiserInfo.getSchema.<locals>.<lambda> at 0x00000154D7B2B9C0>), 'totalValue': And(<class 'int'>, <function AppraiserInfo.getSchema.<locals>.<lambda> at 0x00000154D7B29F80>), 'year': <class 'int'>}) did not validate {'assessedValue': -794030, 'buildingValue': 0, 'landValue': 169440, 'totalValue': 0, 'year': 2024}
Key 'assessedValue' error:
"""
