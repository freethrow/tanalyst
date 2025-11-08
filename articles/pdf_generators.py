"""
PDF generation utilities for articles and weekly summaries.

Deprecated: This module is kept for backward compatibility.
New code should import directly from weasyprint_generators.
"""

# Import from the new implementation for backward compatibility
from .weasyprint_generators import (
    ArticlesPDFGenerator,
    WeeklySummaryPDFGenerator,
    WeasyPrintGenerator,
)

# Re-export the classes for backward compatibility
__all__ = ['ArticlesPDFGenerator', 'WeeklySummaryPDFGenerator']
