from ...UnitedStates import UnitedStates

import os
import ijson

class Florida(UnitedStates, UnitedStates.State):

    @classmethod
    def getDefiningGeometryKey(cls):
        """Return the key that defines the geometry of the county"""
        return "NAME"

    @classmethod
    def getGeometryFeature(cls, value: str) -> dict:
        """Return the geojson feature which matches the value at the defining geometry key"""
        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))
        
        with open(os.path.join(__location__, 'geometry.geojson'), 'r') as f:
            geometryKey = cls.getDefiningGeometryKey()

            objects = ijson.items(f, 'features.item')
            # florida = (o["properties"][geometryKey] for o in objects if o["properties"][geometryKey] == value)
            for i in objects:
                if i["properties"][geometryKey] == value:
                    return i
            return None