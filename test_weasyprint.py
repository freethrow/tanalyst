"""
Simple test script to verify WeasyPrint functionality.
"""

import os
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

def test_weasyprint():
    # Define HTML content
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>WeasyPrint Test</title>
    <style>
        @font-face {
            font-family: 'Roboto';
            src: url('static/fonts/Roboto-Light.ttf');
        }
        
        body {
            font-family: 'Roboto', sans-serif;
            margin: 2cm;
        }
        h1 {
            color: #991b1b;
            text-align: center;
        }
        p {
            text-align: justify;
        }
    </style>
</head>
<body>
    <h1>WeasyPrint Test Document</h1>
    <p>This is a test document to verify that WeasyPrint is working correctly.</p>
    <p>If you see this PDF with proper formatting and fonts, the installation was successful.</p>
</body>
</html>
"""

    try:
        # Configure fonts
        font_config = FontConfiguration()
        
        # Create PDF
        html = HTML(string=html_content)
        css = CSS(string="""
            @font-face {
                font-family: 'Roboto';
                src: url('static/fonts/Roboto-Light.ttf');
            }
        """, font_config=font_config)
        
        output_file = os.path.join(os.path.dirname(__file__), 'weasyprint_test.pdf')
        html.write_pdf(output_file, font_config=font_config)
        
        print(f"✅ Test passed! PDF generated successfully at: {output_file}")
        return True
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_weasyprint()
