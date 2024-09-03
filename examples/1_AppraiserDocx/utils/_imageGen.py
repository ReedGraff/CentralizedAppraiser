import os
from PIL import Image, ImageDraw
import shapely
import numpy as np
import uuid

from utils._geometry import lonLatToTile

def createTempDir():
    tempDir = '_temp'
    os.makedirs(tempDir, exist_ok=True)
    return tempDir

def fetchTiles(tiles, fetchTileFunc, tempDir, token=None):
    tilePaths = []
    for tile in tiles:
        z, y, x = tile
        tilePath, tileSize = fetchTileFunc(x, y, z, tempDir, token=token) # tileSize should remain constant for all tiles
        tilePaths.append((x, y, tilePath))
    return tilePaths, tileSize

def determineBoundingBox(tiles):
    xMin = min(tile[2] for tile in tiles)
    yMin = min(tile[1] for tile in tiles)
    xMax = max(tile[2] for tile in tiles)
    yMax = max(tile[1] for tile in tiles)
    return xMin, yMin, xMax, yMax

def stitchTiles(tilePaths, xMin, yMin, tileSize):
    numTilesX = max(x for x, y, path in tilePaths) - xMin + 1
    numTilesY = max(y for x, y, path in tilePaths) - yMin + 1
    stitchedImage = Image.new('RGB', (tileSize * numTilesX, tileSize * numTilesY))
    
    for x, y, tilePath in tilePaths:
        tileImage = Image.open(tilePath).convert('RGB')
        xOffset = (x - xMin) * tileSize
        yOffset = (y - yMin) * tileSize
        stitchedImage.paste(tileImage, (xOffset, yOffset))
    
    return stitchedImage

def convertPolygon(polygon, zoom):
    return shapely.Polygon([lonLatToTile(lon, lat, zoom) for lon, lat in polygon.exterior.coords])

def adjustPolygon(tilePolygon, xMin, yMin, tileSize):
    return shapely.Polygon([(x - xMin) * tileSize, (y - yMin) * tileSize] for x, y in tilePolygon.exterior.coords)

def createMask(stitchedImage, tilePolygons):
    mask = Image.new('L', stitchedImage.size, 0)
    draw = ImageDraw.Draw(mask)
    for tilePolygon in tilePolygons:
        draw.polygon(list(tilePolygon.exterior.coords), fill=255)
    return mask

def applyMaskAndCrop(stitchedImage, mask):
    stitchedImage.putalpha(mask)
    bbox = mask.getbbox()
    croppedImage = stitchedImage.crop(bbox)
    return croppedImage

def drawOverlayPolygon(stitchedImage, overlayTilePolygons):
    draw = ImageDraw.Draw(stitchedImage)
    for overlayTilePolygon in overlayTilePolygons:
        overlayCoords = [(x, y) for x, y in overlayTilePolygon.exterior.coords]
        draw.line(overlayCoords + [overlayCoords[0]], fill='red', width=5)  # Adjust width as needed

def saveFinalImage(croppedImage, tempDir, filename):
    overlayImagePath = os.path.join(tempDir, filename)
    croppedImage.save(overlayImagePath)
    return overlayImagePath

def fetchAndStitchTiles(tiles, polygon, overlayPolygon, zoom, fetchTileFunc, token=None):
    tempDir = createTempDir()
    tilePaths, tileSize = fetchTiles(tiles, fetchTileFunc, tempDir, token=token)
    xMin, yMin, xMax, yMax = determineBoundingBox(tiles)
    stitchedImage = stitchTiles(tilePaths, xMin, yMin, tileSize)
    
    if isinstance(polygon, shapely.MultiPolygon):
        tilePolygons = [convertPolygon(poly, zoom) for poly in polygon.geoms]
    else:
        tilePolygons = [convertPolygon(polygon, zoom)]
    
    tilePolygons = [adjustPolygon(poly, xMin, yMin, tileSize) for poly in tilePolygons]
    mask = createMask(stitchedImage, tilePolygons)
    croppedImage = applyMaskAndCrop(stitchedImage, mask)
    
    if isinstance(overlayPolygon, shapely.MultiPolygon):
        overlayTilePolygons = [convertPolygon(poly, zoom) for poly in overlayPolygon.geoms]
    else:
        overlayTilePolygons = [convertPolygon(overlayPolygon, zoom)]
    
    overlayTilePolygons = [adjustPolygon(poly, xMin, yMin, tileSize) for poly in overlayTilePolygons]
    drawOverlayPolygon(stitchedImage, overlayTilePolygons)
    
    minX, minY, maxX, maxY = tilePolygons[0].bounds
    for poly in tilePolygons:
        minX = min(minX, poly.bounds[0])
        minY = min(minY, poly.bounds[1])
        maxX = max(maxX, poly.bounds[2])
        maxY = max(maxY, poly.bounds[3])
    croppedImage = stitchedImage.crop((minX, minY, maxX, maxY))
    
    fileName = uuid.uuid4().hex
    return saveFinalImage(croppedImage, tempDir, f'{fileName}.png')