from dataclasses import dataclass, field
from typing import Dict

@dataclass
class ScanResult:
    """A standardized object for all checker results."""
    is_malicious: bool
    summary: str
    source: str
    details: Dict = field(default_factory=dict)
    error: bool = False
    is_pending: bool = False
    risk_factors: Dict = field(default_factory=dict)
