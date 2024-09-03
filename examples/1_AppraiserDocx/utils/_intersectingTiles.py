import math
import shapely

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)

def getTileRange(polygon, zoom):
    bnds = polygon.bounds
    xm = bnds[0]
    xmx = bnds[2]
    ym = bnds[1]
    ymx = bnds[3]
    starting = deg2num(ymx, xm, zoom)
    ending = deg2num(ym, xmx, zoom)
    x_range = (starting[0], ending[0])
    y_range = (starting[1], ending[1])
    return (x_range, y_range)

def getTileAsPolygon(z, y, x):
    nw = num2deg(x, y, z)
    se = num2deg(x + 1, y + 1, z)
    xm = nw[1]
    xmx = se[1]
    ym = se[0]
    ymx = nw[0]
    tile_bound = shapely.Polygon([(xm, ym), (xmx, ym), (xmx, ymx), (xm, ymx)])
    return tile_bound

def doesTileIntersect(z, y, x, polygon):
    tile = getTileAsPolygon(z, y, x)
    return polygon.intersects(tile)

def getTilesForPolygon(polygon, zoom):
    tile_list = []
    x_range, y_range = getTileRange(polygon, zoom)
    for x in range(x_range[0], x_range[1] + 1):
        for y in range(y_range[0], y_range[1] + 1):
            if doesTileIntersect(zoom, y, x, polygon):
                tile_list.append((zoom, y, x))
    return tile_list

def adjust_polygon_aspect_ratio(polygon, desired_aspect_ratio=1 / 1, buffer_distance=0):
    """
    Adjust the polygon's bounding box to achieve the desired aspect ratio.

    :param polygon: The input polygon to be adjusted.
    :param desired_aspect_ratio: The desired aspect ratio (width / height).
    :param buffer_distance: The distance to buffer the new bounding box.
    :return: The adjusted polygon.
    """
    # Get the current bounding box
    minx, miny, maxx, maxy = polygon.bounds
    current_width = maxx - minx
    current_height = maxy - miny

    # Apply buffer distance to the bounding box
    if buffer_distance != 0:
        buffered_polygon = polygon.buffer(buffer_distance, cap_style='square', join_style='mitre')
        minx, miny, maxx, maxy = buffered_polygon.bounds
        current_width = maxx - minx
        current_height = maxy - miny

    current_aspect_ratio = current_width / current_height

    # Calculate new bounding box dimensions
    if current_aspect_ratio < desired_aspect_ratio:
        # Increase width
        new_width = current_height * desired_aspect_ratio
        new_height = current_height
    else:
        # Increase height
        new_width = current_width
        new_height = current_width / desired_aspect_ratio

    # Calculate the center of the current bounding box
    center_x = (minx + maxx) / 2
    center_y = (miny + maxy) / 2

    # Create a new bounding box polygon
    new_minx = center_x - new_width / 2
    new_maxx = center_x + new_width / 2
    new_miny = center_y - new_height / 2
    new_maxy = center_y + new_height / 2
    new_bbox_polygon = shapely.box(new_minx, new_miny, new_maxx, new_maxy)

    return new_bbox_polygon

def getTilesForPolygonWithBuffer(polygon, zoom, desired_aspect_ratio=1/1, buffer_distance=0):
    polygon = adjust_polygon_aspect_ratio(polygon, desired_aspect_ratio, buffer_distance)
    return getTilesForPolygon(polygon, zoom), polygon