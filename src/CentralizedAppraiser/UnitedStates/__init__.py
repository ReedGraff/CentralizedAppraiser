from ..abstracts import Country

class UnitedStates(Country):

    @classmethod
    def getDefiningGeometryKey(cls):
        """Return the key that defines the geometry of the county"""
        return "NAME"