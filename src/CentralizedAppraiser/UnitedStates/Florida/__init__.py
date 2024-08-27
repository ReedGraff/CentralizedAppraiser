from ...UnitedStates import UnitedStates

class Florida(UnitedStates, UnitedStates.State):

    @classmethod
    def getDefiningGeometryKey(cls):
        """Return the key that defines the geometry of the county"""
        return "NAME"