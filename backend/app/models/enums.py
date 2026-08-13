"""Domain enumerations shared by models, schemas and services."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    MARKETER = "marketer"
    VIEWER = "viewer"


class Channel(StrEnum):
    EMAIL = "email"
    MOBILE = "mobile"
    SMS = "sms"

    @property
    def label(self) -> str:
        return {"email": "Email", "mobile": "Mobile", "sms": "SMS"}[self.value]


class GenerationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class AgentStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class QualityStatus(StrEnum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"


class AgentName(StrEnum):
    DATA_EXTRACTION = "data_extraction"
    WEB_SEARCH_GROUNDING = "web_search_grounding"
    COPY_GENERATION = "copy_generation"
    REPETITION_FIX = "repetition_fix"
    CTA_OPTIMIZATION = "cta_optimization"
    OUTPUT_PARSING = "output_parsing"


AGENT_SEQUENCE: tuple[AgentName, ...] = (
    AgentName.DATA_EXTRACTION,
    AgentName.WEB_SEARCH_GROUNDING,
    AgentName.COPY_GENERATION,
    AgentName.REPETITION_FIX,
    AgentName.CTA_OPTIMIZATION,
    AgentName.OUTPUT_PARSING,
)

AGENT_METADATA: dict[AgentName, dict[str, str]] = {
    AgentName.DATA_EXTRACTION: {
        "title": "Data Extraction",
        "description": "Extracting brand, products, SKUs and athlete mentions",
    },
    AgentName.WEB_SEARCH_GROUNDING: {
        "title": "Web Search Grounding",
        "description": "Finding relevant real-world context",
    },
    AgentName.COPY_GENERATION: {
        "title": "Copy Generation",
        "description": "Generating personalized marketing copy",
    },
    AgentName.REPETITION_FIX: {
        "title": "Repetition Fix",
        "description": "Checking and fixing repetitive content",
    },
    AgentName.CTA_OPTIMIZATION: {
        "title": "CTA Optimization",
        "description": "Applying CTA rules and brand guidelines",
    },
    AgentName.OUTPUT_PARSING: {
        "title": "Output Parsing & Logging",
        "description": "Parsing output and logging execution details",
    },
}
