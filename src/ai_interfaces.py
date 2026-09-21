"""Evidence-grounded extension points for future AI features.

This module deliberately contains no model calls. Future summarizers, driver
coaches, or prediction models should receive a bounded context of processed
FastF1 observations and return claims linked to that evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol, Sequence


@dataclass(frozen=True)
class EvidenceItem:
    """One auditable observation that can support a future AI claim."""

    source: str
    statement: str
    value: str | float | int | None = None


@dataclass(frozen=True)
class AnalysisContext:
    """Bounded, serializable context for evidence-grounded analysis."""

    season: int
    event: str
    session: str
    evidence: tuple[EvidenceItem, ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(cls, season: int, event: str, session: str, evidence: Mapping[str, object]) -> "AnalysisContext":
        """Convert processed metric mappings into explicit evidence items."""
        items = tuple(EvidenceItem(source=str(key), statement=f"Observed {key}", value=value if isinstance(value, (str, float, int)) or value is None else str(value)) for key, value in evidence.items())
        return cls(season=int(season), event=str(event), session=str(session), evidence=items)


@dataclass(frozen=True)
class AnalysisResult:
    """Future analyzer output with mandatory evidence references."""

    answer: str
    evidence_sources: tuple[str, ...] = field(default_factory=tuple)
    limitations: tuple[str, ...] = field(default_factory=tuple)


class GroundedAnalyzer(Protocol):
    """Interface future AI analyzers must implement."""

    def analyze(self, context: AnalysisContext) -> AnalysisResult:
        """Generate an answer only from the supplied processed context."""
        ...


def validate_result(result: AnalysisResult, context: AnalysisContext) -> list[str]:
    """Return validation issues instead of allowing unsupported claims silently."""
    available = {item.source for item in context.evidence}
    return [source for source in result.evidence_sources if source not in available]

