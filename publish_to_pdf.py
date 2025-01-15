from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import re
import os
import urllib.request
import warnings

class PageTemplateWithBackground:
    """
    Custom page template that draws a background color
    """
    def __init__(self, background_color):
        self.background_color = background_color
    
    def on_page(self, canvas, doc):
        """Draw the background color on each page"""
        canvas.saveState()
        canvas.setFillColor(self.background_color)
        canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=1)
        canvas.restoreState()

def download_font(font_name, font_url):
    """
    Download a font file if it doesn't exist locally.
    
    Args:
        font_name (str): Name of the font file
        font_url (str): URL to download the font from
    Returns:
        bool: True if font is available (downloaded or exists), False otherwise
    """
    if not os.path.exists(font_name):
        try:
            print(f"Downloading {font_name}...")
            urllib.request.urlretrieve(font_url, font_name)
            return True
        except Exception as e:
            warnings.warn(f"Failed to download {font_name}: {e}")
            return False
    return True

def register_fonts():
    """
    Register fonts for use in the PDF.
    Falls back to default fonts if custom fonts are unavailable.
    """
    font_urls = {
        'CrimsonText-Regular.ttf': 'https://raw.githubusercontent.com/google/fonts/main/ofl/crimsontext/CrimsonText-Regular.ttf',
        'CrimsonText-Bold.ttf': 'https://raw.githubusercontent.com/google/fonts/main/ofl/crimsontext/CrimsonText-Bold.ttf',
        'CrimsonText-Italic.ttf': 'https://raw.githubusercontent.com/google/fonts/main/ofl/crimsontext/CrimsonText-Italic.ttf',
        'Cinzel-Regular.ttf': 'https://github.com/NDISCOVER/Cinzel/raw/refs/heads/master/fonts/ttf/Cinzel-Regular.ttf',
        'Cinzel-Bold.ttf': 'https://github.com/NDISCOVER/Cinzel/raw/refs/heads/master/fonts/ttf/Cinzel-Bold.ttf'
    }
    
    # Try to download and register custom fonts
    fonts_available = all(download_font(name, url) for name, url in font_urls.items())
    
    try:
        if fonts_available:
            # Register custom fonts
            pdfmetrics.registerFont(TTFont('CrimsonText', 'CrimsonText-Regular.ttf'))
            pdfmetrics.registerFont(TTFont('CrimsonText-Bold', 'CrimsonText-Bold.ttf'))
            pdfmetrics.registerFont(TTFont('CrimsonText-Italic', 'CrimsonText-Italic.ttf'))
            pdfmetrics.registerFont(TTFont('Cinzel', 'Cinzel-Regular.ttf'))
            pdfmetrics.registerFont(TTFont('Cinzel-Bold', 'Cinzel-Bold.ttf'))
            return True
    except Exception as e:
        warnings.warn(f"Failed to register custom fonts: {e}")
    
    return False

def clean_text(text):
    """
    Clean text by removing extra spaces, carriage returns, and normalizing whitespace.
    """
    # Replace multiple carriage returns and newlines with a single newline
    text = re.sub(r'\r+', '\n', text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    
    # Remove extra spaces
    text = re.sub(r' +', ' ', text)
    
    # Clean up spaces around newlines
    text = re.sub(r' *\n *', '\n', text)
    
    # Ensure consistent paragraph separation
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Strip whitespace from the beginning and end
    text = text.strip()
    
    return text

def process_novel_to_pdf(input_text, output_filename='novel.pdf', title='My Novel'):
    """
    Process text into chapters and create a beautifully formatted PDF novel.
    """
    # Try to register custom fonts
    custom_fonts = register_fonts()
    
    # Clean the input text
    input_text = clean_text(input_text)
    
    # Define eye-friendly colors
    background_color = colors.Color(0.973, 0.969, 0.957)  # Warm cream color
    text_color = colors.Color(0.133, 0.133, 0.133)  # Soft black
    
    class DocumentWithBackground(SimpleDocTemplate):
        def handle_pageBegin(self):
            self.canv.saveState()
            self.canv.setFillColor(background_color)
            self.canv.rect(0, 0, letter[0], letter[1], fill=1)
            self.canv.restoreState()
            super().handle_pageBegin()
    
    # Create the PDF document
    doc = DocumentWithBackground(
        output_filename,
        pagesize=letter,
        rightMargin=1.25*inch,
        leftMargin=1.25*inch,
        topMargin=1*inch,
        bottomMargin=1*inch
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Create custom styles with appropriate fonts
    title_style = ParagraphStyle(
        'NovelTitle',
        fontName='Cinzel-Bold' if custom_fonts else 'Times-Bold',
        fontSize=24,
        spaceAfter=30,
        alignment=1,
        leading=36,
        textColor=colors.black
    )
    
    chapter_style = ParagraphStyle(
        'ChapterTitle',
        fontName='Cinzel' if custom_fonts else 'Times-Bold',
        fontSize=18,
        spaceAfter=30,
        spaceBefore=30,
        alignment=1,
        leading=28,
        textColor=colors.black
    )
    
    body_style = ParagraphStyle(
        'NovelBody',
        fontName='CrimsonText' if custom_fonts else 'Times-Roman',
        fontSize=12,
        leading=18,
        spaceAfter=12,
        firstLineIndent=24,
        alignment=0,
        textColor=colors.black
    )
    
    # Store the elements that will make up our document
    elements = []
    
    # Add title page
    elements.append(Spacer(1, 3*inch))
    elements.append(Paragraph(title, title_style))
    elements.append(PageBreak())
    
    # Split text into chapters and clean each chapter
    chapters = [clean_text(chapter) for chapter in input_text.split('Chapter')[1:]]
    
    # Process each chapter
    for i, chapter_text in enumerate(chapters, 1):
        # Split chapter title from content
        chapter_parts = chapter_text.strip().split('\n', 1)
        chapter_title = f"Chapter {chapter_parts[0].strip()}"
        
        # Add chapter title with proper spacing
        elements.append(Spacer(1, inch))
        elements.append(Paragraph(chapter_title, chapter_style))
        elements.append(Spacer(1, 0.5*inch))
        
        # Process chapter content
        if len(chapter_parts) > 1:
            content = chapter_parts[1].strip()
            # Split content into paragraphs and clean each paragraph
            paragraphs = [clean_text(para) for para in content.split('\n\n')]
            
            for para in paragraphs:
                if para.strip():
                    elements.append(Paragraph(para.strip(), body_style))
        
        # Add page break after each chapter
        elements.append(PageBreak())
    
    # Build the PDF document
    doc.build(elements)
    
    return output_filename



if __name__ == "__main__":
    text = open("novel_output/final_novel.txt", "r", encoding='utf-8').read()
    text.replace("TERMINATE", "")
    text.replace("**", "")
    process_novel_to_pdf(text, 'novel_output/final_novel.pdf', 'Unit 985')