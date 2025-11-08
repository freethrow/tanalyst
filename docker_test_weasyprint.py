"""
Docker test script for WeasyPrint.
Run this in the Docker container to verify WeasyPrint works correctly.

Usage:
  docker-compose exec web python docker_test_weasyprint.py
"""

import os
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
import platform

def test_weasyprint():
    print(f"Testing WeasyPrint in {platform.system()}")
    
    # Define HTML content
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Docker WeasyPrint Test</title>
    <style>
        body { font-family: sans-serif; margin: 2cm; }
        h1 { color: #991b1b; text-align: center; }
        p { text-align: justify; }
    </style>
</head>
<body>
    <h1>Docker WeasyPrint Test Document</h1>
    <p>This is a test document to verify that WeasyPrint is working correctly in Docker.</p>
    <p>If you see this PDF with proper formatting, the installation was successful.</p>
</body>
</html>
"""

    try:
        # Configure fonts
        font_config = FontConfiguration()
        
        # Create PDF
        html = HTML(string=html_content)
        
        output_file = os.path.join(os.path.dirname(__file__), 'docker_weasyprint_test.pdf')
        html.write_pdf(output_file, font_config=font_config)
        
        print(f"✅ Test passed! PDF generated successfully at: {output_file}")
        return True
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_weasyprint()
