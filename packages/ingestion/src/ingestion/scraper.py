import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin, urlparse
from tqdm import tqdm

# --- Configuration ---
BASE_URL = "https://portal.apvma.gov.au/"
SEARCH_URL = "https://portal.apvma.gov.au/pubcris"
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'data', 'labels')
MAX_PAGES = 2 # Limit for demonstration purposes, set to None to scrape all
PRODUCT_TYPE_FILTER = "HERBICIDE"

# --- Helper Functions ---
def get_session_params(url):
    """
    Fetches the initial page to get necessary session parameters (p_auth).
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        p_auth_input = soup.find('input', {'name': 'p_auth'})
        if not p_auth_input:
            raise ValueError("Could not find 'p_auth' token on the page. The site structure may have changed.")
        return p_auth_input['value']
    except requests.RequestException as e:
        print(f"Error fetching initial page: {e}")
        return None

def ensure_dir(directory):
    """
    Ensures that a directory exists, creating it if necessary.
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")

def download_pdf(pdf_url, filename):
    """
    Downloads a PDF from a given URL and saves it with a specific filename.
    """
    try:
        pdf_response = requests.get(pdf_url, stream=True)
        pdf_response.raise_for_status()
        
        # Get the total file size for the progress bar
        total_size = int(pdf_response.headers.get('content-length', 0))
        
        filepath = os.path.join(DOWNLOAD_DIR, filename)

        with open(filepath, 'wb') as f, tqdm(
            desc=filename,
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in pdf_response.iter_content(chunk_size=1024):
                size = f.write(data)
                bar.update(size)
        return True
    except requests.RequestException as e:
        print(f"  \\_ Error downloading {pdf_url}: {e}")
        return False

# --- Main Scraping Logic ---
def scrape_labels():
    """
    Main function to scrape herbicide labels from the APVMA portal.
    """
    print("Starting APVMA Herbicide Label Scraper...")
    ensure_dir(DOWNLOAD_DIR)

    p_auth = get_session_params(SEARCH_URL)
    if not p_auth:
        return

    print(f"Successfully obtained p_auth token: {p_auth}")

    session = requests.Session()
    current_page = 1
    product_links_found = set()

    while True:
        print(f"\\n--- Scraping Search Results Page {current_page} ---")
        
        form_data = {
            'p_auth': p_auth,
            'p_p_id': 'pubcrisportlet_WAR_pubcrisportlet',
            'p_p_lifecycle': '1',
            'p_p_state': 'normal',
            'p_p_mode': 'view',
            'p_p_col_id': 'column-1',
            'p_p_col_pos': '2',
            'p_p_col_count': '4',
            '_pubcrisportlet_WAR_pubcrisportlet_javax.portlet.action': 'search',
            '_pubcrisportlet_WAR_pubcrisportlet_cur': current_page,
            '_pubcrisportlet_WAR_pubcrisportlet_delta': 75, # Number of results per page
            '_pubcrisportlet_WAR_pubcrisportlet_keywords': '',
            '_pubcrisportlet_WAR_pubcrisportlet_productType': PRODUCT_TYPE_FILTER,
            '_pubcrisportlet_WAR_pubcrisportlet_orderByCol': 'name',
            '_pubcrisportlet_WAR_pubcrisportlet_orderByType': 'asc',
        }

        try:
            response = session.post(SEARCH_URL, data=form_data)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error posting search request for page {current_page}: {e}")
            break

        soup = BeautifulSoup(response.text, 'lxml')
        results_table = soup.find('table', class_='search-results-table')

        if not results_table:
            print("No more results tables found. Ending scrape.")
            break

        rows = results_table.find_all('tr')
        if len(rows) <= 1: # Only header row
            print("No more product rows found on this page. Ending scrape.")
            break
            
        new_links_on_page = 0
        for row in rows[1:]: # Skip header row
            cell = row.find('td')
            if cell and cell.a:
                link = cell.a['href']
                if link not in product_links_found:
                    product_links_found.add(link)
                    new_links_on_page += 1
        
        print(f"Found {new_links_on_page} new product links on page {current_page}.")

        if new_links_on_page == 0 and current_page > 1:
            print("No new links found on this page, assuming end of results.")
            break

        if MAX_PAGES and current_page >= MAX_PAGES:
            print(f"Reached max page limit of {MAX_PAGES}.")
            break
            
        current_page += 1

    print(f"\\n--- Found a total of {len(product_links_found)} unique product links. Now finding and downloading PDFs. ---")

    for product_url in tqdm(list(product_links_found), desc="Processing products"):
        try:
            product_page = session.get(product_url)
            product_page.raise_for_status()
            product_soup = BeautifulSoup(product_page.text, 'lxml')

            # Find the link to the e-label PDF
            elabel_link_tag = product_soup.find('a', text='e-label')
            if elabel_link_tag and elabel_link_tag['href']:
                pdf_url = elabel_link_tag['href']
                
                # Clean up URL if it's relative
                if not pdf_url.startswith('http'):
                    pdf_url = urljoin(BASE_URL, pdf_url)

                # Generate a clean filename from the URL
                parsed_url = urlparse(pdf_url)
                pdf_filename = os.path.basename(parsed_url.path)

                if not os.path.exists(os.path.join(DOWNLOAD_DIR, pdf_filename)):
                    print(f"  -> Found e-label: {pdf_filename}")
                    download_pdf(pdf_url, pdf_filename)
                else:
                    # print(f"  -> Skipping already downloaded file: {pdf_filename}")
                    pass

        except requests.RequestException as e:
            print(f"Error fetching product page {product_url}: {e}")
            continue

    print("\\nScraping complete.")

if __name__ == "__main__":
    scrape_labels()
