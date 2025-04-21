import os
import PyPDF2
import tempfile
import re
import streamlit as st
import sys

class PDFProcessor:
    """Class to handle PDF processing operations with enhanced extraction"""
    
    def __init__(self, pdf_dir="data/pdfs"):
        """Initialize with directory containing PDF files"""
        self.pdf_dir = pdf_dir
        # Create directory if it doesn't exist
        os.makedirs(pdf_dir, exist_ok=True)
    
    def extract_text_from_file(self, pdf_path):
        """Extract text from a PDF file using PyPDF2"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text() or ""
                    text += page_text + "\n\n"
                return text
        except Exception as e:
            print(f"Error extracting text with PyPDF2 from {pdf_path}: {e}")
            return ""
    
    def extract_text_with_pdfplumber(self, pdf_path):
        """Extract text using pdfplumber (better for complex layouts)"""
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text += page_text + "\n\n"
                return text
        except ImportError:
            print("pdfplumber not installed. Install with: pip install pdfplumber")
            return ""
        except Exception as e:
            print(f"Error extracting text with pdfplumber from {pdf_path}: {e}")
            return ""
    
    def enhanced_extract_text(self, pdf_path, use_ocr=False):
        """Extract text with multiple methods for best results"""
        # Try PyPDF2 first
        text = self.extract_text_from_file(pdf_path)
        
        # If text is too short, try pdfplumber as fallback
        if len(text.strip()) < 200:  # Arbitrary threshold to detect failed extraction
            text = self.extract_text_with_pdfplumber(pdf_path)
        
        # Normalize and clean up the text
        return self.normalize_text(text)
    
    def normalize_text(self, text):
        """Clean and normalize extracted text"""
        if not text:
            return ""
            
        # Replace line breaks with spaces in paragraphs
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
        
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Fix common PDF extraction issues
        text = re.sub(r'([a-z])-\s+([a-z])', r'\1\2', text)  # Fix hyphenation
        
        # Remove common header/footer patterns if they repeat
        text = re.sub(r'Page \d+ of \d+', '', text)
        text = re.sub(r'Valley Water HR Guide\s*', '', text)
        
        # Handle bullet points and numbering
        text = re.sub(r'•\s*', '• ', text)
        
        return text.strip()
    
    def extract_text_from_uploaded_file(self, uploaded_file):
        """Extract text from a Streamlit uploaded file"""
        try:
            # Save the uploaded file to a temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(uploaded_file.getbuffer())
                temp_path = temp_file.name
            
            # Extract text from the temporary file
            text = self.enhanced_extract_text(temp_path)
            
            # Clean up the temporary file
            os.unlink(temp_path)
            
            return text
        except Exception as e:
            print(f"Error processing uploaded PDF: {e}")
            return ""
    
    def get_available_pdfs(self):
        """Get a list of available PDFs in the pdf_dir"""
        if not os.path.exists(self.pdf_dir):
            return []
        
        pdf_files = [f for f in os.listdir(self.pdf_dir) if f.lower().endswith('.pdf')]
        return pdf_files
    
    def get_pdf_path(self, filename):
        """Get the full path to a PDF file"""
        return os.path.join(self.pdf_dir, filename)
    
    def save_uploaded_pdf(self, uploaded_file, custom_name=None):
        """Save an uploaded PDF to the pdf directory"""
        if uploaded_file is None:
            return None
        
        # Determine the filename
        if custom_name:
            # Ensure it has .pdf extension
            if not custom_name.lower().endswith('.pdf'):
                custom_name += '.pdf'
            filename = custom_name
        else:
            filename = uploaded_file.name
        
        # Create full path
        file_path = os.path.join(self.pdf_dir, filename)
        
        # Save the file
        try:
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            return file_path
        except Exception as e:
            print(f"Error saving PDF: {e}")
            return None
    
    def load_pdf_content(self, filename=None, uploaded_file=None):
        """Load PDF content either from a file in pdf_dir or an uploaded file"""
        if uploaded_file:
            return self.extract_text_from_uploaded_file(uploaded_file)
        elif filename:
            file_path = self.get_pdf_path(filename)
            if os.path.exists(file_path):
                return self.enhanced_extract_text(file_path)
        return ""
    
    def get_relevant_chunks(self, question, text, num_chunks=3, chunk_size=1000, overlap=100):
        """Find the most relevant chunks of the document for a specific question"""
        if not text:
            return ""
        
        # Create overlapping chunks for better context
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            if len(chunk) > 200:  # Only keep chunks with substantial content
                chunks.append(chunk)
        
        if not chunks:
            return text
        
        # Convert question to lowercase and tokenize to keywords
        question_lower = question.lower()
        # Remove common stop words
        stop_words = {'a', 'an', 'the', 'is', 'are', 'do', 'does', 'what', 'when', 'where', 'how', 'why', 'who'}
        keywords = [word for word in re.findall(r'\b\w+\b', question_lower) if word not in stop_words]
        
        # Score chunks based on keyword matching
        scores = []
        for chunk in chunks:
            chunk_lower = chunk.lower()
            # Count occurrences of each keyword
            score = sum(chunk_lower.count(keyword) for keyword in keywords)
            # Bonus for chunks that contain multiple keywords
            unique_keywords = sum(1 for keyword in keywords if keyword in chunk_lower)
            score += unique_keywords * 2  # Weight for diversity of keywords
            scores.append(score)
        
        # If no good matches, return first chunks as default
        if max(scores) == 0:
            return "\n\n".join(chunks[:num_chunks])
        
        # Get top chunks
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:num_chunks]
        top_chunks = [chunks[i] for i in top_indices]
        
        # Return the most relevant chunks, joined with separators
        return "\n\n==========\n\n".join(top_chunks)
    
    def process_holidays_section(self, text):
        """Extract holiday information into structured data"""
        holidays = []
        # Find the holidays section using regex
        holiday_section = re.search(r'(?:Paid Holidays|Company Holidays)(.+?)(?:Next Section|\Z)', 
                                   text, re.DOTALL | re.IGNORECASE)
        
        if holiday_section:
            section_text = holiday_section.group(1)
            
            # Extract individual holidays using patterns
            holiday_pattern = r'([A-Z][a-zA-Z\s]+\b)(?:\s*[-–]\s*|\s*:\s*|\s+on\s+)?([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s*\d{4})?)?'
            matches = re.findall(holiday_pattern, section_text)
            
            for match in matches:
                holiday_name = match[0].strip()
                holiday_date = match[1].strip() if len(match) > 1 else ""
                
                if holiday_name and not holiday_name.lower().startswith(('section', 'note', 'please')):
                    holidays.append({
                        "name": holiday_name,
                        "date": holiday_date
                    })
        
        return holidays

    @st.cache_data
    def cached_load_pdf_content(self, filename=None, uploaded_file=None):
        """Cached version for Streamlit to avoid reprocessing PDFs"""
        return self.load_pdf_content(filename, uploaded_file)