# REQUIRES: requests, beautifulsoup4

import requests
from bs4 import BeautifulSoup
import logging
from typing import Optional

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TARGET_URL = "https://example.com"
TIMEOUT_SECONDS = 10

def fetch_and_parse_title(url: str) -> Optional[str]:
    """
    Fetches the content of a given URL and extracts the HTML title tag.

    Args:
        url: The URL to fetch.

    Returns:
        The text content of the title tag, or None if fetching or parsing fails.
    """
    logging.info(f"Attempting to fetch URL: {url}")

    try:
        # Use requests.get to fetch the content. Set a reasonable timeout.
        response = requests.get(url, timeout=TIMEOUT_SECONDS)
        
        # Raise HTTPError for bad responses (4xx or 5xx status codes)
        response.raise_for_status() 

    except requests.exceptions.Timeout:
        logging.error(f"Request timed out after {TIMEOUT_SECONDS} seconds for {url}")
        return None
    except requests.exceptions.ConnectionError as e:
        logging.error(f"Connection error occurred while fetching {url}: {e}")
        return None
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error occurred while fetching {url}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        # Catch all other requests exceptions (e.g., TooManyRedirects, invalid URL)
        logging.error(f"An unexpected request error occurred for {url}: {e}")
        return None

    logging.info(f"Successfully fetched content (Status: {response.status_code}). Starting parsing.")

    try:
        # Initialize BeautifulSoup parser using the standard 'html.parser'
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the title tag
        title_tag = soup.find('title')

        if title_tag:
            # Extract the text content, stripping leading/trailing whitespace
            title_text = title_tag.get_text(strip=True)
            logging.info(f"Successfully extracted title.")
            return title_text
        else:
            logging.warning("Title tag not found in the HTML content.")
            return None

    except Exception as e:
        # Catch potential parsing errors
        logging.error(f"An error occurred during HTML parsing: {e}")
        return None


if __name__ == "__main__":
    print(f"--- Starting Web Scraper for {TARGET_URL} ---")

    page_title = fetch_and_parse_title(TARGET_URL)

    if page_title is not None:
        print("\n[RESULT]")
        print(f"URL: {TARGET_URL}")
        print(f"Title: {page_title}")
    else:
        print("\n[RESULT]")
        print(f"Failed to retrieve or parse the title from {TARGET_URL}. Check logs for details.")

    print("--- Script Finished ---")