class TranslationError(Exception):
    """Raised when an error occurs translating data from one format to another"""

class TranslationInvalid(Exception):
    """Raised when a translation is performed, but the data does not match the appropriate format according to the _address schema"""

class AddressClientError(Exception):
    """Raised when an error occurs with the AddressClient"""

