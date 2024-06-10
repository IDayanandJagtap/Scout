import os
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

import fitz
import pandas as pd
import requests
from bs4 import BeautifulSoup
from googlesearch import search
import aiohttp
import asyncio

PDFS_FOLDER = "./pdfs"
TEMP_FOLDER = "./temp"
LOGS_FOLDER = "./logs"
os.makedirs(PDFS_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs(LOGS_FOLDER, exist_ok=True)

SKIP_URLS = set([
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
    "login", "register", "signup", "signin", "faq", "terms", "conditions",
    "terms-of-service", "support", "help", "contact", "about", "my-account",
    "favourites", "bulkOrder", "cart", "cdh", "loba", "finar", "apple",
    "echa.europa", "chembase", "scribd", "whatsapp"
])

# Globals
DOWNLOAD_LIMIT = 3
DOWNLOAD_COUNTER = {}
INSTANCE_NUMBER = 0
REPORT_FILENAME = ""


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
		response = requests.head(url, timeout=7)
		content_type = response.headers.get("content-type")
		return content_type == "application/pdf"
	except requests.Timeout:
		print(f"Timeout occurred while checking {url}")
		return False
	except Exception as e:
		print(f"Error occurred while checking {url}: {e}")
		return False


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
		async with session.get(url, timeout=3) as response:
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
			if pageno > 5:
				break
			text += page.get_text()
		doc.close()
		return text
	except Exception as e:
		print(f"An error occurred while extracting text from {pdf_path}: {e}")
		return None


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


def verify_pdf(file_path, cas=None):
	"""
	Verify if a PDF file contains the specified CAS number or element name and the phrase "safety data sheet".

	Params:
			file_path (str): The file path of the PDF.
			cas (str) : The CAS number to verify against.

	Returns:
			True if the CAS no is found in the PDF along with the phrase 'safety data sheet'. False otherwise.
	"""
	text = extract_text_from_pdf(file_path)
	if text is None:
		return False
	pattern1 = set_pattern(cas)
	pattern2 = set_pattern("safety data sheet")
	return pattern1.search(text) and pattern2.search(text)


def rename_and_move_file(file_path, destination, id="", name="", provider=""):
	"""
	Rename and move a file to a specified destination folder, ensuring a unique filename.

	Params:
			file_path (str): The original file path.
			destination (str): The destination folder path.
			id (str) : The serial no of the chemical.
			name (str) : The name of the Chemical.
			provider (str): The provider name for the new file name.

	Returns:
			str: The new file name, or None if the operation failed.
	"""
	try:
		new_name = f"{id}_{name}_{provider}.pdf"
		new_location = os.path.join(destination, new_name)
		os.rename(file_path, new_location)
	except Exception as e:
		print(f"An error occurred while renaming and moving file {file_path}: {e}")


async def scrape_urls(session, url, base_url, timeout=7):
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
			soup = BeautifulSoup(await response.text(), "html.parser")
			links = [
			    urljoin(base_url, link['href'])
			    for link in soup.find_all("a", href=True)
			]
			return links
	except Exception as e:
		print(f"An error occurred while scraping links from {url}: {e}")
		return []


async def find_pdfs(session,
                    url,
                    depth=2,
                    base_url=None,
                    cas=None,
                    id="",
                    name="",
                    domain_count=None):
	"""
	Recursively find PDFs from a URL, download and verify them.

	Params:
			session (aiohttp.ClientSession): The session to use for making an async http request.
			url (str): The URL to start searching from.
			depth (int, optional): The depth of recursion. Defaults to 3.
			base_url (str, optional): The base URL for resolving relative links. Defaults to None.
			cas (str) : The CAS number. Defaults to None.
			id (str) : The serial no of the chemical. Defaults to empty string.
			name (str): The Element name for verification. Defaults to empty string.
			domain_count (dic) : Store the visited domain count. 
	"""

	global DOWNLOAD_COUNTER

	if depth <= 0:
		return

	if not base_url:
		base_url = url

	if any(skip in url for skip in SKIP_URLS):
		return

	netloc = urlparse(url).netloc
	if domain_count is None:
		domain_count = {}
	domain_count[netloc] = domain_count.get(netloc, 0) + 1

	if domain_count[netloc] > 5:
		print(f"Skipping {url}, domain {netloc} scraped more than 5 times.")
		return

	if DOWNLOAD_COUNTER.get(cas, 0) >= DOWNLOAD_LIMIT:
		print(f"Reached download limit for CAS number {cas}")
		return

	print(f"Finding PDFs on: {url}")
	if is_pdf(url):
		file_path = await download_pdf(session, url)
		if file_path:
			if verify_pdf(file_path, cas):
				print(f"Verification status: {file_path} is probably a MSDS")
				provider_name = base_url.split("/")[2]
				rename_and_move_file(file_path, PDFS_FOLDER, id, name, provider_name)

				DOWNLOAD_COUNTER[cas] = DOWNLOAD_COUNTER.get(
				    cas, 0) + 1  #increment the download count
			else:
				print(f"Verification status: {file_path} is not a MSDS")
				os.remove(file_path)
	else:
		links = await scrape_urls(session, url, base_url)
		for link in links:
			await find_pdfs(session, link, depth - 1, base_url, cas, id, name,
			                domain_count)


def initialise_report_file():
	'''
	Initialise the report file.

	Returns : 
		report_file (str): The path of the report file.  

	'''
	report_file_name = "Excel_" + datetime.now().strftime(
	    "%Y-%m-%d_%H-%M-%S") + "_" + str(INSTANCE_NUMBER) + ".csv"

	with open(os.path.join(LOGS_FOLDER, report_file_name), 'w') as report_file:
		report_file.write(
		    "Id,Cas,Name,Downloaded,Found_by,No_of_downloads, Done_by" + "\n")

	return report_file_name


def save_report(report_file, id, cas, name, no_of_downloads, found_by="CAS"):
	'''
	Save the report into csv file.

	Params : 
		id (str) : The serial no of the chemical.
		cas (str) : The CAS number.
		name (str) : The Element name of the chemical.
		no_of_downloads (int) : The number of MSDS PDF's downloaded.
		found_by (str) : The method by which the PDF was found. Defaults to CAS
	'''
	downloaded = no_of_downloads > 0
	quoted_name = f'"{name}"'
	done_by = "Scout" if downloaded else ""
	found_by = found_by if downloaded else ""

	csv_report_string = f"{id},{cas},{quoted_name},{downloaded}, {found_by}, {no_of_downloads}, {done_by}"
	with open(os.path.join(LOGS_FOLDER, report_file), "a") as file:
		file.write(csv_report_string + "\n")


async def scout(session, id=None, cas=None, name=None, max_search_results=10):
	"""
	Search for Material Safety Data Sheets (MSDS) using Google and process the results.

	Params:
		  session (aiophttp.ClientSession): The session to use for making an async http request.
			id (str) : The ID (serial no) of the chemical. Defaults to None.
			cas (str) : The CAS number to search for. 
			name (str): The Element name to search for.
			max_search_results (int, optional): The maximum number of search results to process. Defaults to 10.

	"""
	query = f"download msds of {cas or name}"
	print(f"Searching google for query: {query}")
	try:
		searched_results = list(
		    search(query, num=max_search_results, stop=max_search_results))
		print("\nSEARCHED RESULTS: ", searched_results, "\n\n")
	except Exception as e:
		print(f"An error occurred while searching: {e}")
		return

	for url in searched_results:
		try:
			await find_pdfs(session,
			                url,
			                depth=2,
			                cas=cas,
			                id=id,
			                name=name,
			                domain_count=None)
		except Exception as e:
			print(f"An error occurred while processing URL {url}: {e}")


# Process the excel file. Starting point of execution
async def process_excel(file_path):
	'''
	Read the excel file and process the data.
	Calls the scout function on each row of the excel file.

	Params : 
		file_path (str) : The file path of the excel file.
	'''
	msds_df = pd.read_excel(file_path, dtype=str)  #read excel file
	#initialise report file
	report_file = initialise_report_file()

	# Create a asynchrounous session
	async with aiohttp.ClientSession() as session:
		for index, row in msds_df.iterrows():  # process each row
			cas = row['CAS']
			name = row.get('ChemName', '')
			id = row.get('ID', '')
			# call scout
			await scout(session, id=id, cas=cas, name=name)
			msds_count = DOWNLOAD_COUNTER.get(
			    cas, 0)  # Get the msds(of current row) download count
			save_report(
			    report_file, id=id, cas=cas, name=name,
			    no_of_downloads=msds_count)  # Save the status to report file(.csv)



