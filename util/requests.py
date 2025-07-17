import requests, logging
from io import BytesIO
from requests.exceptions import RequestException


DEFAULT_HEADERS = {
    'User-Agent': 'ano_valor/0.0.0'
}


async def request(url: str, headers: dict = None, return_type: str = "json"):
    all_headers = {**DEFAULT_HEADERS, **(headers or {})}

    try:
        # Make request
        res = requests.get(url, headers=all_headers)
        res.raise_for_status()

        # Return appropriate data type
        if return_type == "json":
            try:
                return res.json()
            except ValueError:
                logging.warning(f"Failed to parse JSON from {url}")
        elif return_type == "image":
            return res.content
        elif return_type == "stream":
            return BytesIO(res.content)
        else:
            logging.warning(f"Unsupported return_type: {return_type}")

    except RequestException as e:
        logging.warning(f"Request error while accessing {url}: {e}")
        return None
    except Exception as e:
        logging.warning(f"Unexpected error while accessing {url}: {e}")
        return None



async def request_with_csrf(csrf_url: str, url: str, return_type: str = "json"):
    session = requests.Session()

    try:
        # Step 1: Get CSRF token
        csrf_res = session.get(csrf_url, headers=DEFAULT_HEADERS)
        csrf_res.raise_for_status()

        csrf_token = session.cookies.get("csrf_token")
        if not csrf_token:
            logging.warning(f"CSRF token not found in cookies from {url}")

        # Step 2: Use token to fetch actual content
        headers = {
            **DEFAULT_HEADERS,
            "X-CSRF-Token": csrf_token,
            "Content-Type": "application/json"
        }

        res = session.get(url, headers=headers)
        res.raise_for_status()

        if return_type == "json":
            try:
                return res.json()
            except ValueError:
                logging.warning(f"Failed to parse JSON from {url}")
        elif return_type == "image":
            return res.content
        elif return_type == "stream":
            return BytesIO(res.content)
        else:
            logging.warning(f"Unsupported return_type: {return_type}")

    except RequestException as e:
        logging.warning(f"Request error while accessing {url}: {e}")
        return None
    except Exception as e:
        logging.warning(f"Unexpected error: {e}")
        return None