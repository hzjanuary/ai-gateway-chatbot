"""Optional web enrichment, disabled by default. No persistent document retrieval."""

from gateway.enrichment import enrich

__all__ = ["enrich"]
