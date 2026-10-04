from enum import StrEnum


class EngineeringState(StrEnum):
    NORMAL = "NORMAL"
    ATTENTION = "ATTENTION"
    UNCERTAIN = "UNCERTAIN"
    CALIBRATING = "CALIBRATING"


class DataOrigin(StrEnum):
    DEVICE = "DEVICE"
    SYNTHETIC = "SYNTHETIC"

