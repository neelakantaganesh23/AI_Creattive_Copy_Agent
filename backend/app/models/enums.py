"""Domain enumerations shared by models, schemas and services."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    MARKETER = "marketer"
    VIEWER = "viewer"


class AuthProvider(StrEnum):
    LOCAL = "local"
    GOOGLE = "google"


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


class RuleType(StrEnum):
    """How a content rule is enforced.

    Everything except :attr:`GUIDELINE` is machine-checkable and is enforced by
    ``app.agents.rules``; guidelines are natural-language instructions that only
    the LLM judge can assess.
    """

    MAX_CHARS = "max_chars"
    MIN_CHARS = "min_chars"
    MAX_WORDS = "max_words"
    MIN_WORDS = "min_words"
    FORBIDDEN_TERMS = "forbidden_terms"
    REQUIRED_TERMS = "required_terms"
    REGEX = "regex"
    GUIDELINE = "guideline"


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


# Field names a rule may target, per channel. A rule with no field applies to
# every field of its channel.
CHANNEL_FIELDS: dict[Channel, tuple[str, ...]] = {
    Channel.EMAIL: ("headline", "sub_heading", "cta"),
    Channel.MOBILE: ("superline", "pre_heading", "headline", "sub_heading", "cta"),
    Channel.SMS: ("description",),
}

RULE_FIELD_NAMES: frozenset[str] = frozenset(
    name for names in CHANNEL_FIELDS.values() for name in names
)


class AgentName(StrEnum):
    DATA_EXTRACTION = "data_extraction"
    WEB_SEARCH_GROUNDING = "web_search_grounding"
    COPY_GENERATION = "copy_generation"
    REPETITION_FIX = "repetition_fix"
    CTA_OPTIMIZATION = "cta_optimization"
    IMAGE_GENERATION = "image_generation"
    CONTENT_VALIDATION = "content_validation"
    OUTPUT_PARSING = "output_parsing"


AGENT_SEQUENCE: tuple[AgentName, ...] = (
    AgentName.DATA_EXTRACTION,
    AgentName.WEB_SEARCH_GROUNDING,
    AgentName.COPY_GENERATION,
    AgentName.REPETITION_FIX,
    AgentName.CTA_OPTIMIZATION,
    # Runs after CTA optimisation so the final headline and brand are available
    # for the image prompt.
    AgentName.IMAGE_GENERATION,
    # Runs after CTA optimisation so the deterministic CTA is judged too.
    AgentName.CONTENT_VALIDATION,
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
    AgentName.IMAGE_GENERATION: {
        "title": "Image Generation",
        "description": "Generating a campaign visual from the brief",
    },
    AgentName.CONTENT_VALIDATION: {
        "title": "Content Validation",
        "description": "Judging copy against the configured content rules",
    },
    AgentName.OUTPUT_PARSING: {
        "title": "Output Parsing & Logging",
        "description": "Parsing output and logging execution details",
    },
}
