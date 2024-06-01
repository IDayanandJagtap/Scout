"""
Scout for accepting input as CAS number or element name and perfrom strict validation process
"""

import os
import re
from urllib.parse import urljoin, urlparse
import json
from datetime import datetime
import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup
from googlesearch import search

# Directories setup
PDFS_FOLDER = "./pdfs"
TEMP_FOLDER = "./temp"
LOGS_FOLDER = "./logs"
os.makedirs(PDFS_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs(LOGS_FOLDER, exist_ok=True)

# List of URLs to skip
SKIP_URLS = [
    "guidechem", "chemicalbook", "commonchemistry", "alpha-chemistry",
    "lookchem", "home", "pharmaffiliates", "login", "privacy", "linkedin",
    "twitter", "x.com", "facebook", "youtube", "support", "contact", "food",
    "chemicalbook.com", "guidechem.com", "pharmaffiliates.com",
    "benjaminmoore.com", "wikipedia", "imdb", "amazon", "ebay", "craigslist",
    "pinterest", "instagram", "tumblr", "reddit", "snapchat", "tiktok",
    "nytimes", "huffingtonpost", "forbes", "bloomberg", "bbc", "cnn",
    "foxnews", "nbcnews", "abcnews", "theguardian", "dailymail", "usatoday",
    "quora", "stackexchange", "stackoverflow", "tripadvisor", "yelp", "zomato",
    "opentable", "healthline", "webmd", "mayoclinic", "nih.gov", "cdc.gov",
    "fda.gov", "epa.gov", "google", "bing", "yahoo", "ask", "aol", "baidu",
    "msn", "duckduckgo", "yandex", "coursera", "udemy", "edx", "khanacademy",
    "linkedin.com", "twitter.com", "facebook.com", "youtube.com",
    "instagram.com", "tumblr.com", "reddit.com", "snapchat.com", "tiktok.com",
    "nytimes.com", "huffingtonpost.com", "forbes.com", "bloomberg.com",
    "bbc.com", "cnn.com", "foxnews.com", "nbcnews.com", "abcnews.com",
    "theguardian.com", "dailymail.co.uk", "usatoday.com", "quora.com",
    "stackexchange.com", "stackoverflow.com", "tripadvisor.com", "yelp.com",
    "zomato.com", "opentable.com", "healthline.com", "webmd.com",
    "mayoclinic.org", "nih.gov", "cdc.gov", "fda.gov", "epa.gov", "google.com",
    "bing.com", "yahoo.com", "ask.com", "aol.com", "baidu.com", "msn.com",
    "duckduckgo.com", "yandex.com", "coursera.org", "udemy.com", "edx.org",
    "login", "register", "signup", "signin", "faq", "terms",
    "conditions", "terms-of-service", "support", "help", "contact",
    "about", "my-account", "favourites", "bulkOrder", "cart"
]

# URL visit count dictionary
URL_VISIT_COUNT = {}
DOMAIN_VISIT_COUNT = {}
MAX_URL_VISITS = 5
MAX_DOMAIN_VISITS = 5

# Global report list
REPORT_LIST = []

# Limit for downloading files
DOWNLOAD_LIMIT = 5
DOWNLOADED_FILES_COUNT = 0

# Save report to JSON file
def save_report():
    """
    Save the global report list to a JSON file in the logs directory.

    The report includes details of each processed file such as the CAS number or name,
    filename, download status, and provider.
    """
    if REPORT_LIST:
        try:
            json_string = json.dumps(REPORT_LIST, indent=4)
            report_filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".json"
            report_filename = os.path.join(LOGS_FOLDER, report_filename)
            with open(report_filename, "w") as report_file:
                report_file.write(json_string)
            print(f"Scout report generated, check {report_filename}")
        except Exception as e:
            print(f"An error occurred while generating the report: {e}")
    else:
        print("NO REPORT GENERATED")

# Add report entry
def add_report(cas_or_name, filename, downloaded, provider):
    """
    Add an entry to the global report list.

    Params:
        cas_or_name (str): The CAS number or element name.
        filename (str): The name of the file.
        downloaded (bool): Whether the file was successfully downloaded.
        provider (str): The provider or source of the file.
    """
    report = {"cas_or_name": cas_or_name, "provider": provider, "downloaded": downloaded, "filename": filename}
    REPORT_LIST.append(report)

# Check if URL is a PDF
def is_pdf(url):
    """
    Check if a URL points to a PDF file.

    Params:
        url (str): The URL to check.

    Returns:
        bool: True if the URL points to a PDF file, False otherwise.
    """
    try:
        if url.endswith(".pdf"):
            return True
        response = requests.head(url, timeout=10)
        content_type = response.headers.get("content-type")
        return content_type == "application/pdf"
    except requests.Timeout:
        print(f"Timeout occurred while checking {url}")
        return False
    except Exception as e:
        print(f"Error occurred while checking {url}: {e}")
        return False

# Download PDF from URL
def download_pdf(url, folder_path):
    """
    Download a PDF file from a URL and save it to the specified folder.

    Params:
        url (str): The URL of the PDF file.
        folder_path (str): The folder path to save the PDF file.

    Returns:
        str: The file path of the downloaded PDF, or None if the download failed.
    """
    global DOWNLOADED_FILES_COUNT
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        if response.headers.get('content-type') == 'application/pdf':
            file_name = url.split("/")[-1]
            if not file_name.endswith(".pdf"):
                file_name += ".pdf"
            file_path = os.path.join(folder_path, file_name)
            with open(file_path, 'wb') as pdf_file:
                pdf_file.write(response.content)
            print(f"Downloaded: {file_name}")
            DOWNLOADED_FILES_COUNT += 1
            return file_path
        else:
            print(f"Skipping {url}, not a PDF file.")
            return None
    except requests.Timeout:
        print(f"Timeout occurred while downloading {url}")
    except requests.HTTPError as e:
        print(f"Failed to download {url}, HTTP error: {e}")
    except Exception as e:
        print(f"An error occurred while downloading {url}: {e}")
    return None

# Extract text from PDF
def extract_text_from_pdf(pdf_path):
    """
    Extract text content from a PDF file.

    Params:
        pdf_path (str): The file path of the PDF.

    Returns:
        str: The extracted text content, or None if extraction failed.
    """
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"An error occurred while extracting text from {pdf_path}: {e}")
        return None

# Set regular expression pattern
def set_pattern(sequence):
    """
    Create a regular expression pattern for a given sequence.

    Params:
        sequence (str): The sequence to escape and compile into a pattern.

    Returns:
        re.Pattern: The compiled regular expression pattern.
    """
    escaped_sequence = re.escape(sequence)
    return re.compile(rf'\b{escaped_sequence}\b', re.IGNORECASE)

# Verify PDF content
def verify_pdf(file_path, cas_or_name):
    """
    Verify if a PDF file contains the specified CAS number or element name and the phrase "safety data sheet".

    Params:
        file_path (str): The file path of the PDF.
        cas_or_name (str): The CAS number or element name to verify against.

    Returns:
        bool: True if both patterns are found in the PDF content, False otherwise.
    """
    text = extract_text_from_pdf(file_path)
    if text is None:
        return False
    pattern1 = set_pattern(cas_or_name)
    pattern2 = set_pattern("safety data sheet")
    return pattern1.search(text) and pattern2.search(text)

# Rename and move file
def rename_and_move_file(file_path, destination, cas_or_name, provider):
    """
    Rename and move a file to a specified destination folder, ensuring a unique filename.

    Params:
        file_path (str): The original file path.
        destination (str): The destination folder path.
        cas_or_name (str): The CAS number or element name for the new file name.
        provider (str): The provider name for the new file name.

    Returns:
        str: The new file name, or None if the operation failed.
    """
    try:
        # Generate a unique file name
        file_name = f"{cas_or_name}_{provider}.pdf"
        counter = 1
        while os.path.exists(os.path.join(destination, file_name)):
            file_name = f"{cas_or_name}_{provider}_{counter}.pdf"
            counter += 1

        # Move the file
        new_location = os.path.join(destination, file_name)
        os.rename(file_path, new_location)
        return file_name
    except Exception as e:
        print(f"An error occurred while renaming and moving file {file_path}: {e}")
    return None

# Scrape URLs from webpage
def scrape_urls(url, base_url, timeout=10):
    """
    Scrape URLs from a webpage.

    Params:
        url (str): The URL of the webpage to scrape.
        base_url (str): The base URL for resolving relative links.
        timeout (int, optional): The timeout for the request in seconds. Defaults to 10.

    Returns:
        list: A list of scraped URLs.
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        links = [
            urljoin(base_url, link['href'])
            for link in soup.find_all("a", href=True)
        ]
        return links
    except requests.Timeout:
        print(f"Timeout occurred while scraping links from: {url}")
    except requests.HTTPError as e:
        print(f"Failed to scrape links from {url}, HTTP error: {e}")
    except Exception as e:
        print(f"An error occurred while scraping links from {url}: {e}")
    return []

# Find PDFs recursively
def find_pdfs(url, depth=2, base_url=None, cas_or_name=None):
    """
    Recursively find PDFs from a URL, download and verify them.

    Params:
        url (str): The URL to start searching from.
        depth (int, optional): The depth of recursion. Defaults to 2.
        base_url (str, optional): The base URL for resolving relative links. Defaults to None.
        cas_or_name (str, optional): The CAS number or element name for verification. Defaults to None.
    """
    global DOWNLOADED_FILES_COUNT, URL_VISIT_COUNT, DOMAIN_VISIT_COUNT
    if depth <= 0 or DOWNLOADED_FILES_COUNT >= DOWNLOAD_LIMIT:
        return
    if any(skip_url in url.lower() for skip_url in SKIP_URLS):
        print(f"Skipped: {url}")
        return

    # Parse the domain from the URL
    domain = urlparse(url).netloc

    # Check if the domain visit count exceeds the limit
    if DOMAIN_VISIT_COUNT.get(domain, 0) >= MAX_DOMAIN_VISITS:
        print(f"Skipped: {url}, domain {domain} visited more than {MAX_DOMAIN_VISITS} times")
        return

    # Check if the specific URL visit count exceeds the limit
    if URL_VISIT_COUNT.get(url, 0) >= MAX_URL_VISITS:
        print(f"Skipped: {url}, URL visited more than {MAX_URL_VISITS} times")
        return

    # Update visit counts
    URL_VISIT_COUNT[url] = URL_VISIT_COUNT.get(url, 0) + 1
    DOMAIN_VISIT_COUNT[domain] = DOMAIN_VISIT_COUNT.get(domain, 0) + 1

    # Use base_url if provided, otherwise infer from the URL itself
    if not base_url:
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    if is_pdf(url):
        file_path = download_pdf(url, TEMP_FOLDER)
        if file_path:
            if verify_pdf(file_path, cas_or_name):
                print(f"Verification status: {file_path} is probably a MSDS")
                provider_name = base_url.split("/")[2]
                file_name = rename_and_move_file(file_path, PDFS_FOLDER, cas_or_name, provider_name)
                if file_name:
                    add_report(cas_or_name, file_name, True, provider_name)
            else:
                print(f"Verification status: {file_path} is not a verified MSDS")
                # Delete the file
                os.remove(file_path)
    else:
        links = scrape_urls(url, base_url)
        for link in links:
            find_pdfs(link, depth - 1, base_url, cas_or_name)

# Search Google for MSDS
def scout(cas_or_name, max_search_results=10):
    """
    Search for Material Safety Data Sheets (MSDS) using Google and process the results.

    Params:
        cas_or_name (str): The CAS number or element name to search for.
        max_search_results (int, optional): The maximum number of search results to process. Defaults to 10.
    """
    query = f"download msds of {cas_or_name}"
    print(f"Searching Google for: {query}")
    search_results = search(query, num=max_search_results, stop=max_search_results)
    for result in search_results:
        print(f"Google search result: {result}")
        find_pdfs(result, depth=2, base_url=None, cas_or_name=cas_or_name)
    save_report()


# User input handling
def main():
    """
    Main function to handle user input and start the scouting process.
    """
    cas_or_name = input("Enter CAS number or element name: ").strip()
    if not cas_or_name:
        print("No input provided. Exiting.")
        return

    scout(cas_or_name)



if __name__ == "__main__":
    main()


# cas - 106-38-7
# name - Benzene, 1-bromo-4-methyl-

'''
  1. requirements.txt
  2. log url
  3. selenium
  4. Improve static checks
'''
