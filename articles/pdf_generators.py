"""
PDF generation utilities for articles and weekly summaries using ReportLab.
"""

import io
import os
from datetime import datetime
from typing import List, Optional

from django.conf import settings
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .models import Article, WeeklySummary


class PDFStyleManager:
    """Manages consistent styling across all PDF documents."""

    def __init__(self):
        self.brand_color = colors.HexColor("#991b1b")
        self.font_name = "Times-Roman"
        self.title_font_name = "Times-Bold"
        self._load_custom_fonts()

    def _load_custom_fonts(self):
        """Load custom fonts if available, fallback to standard fonts."""
        try:
            roboto_light_path = os.path.join(
                settings.BASE_DIR, "static", "fonts", "Roboto-Light.ttf"
            )
            manrope_bold_path = os.path.join(
                settings.BASE_DIR, "static", "fonts", "Manrope-Bold.ttf"
            )

            pdfmetrics.registerFont(TTFont("Roboto-Light", roboto_light_path))
            pdfmetrics.registerFont(TTFont("Manrope-Bold", manrope_bold_path))

            self.font_name = "Roboto-Light"
            self.title_font_name = "Manrope-Bold"
        except Exception as e:
            print(f"Could not load custom fonts: {e}")
            # Keep default fonts

    def get_styles(self):
        """Get standard paragraph styles for PDF documents."""
        styles = getSampleStyleSheet()

        return {
            "main_title": ParagraphStyle(
                "MainTitle",
                parent=styles["Heading1"],
                fontName=self.title_font_name,
                fontSize=22,
                textColor=self.brand_color,
                alignment=TA_CENTER,
                spaceAfter=8,
            ),
            "subtitle": ParagraphStyle(
                "Subtitle",
                parent=styles["Normal"],
                fontName=self.font_name,
                fontSize=11,
                textColor=colors.grey,
                alignment=TA_CENTER,
                spaceAfter=20,
            ),
            "section_title": ParagraphStyle(
                "SectionTitle",
                parent=styles["Heading2"],
                fontName=self.title_font_name,
                fontSize=16,
                textColor=self.brand_color,
                spaceAfter=10,
                spaceBefore=15,
            ),
            "subsection_title": ParagraphStyle(
                "SubsectionTitle",
                parent=styles["Heading3"],
                fontName=self.title_font_name,
                fontSize=13,
                textColor=self.brand_color,
                spaceAfter=8,
                spaceBefore=12,
            ),
            "content": ParagraphStyle(
                "Content",
                parent=styles["Normal"],
                fontName=self.font_name,
                fontSize=10,
                alignment=TA_JUSTIFY,
                spaceAfter=12,
                leading=14,
            ),
            "bullet": ParagraphStyle(
                "Bullet",
                parent=styles["Normal"],
                fontName=self.font_name,
                fontSize=10,
                leftIndent=20,
                spaceAfter=8,
                leading=13,
            ),
            "highlight_box": ParagraphStyle(
                "HighlightBox",
                parent=styles["Normal"],
                fontName=self.font_name,
                fontSize=11,
                alignment=TA_JUSTIFY,
                spaceAfter=15,
                leading=15,
                leftIndent=15,
                rightIndent=15,
            ),
            "footer": ParagraphStyle(
                "Footer",
                parent=styles["Normal"],
                fontName=self.font_name,
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER,
            ),
            "contact_footer": ParagraphStyle(
                "ContactFooter",
                parent=styles["Normal"],
                fontName=self.font_name,
                fontSize=9,
                textColor=colors.grey,
                alignment=TA_CENTER,
                spaceAfter=5,
            ),
            "article_title": ParagraphStyle(
                "ArticleTitle",
                parent=styles["Heading3"],
                fontName=self.title_font_name,
                fontSize=12,
                textColor=self.brand_color,
                spaceAfter=8,
                spaceBefore=12,
            ),
            "article_content": ParagraphStyle(
                "ArticleContent",
                parent=styles["Normal"],
                fontName=self.font_name,
                fontSize=9,
                alignment=TA_JUSTIFY,
                spaceAfter=10,
                leading=12,
            ),
            "article_meta": ParagraphStyle(
                "ArticleMeta",
                parent=styles["Normal"],
                fontName=self.font_name,
                fontSize=8,
                textColor=colors.grey,
                spaceAfter=8,
            ),
        }


class ArticlesPDFGenerator:
    """Generates PDF reports for approved articles."""

    def __init__(self):
        self.style_manager = PDFStyleManager()
        self.styles = self.style_manager.get_styles()

    def generate_articles_pdf(self, articles: List[Article]) -> HttpResponse:
        """Generate PDF report of approved articles."""
        # Create PDF buffer
        buffer = io.BytesIO()

        # Define page dimensions
        page_width, page_height = A4
        left_margin = 2 * cm
        right_margin = 2 * cm
        top_margin = 2 * cm
        bottom_margin = 2 * cm

        # Create document with two-column layout
        doc = BaseDocTemplate(buffer, pagesize=A4)

        # Container for PDF elements
        elements = []

        # Add title
        title_text = f"Report Articoli Approvati - {datetime.now().strftime('%B %Y')}"
        elements.append(Paragraph(title_text, self.styles["main_title"]))

        # Add metadata
        metadata_text = f"Generato il {datetime.now().strftime('%d/%m/%Y')} | {len(articles)} articoli"
        elements.append(Paragraph(metadata_text, self.styles["subtitle"]))
        elements.append(Spacer(1, 0.5 * cm))

        # Add articles
        for idx, article in enumerate(articles, 1):
            article_elements = self._create_article_elements(article, idx)
            elements.append(KeepTogether(article_elements))

        # Add contact footer
        elements.append(Spacer(1, 2 * cm))
        contact_info = """
        <b>TA - Trade AI Analyst</b><br/>
        Email: info@technicalanalyst.com | Tel: +39 123 456 7890<br/>
        Web: www.technicalanalyst.com | Via Example 123, Milano, Italia<br/>
        <i>Report generato automaticamente dal sistema TA</i>
        """
        elements.append(Paragraph(contact_info, self.styles["contact_footer"]))

        # Create header and footer function
        def add_header_footer(canvas, doc):
            self._add_header_footer(
                canvas, doc, page_width, page_height, left_margin, right_margin
            )

        # Create two-column frame
        frame_width = (page_width - left_margin - right_margin - 1 * cm) / 2
        frame1 = Frame(
            left_margin,
            bottom_margin,
            frame_width,
            page_height - top_margin - bottom_margin - 3 * cm,
            id="col1",
        )
        frame2 = Frame(
            left_margin + frame_width + 1 * cm,
            bottom_margin,
            frame_width,
            page_height - top_margin - bottom_margin - 3 * cm,
            id="col2",
        )

        # Create page template with two columns
        page_template = PageTemplate(
            id="TwoColumn", frames=[frame1, frame2], onPage=add_header_footer
        )
        doc.addPageTemplates([page_template])

        # Build PDF
        doc.build(elements)

        # Create response
        pdf_value = buffer.getvalue()
        buffer.close()

        response = HttpResponse(pdf_value, content_type="application/pdf")
        filename = f"report_articoli_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    def _create_article_elements(self, article: Article, index: int) -> List:
        """Create PDF elements for a single article."""
        elements = []

        # Article number and title
        title_text = f"{index}. {article.title_it}"
        elements.append(Paragraph(title_text, self.styles["article_title"]))

        # Article metadata
        meta_parts = []
        if article.source:
            meta_parts.append(f"Fonte: {article.source}")
        if article.article_date:
            meta_parts.append(f"Data: {article.article_date.strftime('%d/%m/%Y')}")
        if article.sector:
            meta_parts.append(f"Settore: {article.sector}")

        if meta_parts:
            meta_text = " | ".join(meta_parts)
            elements.append(Paragraph(meta_text, self.styles["article_meta"]))

        # Article content
        if article.content_it:
            # Limit content length for PDF
            content = article.content_it[:1500]
            if len(article.content_it) > 1500:
                content += "..."
            elements.append(Paragraph(content, self.styles["article_content"]))

        elements.append(Spacer(1, 0.3 * cm))
        return elements

    def _add_header_footer(
        self, canvas, doc, page_width, page_height, left_margin, right_margin
    ):
        """Add header and footer to each page."""
        canvas.saveState()

        # Draw header background
        canvas.setFillColor(self.style_manager.brand_color)
        canvas.rect(
            0, page_height - 3 * cm, page_width, 3 * cm, fill=True, stroke=False
        )

        # Header text in white
        canvas.setFont("Helvetica-Bold", 16)
        canvas.setFillColor(colors.white)
        canvas.drawCentredString(
            page_width / 2, page_height - 1.5 * cm, "TA - Technical Analyst"
        )

        # Subtitle
        canvas.setFont("Helvetica", 10)
        metadata_text = (
            f"Report Articoli | Generato il {datetime.now().strftime('%d/%m/%Y')}"
        )
        canvas.drawCentredString(page_width / 2, page_height - 2.2 * cm, metadata_text)

        # Draw footer background
        canvas.setFillColor(self.style_manager.brand_color)
        canvas.rect(0, 0, page_width, 1 * cm, fill=True, stroke=False)

        # Footer text in white
        footer_text = f"TA - Technical Analyst | Report generato il {datetime.now().strftime('%d/%m/%Y')}"
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.white)
        canvas.drawCentredString(page_width / 2, 0.4 * cm, footer_text)

        # Page number in white
        page_num = f"Pagina {canvas.getPageNumber()}"
        canvas.drawRightString(page_width - right_margin, 0.4 * cm, page_num)
        canvas.restoreState()


class WeeklySummaryPDFGenerator:
    """Generates PDF reports for weekly summaries."""

    def __init__(self):
        self.style_manager = PDFStyleManager()
        self.styles = self.style_manager.get_styles()

    def generate_weekly_summary_pdf(self, summary: WeeklySummary) -> HttpResponse:
        """Generate PDF report for a specific weekly summary."""
        # Create PDF buffer
        buffer = io.BytesIO()

        # Define page dimensions
        page_width, page_height = A4
        left_margin = 2.5 * cm
        right_margin = 2.5 * cm
        top_margin = 2 * cm
        bottom_margin = 2 * cm

        # Create document
        doc = BaseDocTemplate(buffer, pagesize=A4)

        # Container for PDF elements
        elements = []

        # Add title
        title_text = summary.title or "Weekly Business Summary"
        elements.append(Paragraph(title_text, self.styles["main_title"]))

        # Add metadata
        period_start = summary.period_start
        period_end = summary.period_end
        generated_at = summary.generated_at

        if period_start and period_end:
            period_text = f"Periodo: {period_start.strftime('%d %b')} - {period_end.strftime('%d %b %Y')}"
        else:
            period_text = "Periodo: N/A"

        metadata_text = f"{period_text} | Articoli analizzati: {summary.articles_analyzed or 0} | Generato: {generated_at.strftime('%d/%m/%Y') if generated_at else 'N/A'}"
        elements.append(Paragraph(metadata_text, self.styles["subtitle"]))
        elements.append(Spacer(1, 0.3 * cm))

        # Executive Summary in a highlighted box
        elements.append(Paragraph("Sintesi Esecutiva", self.styles["section_title"]))

        exec_summary_text = summary.executive_summary or ""
        exec_data = [[Paragraph(exec_summary_text, self.styles["highlight_box"])]]
        exec_table = Table(
            exec_data, colWidths=[page_width - left_margin - right_margin - 1 * cm]
        )
        exec_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
                    ("BOX", (0, 0), (-1, -1), 1, self.style_manager.brand_color),
                    ("TOPPADDING", (0, 0), (-1, -1), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ("LEFTPADDING", (0, 0), (-1, -1), 15),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 15),
                ]
            )
        )
        elements.append(exec_table)
        elements.append(Spacer(1, 0.5 * cm))

        # Main Trends
        main_trends = summary.main_trends or []
        if main_trends:
            elements.append(
                Paragraph("Tendenze Principali", self.styles["section_title"])
            )
            for idx, trend in enumerate(main_trends, 1):
                bullet_text = f"<b>{idx}.</b> {trend}"
                elements.append(Paragraph(bullet_text, self.styles["bullet"]))
            elements.append(Spacer(1, 0.3 * cm))

        # Featured Sectors
        featured_sectors = summary.featured_sectors or []
        if featured_sectors:
            elements.append(
                Paragraph("Settori in Evidenza", self.styles["subsection_title"])
            )
            sectors_text = " • ".join(featured_sectors)
            elements.append(Paragraph(sectors_text, self.styles["content"]))
            elements.append(Spacer(1, 0.3 * cm))

        # Opportunities for Italy
        opportunities = summary.opportunities_italy or ""
        if opportunities:
            elements.append(
                Paragraph(
                    "Opportunità per le Aziende Italiane", self.styles["section_title"]
                )
            )

            opp_data = [[Paragraph(opportunities, self.styles["highlight_box"])]]
            opp_table = Table(
                opp_data, colWidths=[page_width - left_margin - right_margin - 1 * cm]
            )
            opp_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
                        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#16A34A")),
                        ("TOPPADDING", (0, 0), (-1, -1), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                        ("LEFTPADDING", (0, 0), (-1, -1), 15),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 15),
                    ]
                )
            )
            elements.append(opp_table)
            elements.append(Spacer(1, 0.5 * cm))

        # Full Content/Analysis
        full_content = summary.full_content or ""
        if full_content:
            elements.append(Paragraph("Analisi Completa", self.styles["section_title"]))
            paragraphs = full_content.split("\n")
            for para in paragraphs:
                if para.strip():
                    elements.append(Paragraph(para.strip(), self.styles["content"]))

        # Add footer info
        elements.append(Spacer(1, 1 * cm))
        llm_model = summary.llm_model or "AI Assistant"
        footer_info = f"<i>Generato da {llm_model}</i>"
        elements.append(Paragraph(footer_info, self.styles["footer"]))

        # Create header and footer function
        def add_header_footer(canvas, doc):
            self._add_header_footer(
                canvas, doc, page_width, page_height, left_margin, right_margin
            )

        # Create frame with space for header
        frame = Frame(
            left_margin,
            bottom_margin,
            page_width - left_margin - right_margin,
            page_height - top_margin - bottom_margin - 2.5 * cm,
            id="normal",
        )

        # Create page template
        page_template = PageTemplate(
            id="OneColumn", frames=[frame], onPage=add_header_footer
        )
        doc.addPageTemplates([page_template])

        # Build PDF
        doc.build(elements)

        # Create response
        pdf_value = buffer.getvalue()
        buffer.close()

        response = HttpResponse(pdf_value, content_type="application/pdf")
        filename = (
            f"weekly_summary_{summary.id}_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    def _add_header_footer(
        self, canvas, doc, page_width, page_height, left_margin, right_margin
    ):
        """Add header and footer to each page."""
        canvas.saveState()

        # Draw header background
        canvas.setFillColor(self.style_manager.brand_color)
        canvas.rect(
            0, page_height - 2.5 * cm, page_width, 2.5 * cm, fill=True, stroke=False
        )

        # Header text in white
        canvas.setFont("Helvetica-Bold", 18)
        canvas.setFillColor(colors.white)
        canvas.drawCentredString(
            page_width / 2, page_height - 1.3 * cm, "Weekly Business Summary"
        )

        # Draw footer background
        canvas.setFillColor(self.style_manager.brand_color)
        canvas.rect(0, 0, page_width, 1 * cm, fill=True, stroke=False)

        # Footer text in white
        footer_text = f"TA - Technical Analyst | Generato il {datetime.now().strftime('%d/%m/%Y')}"
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.white)
        canvas.drawCentredString(page_width / 2, 0.4 * cm, footer_text)

        # Page number in white
        page_num = f"Pagina {canvas.getPageNumber()}"
        canvas.drawRightString(page_width - right_margin, 0.4 * cm, page_num)
        canvas.restoreState()
