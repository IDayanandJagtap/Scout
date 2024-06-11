import os
import re
from urllib.parse import urljoin, urlparse
import json
from datetime import datetime
import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup
from googlesearch import search
import aiohttp

# Directories setup
PDFS_FOLDER = "./verified"
TEMP_FOLDER = "./unverified"
LOGS_FOLDER = "./logs"
os.makedirs(PDFS_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs(LOGS_FOLDER, exist_ok=True)

# List of URLs to skip
SKIP_URLS = set([
    "guidechem",
    "chemicalbook",
    "commonchemistry",
    "alpha-chemistry",
    "lookchem",
    "home",
    "pharmaffiliates",
    "login",
    "privacy",
    "linkedin",
    "twitter",
    "x.com",
    "facebook",
    "youtube",
    "support",
    "contact",
    "food",
    "chemicalbook.com",
    "guidechem.com",
    "pharmaffiliates.com",
    "benjaminmoore.com",
    "wikipedia",
    "imdb",
    "amazon",
    "ebay",
    "craigslist",
    "pinterest",
    "instagram",
    "tumblr",
    "reddit",
    "snapchat",
    "tiktok",
    "nytimes",
    "huffingtonpost",
    "forbes",
    "bloomberg",
    "bbc",
    "cnn",
    "foxnews",
    "nbcnews",
    "abcnews",
    "theguardian",
    "dailymail",
    "usatoday",
    "quora",
    "stackexchange",
    "stackoverflow",
    "tripadvisor",
    "yelp",
    "zomato",
    "opentable",
    "healthline",
    "webmd",
    "mayoclinic",
    "nih.gov",
    "cdc.gov",
    "fda.gov",
    "epa.gov",
    "google",
    "bing",
    "yahoo",
    "ask",
    "aol",
    "baidu",
    "msn",
    "duckduckgo",
    "yandex",
    "coursera",
    "udemy",
    "edx",
    "khanacademy",
    "linkedin.com",
    "twitter.com",
    "facebook.com",
    "youtube.com",
    "instagram.com",
    "tumblr.com",
    "reddit.com",
    "snapchat.com",
    "tiktok.com",
    "nytimes.com",
    "huffingtonpost.com",
    "forbes.com",
    "bloomberg.com",
    "bbc.com",
    "cnn.com",
    "foxnews.com",
    "nbcnews.com",
    "abcnews.com",
    "theguardian.com",
    "dailymail.co.uk",
    "usatoday.com",
    "quora.com",
    "stackexchange.com",
    "stackoverflow.com",
    "tripadvisor.com",
    "yelp.com",
    "zomato.com",
    "opentable.com",
    "healthline.com",
    "webmd.com",
    "mayoclinic.org",
    "nih.gov",
    "cdc.gov",
    "fda.gov",
    "epa.gov",
    "google.com",
    "bing.com",
    "yahoo.com",
    "ask.com",
    "aol.com",
    "baidu.com",
    "msn.com",
    "duckduckgo.com",
    "yandex.com",
    "coursera.org",
    "udemy.com",
    "edx.org",
    "login",
    "register",
    "signup",
    "signin",
    "faq",
    "terms",
    "conditions",
    "terms-of-service",
    "support",
    "help",
    "contact",
    "about",
    "my-account",
    "favourites",
    "bulkOrder",
    "cart",
    "pinterest",
    "scribd",
])


# Save report to JSON file
def save_report(report_list):
    """
    Save the global report list to a JSON file in the logs directory.
    The report includes details of each processed file such as the CAS number or name,
    filename, download status, and provider.

    Params: 
        report_list(list) : A list of dictionary containing the necessary info

    Return: 
        The json report.
    """
    if report_list:
        try:
            json_string = json.dumps(
                report_list, indent=4)  # convert the list to json string
            report_filename = datetime.now(
            ).strftime(  # create a report file name
                "%Y-%m-%d_%H-%M-%S") + ".json"
            report_filename = os.path.join(LOGS_FOLDER, report_filename)
            # write the json string in the report file
            with open(report_filename, "w") as report_file:
                report_file.write(json_string)
            print(f"Scout report generated, check {report_filename}")
            # return the json string
            return json.loads(json_string)
        except Exception as e:
            print(f"An error occurred while generating the report: {e}")
    else:
        print("NO REPORT GENERATED")

    return {}


# Add report entry
def add_report(report_list, cas, name, filepath, verified, provider, url):
    """
    Add an entry to the global report list.

    Params:
        report_list (list) : The new entry(report) to be appended to this list.
        cas (str) : The CAS number.
        name (str): The Element name.
        filepath (str): The path of the file.
        verified (bool): Is the file strictly verified.
        provider (str): The provider or source of the file.
        url (str) : The url from which the pdf is downloaded.
    """
    # Modify the filepath to access the file via static route
    filepath = filepath[2:]  # ./verified/filename becomes verfied/filename
    # Append the new entry to the report list
    report = {
        "cas": cas,
        "name": name,
        "provider": provider,
        "verified": verified,
        "filepath": filepath,
        "url": url
    }
    report_list.append(report)


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
async def download_pdf(session, url):
    """
    Download a PDF file from a URL and save it to the specified folder.

    Params:
        session (aiohttp.ClientSession): The session to use for the download.
        url (str): The URL of the PDF file.

    Returns:
        str: The file path of the downloaded PDF, or None if the download failed.
    """

    try:
        async with session.get(url, timeout=10) as response:
            response.raise_for_status()
            if response.headers.get('content-type') == 'application/pdf':
                file_name = url.split("/")[-1]
                if not file_name.endswith(".pdf"):
                    file_name += ".pdf"
                file_path = os.path.join(TEMP_FOLDER, file_name)

                with open(file_path, 'wb') as pdf_file:
                    pdf_file.write(await response.read())
                print(f"Downloaded: {file_name}")

                return file_path
            else:
                print(f"Skipping {url}, not a PDF file.")
                return None
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
        for pageno, page in enumerate(doc, start=1):
            if pageno > 5:  # read only first 5 pages
                break
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
def verify_pdf(file_path, cas=None, name=None):
    """
    Verify if a PDF file contains the specified CAS number or element name and the phrase "safety data sheet".

    Params:
        file_path (str): The file path of the PDF.
        cas (str) : The CAS number.
        name (str): The Element name to verify against.

    Returns:
        "same" : if the PDF contains the specified CAS number and the phrase "safety data sheet".
        "similar" : if the PDF contains a part of the element name and the phrase "safety data sheet". 
         False otherwise.
    """
    text = extract_text_from_pdf(file_path)
    if text is None:
        return False
    pattern1 = set_pattern(cas or name)
    pattern2 = set_pattern("safety data sheet")
    if name is not None:
        pattern3 = re.compile('|'.join(map(re.escape, name.split())),
                              re.IGNORECASE)
    # exact match
    if pattern1.search(text) and pattern2.search(text):
        return "same"
    elif name is not None and pattern2.search(text) and pattern3.search(text):
        return "similar"

    return False


# Rename and move file
def rename_and_move_file(file_path, destination, cas, name, provider):
    """
    Rename and move a file to a specified destination folder, ensuring a unique filename.

    Params:
        file_path (str): The original file path.
        destination (str): The destination folder path.
        cas (str): The CAS number or element name for the new file name.
        name (str) : The name of the Chemical.
        provider (str): The provider name for the new file name.

    Returns:
        str: The new file name, or None if the operation failed.
    """
    try:
        # Generate a unique file name
        file_name = f"{cas or name}_{provider}.pdf"
        counter = 1
        while os.path.exists(os.path.join(destination, file_name)):
            file_name = f"{cas or name}_{provider}_{counter}.pdf"
            counter += 1

        # Move the file
        new_location = os.path.join(destination, file_name)
        os.rename(file_path, new_location)
        return new_location
    except Exception as e:
        print(
            f"An error occurred while renaming and moving file {file_path}: {e}"
        )
    return None


# Scrape URLs from webpage
async def scrape_urls(session, url, base_url, timeout=10):
    """
    Scrape URLs from a webpage.

    Params:
        session (aiohttp.ClientSession): The session to use for making an async http request.
        url (str): The URL of the webpage to scrape.
        base_url (str): The base URL for resolving relative links.
        timeout (int, optional): The timeout for the request in seconds. Defaults to 10.

    Returns:
        list: A list of scraped URLs.
    """
    try:
        async with session.get(url, timeout=timeout) as response:
            response.raise_for_status()
            soup = BeautifulSoup(await response.text(),
                                 "html.parser")  # Parse the html from the url
            # find hrefs from the html
            links = [
                urljoin(base_url, link['href'])
                for link in soup.find_all("a", href=True)
            ]
            return links
    except Exception as e:
        print(f"An error occurred while scraping links from {url}: {e}")
    return []


# Find PDFs recursively
async def find_pdfs(session,
                    url,
                    depth=3,
                    base_url=None,
                    cas=None,
                    name=None,
                    config_params={}):
    """
    Recursively find PDFs from a URL, download and verify them.

    Params:
        session (aiohttp.ClientSession): The session to use for making an async http request.
        url (str): The URL to start searching from.
        depth (int, optional): The depth of recursion. Defaults to 3.
        base_url (str, optional): The base URL for resolving relative links. Defaults to None.
        cas (str) : The CAS number. Defaults to None.
        name (str): The Element name for verification. Defaults to None.
        config_params (dict) : Contains required config params. 
    """

    # extract config params
    DOWNLOADED_FILES_COUNT = config_params.get("DOWNLODED_FILES_COUNT", 0)
    DOWNLOAD_LIMIT = config_params.get("download_limit", 0)
    URL_VISIT_COUNT = config_params.get("url_visit_count", {})
    DOMAIN_VISIT_COUNT = config_params.get("domain_visit_count", {})
    MAX_URL_VISITS = config_params.get("max_url_visits", 0)
    MAX_DOMAIN_VISITS = config_params.get("max_domain_visits", 0)
    REPORT_LIST = config_params.get("report_list", [])

    # Depth check and stop when limit exceeded
    if depth <= 0 or DOWNLOADED_FILES_COUNT >= DOWNLOAD_LIMIT:
        return

    # check whether to skip the current url
    if any(skip_url in url.lower() for skip_url in SKIP_URLS):
        print(f"Skipped: {url}")
        return

    # Parse the domain from the URL
    domain = urlparse(url).netloc

    # Check if the domain visit count exceeds the limit
    if DOMAIN_VISIT_COUNT.get(domain, 0) >= MAX_DOMAIN_VISITS:
        print(
            f"Skipped: {url}, domain {domain} visited more than {MAX_DOMAIN_VISITS} times"
        )
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
        file_path = await download_pdf(session, url)
        if file_path:
            verification_status = verify_pdf(
                file_path, cas, name)  # check the verification status
            provider_name = base_url.split("/")[2]  # get the provider name
            DOWNLOADED_FILES_COUNT += 1  # increment the download count
            if verification_status == "same":  # strict validation
                print(
                    f"Verification status: {file_path} is probably the required MSDS"
                )
                new_file_path = rename_and_move_file(
                    file_path, PDFS_FOLDER, cas, name,
                    provider_name)  # move file to the verified folder
                if new_file_path:
                    add_report(REPORT_LIST, cas, name, new_file_path, True,
                               provider_name, url)

            elif verification_status == "similar":  # flexible validation
                print(
                    f"Verification status: {file_path} may be the required MSDS"
                )
                add_report(REPORT_LIST, cas, name, file_path, False,
                           provider_name, url)

            else:
                print(f"Verification status: {file_path} is not a MSDS")
                os.remove(file_path)  # Delete the unnecessary files
                DOWNLOADED_FILES_COUNT -= 1  # decrement the download count
    else:
        links = await scrape_urls(session, url, base_url)
        for link in links:
            params = {
                "downloaded_files_count": DOWNLOADED_FILES_COUNT,
                "download_limit": DOWNLOAD_LIMIT,
                "url_visit_count": URL_VISIT_COUNT,
                "domain_visit_count": DOMAIN_VISIT_COUNT,
                "max_url_visits": MAX_URL_VISITS,
                "max_domain_visits": MAX_DOMAIN_VISITS,
                "report_list": REPORT_LIST
            }
            await find_pdfs(session, link, depth - 1, base_url, cas, name,
                            params)  # recursive call to find_pdfs


# Search Google for MSDS
async def scout(cas, name, max_search_results=10):
    """
    Search for Material Safety Data Sheets (MSDS) using Google and process the results.

    Params:
        cas (str) : The CAS number to search for. 
        name (str): The Element name to search for.
        max_search_results (int, optional): The maximum number of search results to process. Defaults to 10.

    Returns : 
        json_report (json) : It returns the generated report as json string.
    """

    if cas is None and name is None:
        print("No input provided. Exiting.")
        return

    # Report list :
    report_list = []

    # create query and do a google search
    query = f"download msds of {cas or name}"
    print(f"Searching Google for: {query}")
    search_results = search(query,
                            num=max_search_results,
                            stop=max_search_results)
    # Create async session
    async with aiohttp.ClientSession() as session:
        for result in search_results:
            print(f"Google search result: {result}")
            try:
                # create params
                config_params = {
                    "report_list": report_list,
                    "url_visit_count": {},
                    "domain_visit_count": {},
                    "max_url_visits": 5,
                    "max_domain_visits": 10,
                    "download_limit": 5,
                    "downloaded_files_count": 0,
                }

                await find_pdfs(session,
                                result,
                                depth=2,
                                base_url=None,
                                cas=cas,
                                name=name,
                                config_params=config_params)
            except Exception as e:
                print(f"An error occurred while searching {result}: {e}")

    # save report
    report_in_json = save_report(report_list)
    return report_in_json


# cas - 106-38-7
# name - Benzene, 1-bromo-4-methyl-
'''

  Next :
  1. Generate proper file path.
  2. selenium


'''
