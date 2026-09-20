from enum import Enum


class SrcType(str, Enum):
    VIDEO = "video"
    WEBCAM = "webcam"
    LIVE = "live"
