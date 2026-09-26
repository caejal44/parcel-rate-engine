from enum import Enum


class SignatureType(str, Enum):
    REQUIRED = "SIG"
    ADULT = "ASIG"


class DeliveryAreaType(str, Enum):
    COMMERCIAL = "DASC"
    RESIDENTIAL = "DASR"
    EXTENDED = "EDAS"
    REMOTE = "REM"


class AdditionalHandlingType(str, Enum):
    WEIGHT = "ADW"
    DIMENSIONS = "AHD"
    PACKAGING = "AHP"


class LargePackageType(str, Enum):
    LARGE_PACKAGE = "LPS"
    OVER_MAX = "MAX"