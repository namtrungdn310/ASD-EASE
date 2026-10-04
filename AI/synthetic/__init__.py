"""Reproducible engineering signal generator; not a physiological validator."""
from .config import GeneratorConfig, ParticipantProfile
from .generator import SyntheticGenerator, SyntheticSession
from .scenarios import Scenario

__all__ = ["GeneratorConfig", "ParticipantProfile", "Scenario", "SyntheticGenerator", "SyntheticSession"]
__version__ = "0.1.0"

