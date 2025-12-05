# REQUIRES: requests
# REQUIRES: beautifulsoup4

import requests
import sys
from bs4 import BeautifulSoup
from requests. exceptions import RequestException, HTTPError, Timeout

TARGET_URL = "https://example.com"
TIMEOUT_SECONDS = 10

def fetch_and_parse_title(url: str) -> str | None:
    """
    Fetches the content of a URL and parses the HTML to extract the title tag.

    Args:
        url: The URL to fetch.

    Returns:
        The text content of the <title> tag, or None if fetching/parsing fails.
    """
    print(f"Attempting to fetch content from: {url}")

    try:
        # Use a context manager for the request session
        with requests.Session() as session:
            # Set a reasonable timeout
            response = session.get(url, timeout=TIMEOUT_SECONDS)

            # Raise an HTTPError for bad status codes (4xx or 5xx)
            response.raise_for_status()

            # Parse the HTML content using BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find the title tag
            title_tag = soup.find('title')

            if title_tag:
                title_text = title_tag.get_text(strip=True)
                print("Successfully parsed title.")
                return title_text
            else:
                print("Warning: <title> tag not found in the response.")
                return None

    except HTTPError as e:
        print(f"Error: HTTP request failed with status code {e.response.status_code} for {url}", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        return None
    except Timeout:
        print(f"Error: Request timed out after {TIMEOUT_SECONDS} seconds for {url}", file=sys.stderr)
        return None
    except RequestException as e:
        # Catches connection errors, DNS errors, etc.
        print(f"Error: A network error occurred while fetching {url}", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        return None
    except Exception as e:
        # Catch any unexpected parsing or runtime errors
        print(f"Error: An unexpected error occurred during processing: {e}", file=sys.stderr)
        return None

def main():
    """
    Main execution function.
    """
    title = fetch_and_parse_title(TARGET_URL)

    print("-" * 30)
    if title is not None:
        print(f"Extracted Title: '{title}'")
    else:
        print(f"Failed to extract title from {TARGET_URL}.")

if __name__ == "__main__":
    main()