"""Bộ sinh tín hiệu có thể tái lập, không chứng nhận tính đúng sinh lý."""
from .config import GeneratorConfig, ParticipantProfile
from .generator import SyntheticGenerator, SyntheticSession
from .scenarios import Scenario

__all__ = ["GeneratorConfig", "ParticipantProfile", "Scenario", "SyntheticGenerator", "SyntheticSession"]
__version__ = "0.1.0"

