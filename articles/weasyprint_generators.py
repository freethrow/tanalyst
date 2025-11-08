"""
PDF generation utilities for articles and weekly summaries using WeasyPrint.

This module supports both Windows (development) and Linux (production) environments.
On Windows, it provides a simple fallback message since WeasyPrint dependencies are complex.
On Linux/Docker, it uses WeasyPrint to generate high-quality PDFs.
"""

import os
import sys
import platform
from datetime import datetime
from typing import List, Optional

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string

# Check if running on Windows
IS_WINDOWS = platform.system() == 'Windows'

# Only import WeasyPrint on Linux/Docker
if not IS_WINDOWS:
    try:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
        WEASYPRINT_AVAILABLE = True
    except ImportError:
        WEASYPRINT_AVAILABLE = False
else:
    WEASYPRINT_AVAILABLE = False

from .models import Article, WeeklySummary


class WeasyPrintGenerator:
    """Base class for WeasyPrint PDF generation."""

    def __init__(self):
        if WEASYPRINT_AVAILABLE:
            self.font_config = FontConfiguration()
            self.css_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'pdf.css')
        else:
            self.font_config = None
            self.css_path = None

    def get_fonts_css(self) -> Optional[object]:
        """Get custom CSS for fonts if available."""
        if not WEASYPRINT_AVAILABLE:
            return None
            
        try:
            if os.path.exists(self.css_path):
                return CSS(filename=self.css_path, font_config=self.font_config)
        except Exception as e:
            print(f"Could not load custom CSS: {e}")
        return None
        
    def create_windows_fallback_response(self, filename: str) -> HttpResponse:
        """Create a fallback HTML response for Windows development environment."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>PDF Generation Not Available</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; }}
                h1 {{ color: #991b1b; }}
                .note {{ background-color: #fff3cd; padding: 15px; border-left: 5px solid #ffc107; }}
                .instructions {{ background-color: #d1e7dd; padding: 15px; border-left: 5px solid #198754; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>PDF Generation Not Available on Windows</h1>
                <div class="note">
                    <strong>Note:</strong> WeasyPrint requires GTK libraries that are difficult to set up on Windows.
                    PDF generation is only available in the Docker environment.
                </div>
                <p>The PDF you attempted to generate would be saved as: <strong>{filename}</strong></p>
                <div class="instructions">
                    <h3>To generate PDFs:</h3>
                    <ol>
                        <li>Use Docker Compose to run the application</li>
                        <li>Access the same URL through the Docker container</li>
                    </ol>
                </div>
                <p>This is only a limitation of the development environment. In production, PDFs will generate correctly.</p>
            </div>
        </body>
        </html>
        """
        return HttpResponse(html_content)


class ArticlesPDFGenerator(WeasyPrintGenerator):
    """Generates PDF reports for approved articles using WeasyPrint."""

    def generate_articles_pdf_bytes(self, articles: List[Article]) -> bytes:
        """Generate PDF report of approved articles and return as bytes."""
        if not WEASYPRINT_AVAILABLE:
            raise RuntimeError("WeasyPrint is not available in this environment")
            
        # Prepare context for the template
        context = {
            'articles': articles,
            'now': datetime.now(),
            'STATIC_URL': settings.STATIC_URL,
        }
        
        # Render HTML template
        html_string = render_to_string('articles_pdf.html', context)
        
        # Generate PDF
        html = HTML(string=html_string, base_url=settings.BASE_DIR)
        css = self.get_fonts_css()
        
        if css:
            pdf_file = html.write_pdf(font_config=self.font_config, stylesheets=[css])
        else:
            pdf_file = html.write_pdf(font_config=self.font_config)
        
        return pdf_file
    
    def generate_articles_pdf(self, articles: List[Article]) -> HttpResponse:
        """Generate PDF report of approved articles."""
        filename = f"report_articoli_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Windows fallback mode
        if IS_WINDOWS:
            return self.create_windows_fallback_response(filename)
            
        try:
            # Generate PDF content
            pdf_value = self.generate_articles_pdf_bytes(articles)

            # Create response
            response = HttpResponse(pdf_value, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
            
        except Exception as e:
            # If any error occurs, show the error message
            error_message = f"Error generating PDF: {str(e)}"
            return HttpResponse(f"<h1>PDF Generation Error</h1><p>{error_message}</p>", 
                              content_type="text/html", status=500)


class WeeklySummaryPDFGenerator(WeasyPrintGenerator):
    """Generates PDF reports for weekly summaries using WeasyPrint."""

    def generate_weekly_summary_pdf_bytes(self, summary: WeeklySummary) -> bytes:
        """Generate PDF report bytes for a specific weekly summary."""
        if not WEASYPRINT_AVAILABLE:
            raise RuntimeError("WeasyPrint is not available in this environment")
            
        # Prepare context for the template
        context = {
            'summary': summary,
            'now': datetime.now(),
            'STATIC_URL': settings.STATIC_URL,
        }
        
        # Render HTML template
        html_string = render_to_string('weekly_summary_pdf.html', context)
        
        # Generate PDF
        html = HTML(string=html_string, base_url=settings.BASE_DIR)
        css = self.get_fonts_css()
        
        if css:
            pdf_file = html.write_pdf(font_config=self.font_config, stylesheets=[css])
        else:
            pdf_file = html.write_pdf(font_config=self.font_config)
            
        return pdf_file

    def generate_weekly_summary_pdf(self, summary: WeeklySummary) -> HttpResponse:
        """Generate PDF report for a specific weekly summary."""
        filename = f"weekly_summary_{summary.id}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        # Windows fallback mode
        if IS_WINDOWS:
            return self.create_windows_fallback_response(filename)
            
        try:
            # Generate PDF content
            pdf_file = self.generate_weekly_summary_pdf_bytes(summary)
            
            # Create response
            response = HttpResponse(pdf_file, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
            
        except Exception as e:
            # If any error occurs, show the error message
            error_message = f"Error generating PDF: {str(e)}"
            return HttpResponse(f"<h1>PDF Generation Error</h1><p>{error_message}</p>", 
                              content_type="text/html", status=500)
