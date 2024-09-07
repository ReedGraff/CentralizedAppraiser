from ._client import Client
from ._address import AddressInfo, AppraiserInfo, FolioInfo

# The reason I am nesting the classes inside of eachother and not having them extend eachother is for the sake of importing the classes later on.
class Country(object):
    """Uncertain Implementation"""

    """The following functions are nested here, because maybe there in some states there is a uniform appraiser?"""
    @classmethod
    def getDefiningGeometryKey(cls) -> str:
        raise NotImplementedError
    
    @classmethod
    def getFoliosByAddressInfo(cls, search:AddressInfo) -> set[list[FolioInfo], dict]:
        """just returns all of the possible folios for an address, given in the format of list[FolioInfo]"""
        # this would replace the regrid folio search or typeahead function...
        # right now, we are somewhat dependent on regrid to access the right folio number... (in the case where there are multiple folios for an address)
        # existing county apis do not have a way to search just for a folio by the address. Many do have typeahead, but this is not uniform, and would be difficult to make uniform.
        # we would need to make a function that would search, for an address, and then return a list of folios by finding the county, and then searching for the folio, and returning the options like a typeahead function...
        raise NotImplementedError

    @classmethod
    def folioByAddressInfo(cls, search:AddressInfo) -> set[str, dict]:
        """just returns the first folio for an address (if there are multiple folios, you may get the wrong one)"""
        raise NotImplementedError
    
    @classmethod
    def appraiserInfoByFolio(cls, folio:str, client:Client) -> set[AppraiserInfo, dict]:
        """just returns the appraiser info for a folio. We use the Client to validate mailing addresses"""
        raise NotImplementedError
    
    @classmethod
    def appraiserInfoByAddressInfo(cls, search:AddressInfo, client:Client) -> set[AppraiserInfo, dict]:
        """just implements the appraiser info by folio with the address info. We use the Client to validate mailing addresses"""
        raise NotImplementedError
    
    @classmethod
    def getPropertyLinesByFolio(cls, folio:str) -> set[list, dict]:
        """just returns the property lines for an address"""
        # list is just a list of lists of coordinates [[(lon, lat), (lon, lat), ...], [(lon, lat), (lon, lat), ...], ...]
        raise NotImplementedError

    @classmethod
    def getScreenshotByFolio(cls, folio:str) -> set[bool, dict]:
        """just returns the screenshot for an address"""
        raise NotImplementedError
    
    def safe_list_get(l, idx, default={}):
        try:
            return l[idx]
        except:
            return default

    class State():
        """Uncertain Implementation"""

        class County():
            """
            Abstract class to define the structure of a county object. This class is inherited by the other materials in the subdirectories.
                - It can be inherited by other classes, but not instantiated directly
            """
            @classmethod
            def __translate(cls, data:dict, client:Client) -> dict:
                """just returns the translated data. We use the Client to validate mailing addresses"""
                raise NotImplementedError

            class City():
                """Uncertain Implementation"""
                pass