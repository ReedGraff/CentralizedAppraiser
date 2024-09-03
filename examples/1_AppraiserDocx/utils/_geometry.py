import math

# Various helping functions for geometry calculations
def lonLatToTile(lon, lat, zoom):
    """Convert longitude and latitude to tile coordinates."""
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x_tile = (lon + 180.0) / 360.0 * n
    y_tile = (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n
    return x_tile, y_tile
