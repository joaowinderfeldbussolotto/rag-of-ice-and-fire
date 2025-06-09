from pathlib import Path
from PyPDF2 import PdfReader


def extract_pdf_text(pdf_path: str, start_page: int = 15, end_page = 170) -> str:
    """Extract text from PDF starting from specified page."""
    
    with open(pdf_path, 'rb') as file:
        pdf_reader = PdfReader(file)
        total_pages = len(pdf_reader.pages)
        
        print(f"PDF has {total_pages} pages, extracting from page {start_page} until {end_page}...")
        
        extracted_text = []
        
        for page_num in range(start_page - 1, end_page):
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            
            if text.strip():
                extracted_text.append(text)
        
        return "\n\n".join(extracted_text)


def save_text_file(text: str, output_path: str) -> None:
    """Save text to file, creating directories if needed."""
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(text)
    
    print(f"Text saved to: {output_path}")


def main():
    """Extract text from PDF and save to file."""
    
    pdf_path = "./data/Summary of A Song of Ice and Fire, vol. 1-5 (v1.2).pdf"
    output_path = "./graphragtest/input/GOT_chapter_summaries.txt"
    
    try:
        # Extract text from PDF starting from page 6
        text = extract_pdf_text(pdf_path, start_page=15, end_page=554)
        
        # Save to text file
        save_text_file(text, output_path)
        
        print(f"✅ Successfully extracted {len(text)} characters")
        
    except FileNotFoundError:
        print(f"❌ PDF file not found: {pdf_path}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()