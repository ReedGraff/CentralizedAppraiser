# other packages
import json
import shapely

# centralize appraiser [pip install CentralizedAppraiser]
import CentralizedAppraiser
from CentralizedAppraiser import GoogleClient

# local packages
from utils._intersectingTiles import getTilesForPolygonWithBuffer
from utils._imageGen import fetchAndStitchTiles
from utils._imageClients import getGoogleTiles, getMapboxTiles

# variables
address = "62 NE 78 ST. MIAMI"
zoom = 19 # zoom level for the tiles (google maps)
buffer = 0.0005 # buffer distance for the property lines

###
# Main Code
###
# get api key
with open("creds.txt", "r") as f:
    googleApiKey = f.readline().strip()

# get the data from the Centralized Appraiser package
client = GoogleClient(googleApiKey)
addressInfo, errorHandler = client.getByAddress(address)
classPointer, errorHandler = CentralizedAppraiser.classByAddressInfo(addressInfo)
appraiserInfo, errorHandler = CentralizedAppraiser.appraiserInfoByAddressInfo(addressInfo, client)
location, error = addressInfo.get()
data, error = appraiserInfo.get()

# generate the data.json file
json.dump(data, open("data.json", "w"), indent=4)

# get the property lines and convert them to a shapely polygon
propertyLines, errorHandler = classPointer.getPropertyLinesByFolio(data["propertyInfo"]["folio"])
propertyLines = [shapely.Polygon(ring) for ring in propertyLines]
propertyLines = shapely.geometry.MultiPolygon(propertyLines)

# get the tiles we need to fetch from google maps in order to cover the property lines with a buffer
tiles, adjustedPoly = getTilesForPolygonWithBuffer(propertyLines, zoom, desired_aspect_ratio=5.43 / 2.35, buffer_distance=buffer)
GooglePath = fetchAndStitchTiles(tiles, adjustedPoly, propertyLines, zoom, getGoogleTiles, token="AIzaSyCXT61vk2WlXPF5CWzsiig5Kknc-CGhcbU")

# get the MapBoxPath image from regrid
tiles, adjustedPoly = getTilesForPolygonWithBuffer(propertyLines, zoom, desired_aspect_ratio=1.87 / 2.35, buffer_distance=buffer)
MapBoxPath = fetchAndStitchTiles(tiles, adjustedPoly, propertyLines, zoom, getMapboxTiles, token="AIzaSyCXT61vk2WlXPF5CWzsiig5Kknc-CGhcbU")

# generate the word document
import datetime
from docxtpl import DocxTemplate
from docxtpl import InlineImage
from docx.shared import Inches
from docx2pdf import convert

wordTemplatePath = "Centralized Appraiser.docx"
today = datetime.datetime.today()
doc = DocxTemplate(wordTemplatePath)

owner1 = data["owners"][0] if len(data["owners"]) > 0 else None
owner1Address = owner1["mailingAddresses"][0] if owner1 and len(owner1["mailingAddresses"]) > 0 else None
owner2 = data["owners"][1] if len(data["owners"]) > 1 else None
owner2Address = owner2["mailingAddresses"][0] if owner2 and len(owner2["mailingAddresses"]) > 0 else None
owner3 = data["owners"][2] if len(data["owners"]) > 2 else None
owner3Address = owner3["mailingAddresses"][0] if owner3 and len(owner3["mailingAddresses"]) > 0 else None
owner4 = data["owners"][3] if len(data["owners"]) > 3 else None
owner4Address = owner4["mailingAddresses"][0] if owner4 and len(owner4["mailingAddresses"]) > 0 else None

assessments = data["assessments"][0] if len(data["assessments"]) > 0 else None
context = {
    "ADDRESS": location["formattedAddress"],
    "DATE": today.strftime("%Y-%m-%d"),

    "GOOGLEMAP_PHOTO": InlineImage(doc, GooglePath, height=Inches(2.35)),
    "ROADMAP_PHOTO": InlineImage(doc, MapBoxPath, height=Inches(2.35)),
    
    "LEGAL": f"{data["propertyInfo"]["legal"]}\n - {data["propertyInfo"]["use"]}",

    # Property Info
    "FOLIO": data["propertyInfo"]["folio"],
    "PARENT_FOLIO": data["propertyInfo"]["parentFolio"],
    "SUBDIVISION": data["propertyInfo"]["subdivision"],
    "BLK": data["propertyInfo"]["blk"],
    "LOT": data["propertyInfo"]["lot"],
    "PLAT": f"Plat book: {data["propertyInfo"]["plat"]["book"]} pg: {data["propertyInfo"]["plat"]["page"]}",
    "LOT_SIZE": data["propertyInfo"]["lotSize"],
    "OTHER_RECORDS": ", ".join([f"{record['type']} : {record['book']}-{record['page']}" for record in data["propertyInfo"]["otherRecords"]]),

    # Owner Info
    "OWNER_1_NAME": owner1["name"] if owner1 else "",
    "OWNER_1_ADDRESS": owner1Address["formattedAddress"] if owner1Address else "",
    "OWNER_2_NAME": owner2["name"] if owner2 else "",
    "OWNER_2_ADDRESS": owner2Address["formattedAddress"] if owner2Address else "",
    "OWNER_3_NAME": owner3["name"] if owner3 else "",
    "OWNER_3_ADDRESS": owner3Address["formattedAddress"] if owner3Address else "",
    "OWNER_4_NAME": owner4["name"] if owner4 else "",
    "OWNER_4_ADDRESS": owner4Address["formattedAddress"] if owner4Address else "",

    # Assessments
    "ASSESSED_VALUE": assessments["assessedValue"] if assessments else "",
    "BUILDING_VALUE": assessments["buildingValue"] if assessments else "",
    "LAND_VALUE": assessments["landValue"] if assessments else "",
    "TOTAL_VALUE": assessments["totalValue"] if assessments else "",
    "YEAR": assessments["year"] if assessments else "",
}

doc.render(context)
doc.save("_temp/output.docx")
convert("_temp/output.docx", "output.pdf")