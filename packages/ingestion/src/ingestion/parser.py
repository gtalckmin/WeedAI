import os
import asyncio
from llama_parse import LlamaParse
from dotenv import load_dotenv
from tqdm import tqdm
import glob

# Load environment variables
load_dotenv()

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'data')
LABELS_DIR = os.path.join(DATA_DIR, 'labels')
PARSED_DIR = os.path.join(DATA_DIR, 'parsed')

# Ensure output directory exists
os.makedirs(PARSED_DIR, exist_ok=True)

async def parse_pdf(parser, pdf_path, output_path):
    """Parses a single PDF and saves the markdown output."""
    try:
        # Check if already parsed
        if os.path.exists(output_path):
            return True

        # Parse the document
        documents = await parser.aload_data(pdf_path)
        
        # Combine text from all pages
        full_text = "\n\n".join([doc.text for doc in documents])
        
        # Save to markdown file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
            
        return True
    except Exception as e:
        print(f"Error parsing {os.path.basename(pdf_path)}: {e}")
        return False

async def main():
    api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    if not api_key:
        print("Error: LLAMA_CLOUD_API_KEY not found in environment variables.")
        print("Please set it in your .env file.")
        return

    print("Initializing LlamaParse...")
    parser = LlamaParse(
        api_key=api_key,
        result_type="markdown",
        verbose=False,
        language="en"
    )

    # Get list of PDF files
    pdf_files = glob.glob(os.path.join(LABELS_DIR, "*.pdf"))
    print(f"Found {len(pdf_files)} PDF files to parse.")

    # Process files
    success_count = 0
    fail_count = 0
    
    # Create tasks for concurrent processing (limit concurrency to avoid rate limits)
    # For simplicity in this script, we'll do it sequentially or with a small semaphore if needed.
    # LlamaParse async client handles some concurrency, but let's stick to a simple loop for clarity and rate limit safety first.
    
    for pdf_path in tqdm(pdf_files, desc="Parsing PDFs"):
        filename = os.path.basename(pdf_path)
        name_without_ext = os.path.splitext(filename)[0]
        output_filename = f"{name_without_ext}.md"
        output_path = os.path.join(PARSED_DIR, output_filename)
        
        if await parse_pdf(parser, pdf_path, output_path):
            success_count += 1
        else:
            fail_count += 1

    print("\nParsing Complete.")
    print(f"Successfully parsed: {success_count}")
    print(f"Failed: {fail_count}")

if __name__ == "__main__":
    asyncio.run(main())
