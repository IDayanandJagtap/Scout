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
REPORT_LIST = []
INSTANCE_NUMBER = 0
REPORT_FILENAME = ""


def is_pdf(url):
		"""
				Check if url points to a pdf file
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


async def download_pdf(session, url, folder_path):
		try:
				async with session.get(url, timeout=3) as response:
						response.raise_for_status()
						if response.headers.get('content-type') == 'application/pdf':
								file_name = url.split("/")[-1]
								if not file_name.endswith(".pdf"):
										file_name += ".pdf"
								file_path = os.path.join(folder_path, file_name)
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


def set_pattern(sequence):
		escaped_sequence = re.escape(sequence)
		return re.compile(rf'\b{escaped_sequence}\b', re.IGNORECASE)


def verify_pdf(file_path, cas=None):
		text = extract_text_from_pdf(file_path)
		if text is None:
				return False
		pattern1 = set_pattern(cas)
		pattern2 = set_pattern("safety data sheet")
		return pattern1.search(text) and pattern2.search(text)


def rename_and_move_file(file_path,
												 destination,
												 id="",
												 cas="",
												 name="",
												 manufacturer=""):
		try:
				new_name = f"{id}_{name}_{manufacturer}.pdf"
				new_location = os.path.join(destination, new_name)
				os.rename(file_path, new_location)
		except Exception as e:
				print(
						f"An error occurred while renaming and moving file {file_path}: {e}"
				)


async def scrape_urls(session, url, base_url, timeout=7):
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
				file_path = await download_pdf(session, url, TEMP_FOLDER)
				if file_path:
						if verify_pdf(file_path, cas):
								print(f"Verification status: {file_path} is probably a MSDS")
								provider_name = base_url.split("/")[2]
								rename_and_move_file(file_path, PDFS_FOLDER, id, cas, name,
																		 provider_name)

								DOWNLOAD_COUNTER[cas] = DOWNLOAD_COUNTER.get(cas, 0) + 1
						else:
								print(f"Verification status: {file_path} is not a MSDS")
								os.remove(file_path)
		else:
				links = await scrape_urls(session, url, base_url)
				for link in links:
						await find_pdfs(session, link, depth - 1, base_url, cas, id, name,
														domain_count)


def initialise_report_file():
		global REPORT_FILENAME
		REPORT_FILENAME = "Excel_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_" + str(
				INSTANCE_NUMBER) + ".csv"
		with open(os.path.join(LOGS_FOLDER, REPORT_FILENAME), 'w') as report_file:
				report_file.write(
						"Id,Cas,Name,Downloaded,Found_by,No_of_downloads, Done_by")


def save_report(id, cas, name, no_of_downloads, found_by="CAS"):
		downloaded = no_of_downloads > 0
		quoted_name = f'"{name}"'
		done_by = "Scout" if downloaded else ""
		found_by = found_by if downloaded else ""

		csv_report_string = f"{id},{cas},{quoted_name},{downloaded}, {found_by}, {no_of_downloads}, {done_by}"
		with open(os.path.join(LOGS_FOLDER, REPORT_FILENAME), "a") as report_file:
				report_file.write("\n")
				report_file.write(csv_report_string)


async def scout(session, id=None, cas=None, name=None, max_search_results=10):
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


async def process_excel(file_path):
		msds_df = pd.read_excel(file_path, dtype=str)
		initialise_report_file()
		async with aiohttp.ClientSession() as session:
				for index, row in msds_df.iterrows():
						cas = row['CAS']
						name = row.get('ChemName', '')
						id = row.get('ID', '')
						await scout(session, id=id, cas=cas, name=name)
						msds_count = DOWNLOAD_COUNTER.get(cas, 0)
						save_report(id=id, cas=cas, name=name, no_of_downloads=msds_count)


