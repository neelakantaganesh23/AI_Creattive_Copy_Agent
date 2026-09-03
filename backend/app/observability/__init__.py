"""Opik tracing & evaluation seam.

The only package that imports the Opik SDK. Everything is gated on
``settings.opik_active``: when tracing is disabled (the default, and always in
tests) the decorators are identity functions and the annotators are no-ops, so
no Opik code runs, no network is touched, and no credentials are required.
"""

from app.observability.opik_tracing import (
    annotate_current_span,
    annotate_current_trace,
    configure_opik,
    flush_opik,
    traced,
)

__all__ = [
    "annotate_current_span",
    "annotate_current_trace",
    "configure_opik",
    "flush_opik",
    "traced",
]
