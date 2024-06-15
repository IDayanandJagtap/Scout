# Scout: Crawler for Automation and Reporting

## Overview

Scout is a Python-based automation tool designed to download, verify, and process Material Safety Data Sheets (MSDS) from PDFs. The tool can scrape websites for PDF files, verify their content, and organize them in a structured manner. It also logs the process and generates a JSON report.

## Features

-   **PDF Downloading**: Downloads PDF files from specified URLs.
-   **Content Verification**: Verifies the content of PDFs to ensure they are MSDS files.
-   **File Management**: Renames and moves verified PDFs to designated folders.
-   **Web Scraping**: Recursively scrapes websites for PDF links.
-   **JSON Report Generation**: Generates a detailed report of the processed files.

## API usage
Scout provides an API service to access it's functionality. 


### 1. Search for MSDS
```
https://scout-api.azurewebsites.net/scout/CAS_OR_NAME
```
- **Method** : `Get`
- **Query (CAS_OR_NAME)** : You need to provide a valid CAS Number or the Chemical Name. Example
    ```
    https://scout-api.azurewebsites.net/scout/106-38-7
    https://scout-api.azurewebsites.net/scout/methanol
    ```
- **Response**: A JSON response with the entire search detials is provided. Example
  
    ```
    [
        {
            "cas": null,
            "name": "methanol",
            "provider": "beta-static.fishersci.com",
            "verified": true,
            "filepath": "verified/methanol_beta-static.fishersci.com_3.pdf",
            "url": "https://beta-static.fishersci.com/content/dam/fishersci/en_US/documents/programs/education/regulatory-documents/sds/chemicals/chemicals-m/S25426A.pdf"
        }, ...
    ]
    ```
  

### 2.Access files :
To access the downloaded files use the following api
```
https://scout-api.azurewebsites.net/FILEPATH
```
- **Method** : `Get`
- **Query (FILEPATH)** : The path of the file. It is present in the response as `filepath`. Example

    ```
    https://scout-api.azurewebsites.net/verified/methanol_beta-static.fishersci.com_3.pdf
    ```
<br>

----------------

<br>

# Local Installation:

## Requirements

-   Python 3.7+
-   Required Python Packages:
    -   `PyMuPDF`
    -   `requests`
    -   `beautifulsoup4`
    -   `googlesearch-python`

You can install the required packages using:

```bash
pip install -r requirements.txt
```

## Installation

1. Clone this repository

```
git clone https://github.com/IDayanandJagtap/scout.git
cd scout
```

2. Install required python packages using

```
pip install -r requirements.txt
```

## Usage

-   To run scout from command line run

```
python scout_strict.py
```

## Logging

-   Check the logs in `./logs/` directory.
-   Each run generates a log file with a timestamp.

## Configurations

- PDFS_FOLDER: Directory to store downloaded PDFs.
- TEMP_FOLDER: Temporary directory for intermediate files.
- LOGS_FOLDER: Directory to store logs.
- SKIP_URLS: List of URLs to skip during the scraping process.
- DOWNLOAD_LIMIT: Limit for the number of downloads per item.

These configurations can be found and modified in the script.

## Contributors

- Atharva Sawant
- Dayanand Jagtap
- Saba Shaikh
- Shireen Tekade

## Contact

For any questions or support, please open an issue on GitHub or contact [dayanandjagtap07@gmail.com].
