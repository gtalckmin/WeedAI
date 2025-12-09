import csv
import os
import requests
from tqdm import tqdm
from urllib.parse import urljoin

# --- Configuration ---
BASE_URL = "https://elabels.apvma.gov.au/"
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
# Assuming search-results.csv is in packages/ingestion/
CSV_PATH = os.path.join(PACKAGE_DIR, '..', '..', 'search-results.csv')
DOWNLOAD_DIR = os.path.join(PACKAGE_DIR, '..', '..', '..', '..', 'data', 'labels')

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def download_pdf(pdf_url, filename):
    try:
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        if os.path.exists(filepath):
            return True # Skip if exists

        response = requests.get(pdf_url, stream=True)
        if response.status_code == 404:
            # print(f"  [404] Label not found for {filename}")
            return False
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(filepath, 'wb') as f, tqdm(
            desc=filename,
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
            leave=False
        ) as bar:
            for data in response.iter_content(chunk_size=1024):
                size = f.write(data)
                bar.update(size)
        return True
    except Exception as e:
        print(f"  Error downloading {filename}: {e}")
        return False

def process_csv():
    print(f"Reading CSV from: {CSV_PATH}")
    ensure_dir(DOWNLOAD_DIR)
    
    unique_actives = set()
    products_to_download = []

    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            actives = row.get('Actives', '').strip()
            product_no = row.get('No', '').strip()
            
            if not actives or not product_no:
                continue

            # Normalization could be added here (e.g., sorting ingredients), 
            # but for now we trust the string representation
            if actives not in unique_actives:
                unique_actives.add(actives)
                products_to_download.append({
                    'no': product_no,
                    'actives': actives,
                    'name': row.get('Name', 'Unknown')
                })

    print(f"Found {len(products_to_download)} unique active ingredient combinations.")
    
    success_count = 0
    fail_count = 0

    for product in tqdm(products_to_download, desc="Downloading Labels"):
        product_no = product['no']
        filename = f"{product_no}ELBL.pdf"
        url = f"{BASE_URL}{filename}"
        
        if download_pdf(url, filename):
            success_count += 1
        else:
            fail_count += 1

    print(f"\nDownload Complete.")
    print(f"Successfully downloaded: {success_count}")
    print(f"Failed/Not Found: {fail_count}")

if __name__ == "__main__":
    process_csv()
