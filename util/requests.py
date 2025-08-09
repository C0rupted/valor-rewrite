import requests, logging, aiohttp, asyncio, os, time

from io import BytesIO
from requests.exceptions import RequestException


# Default headers for HTTP requests
DEFAULT_HEADERS = {
    'User-Agent': 'ano_valor/0.0.0'
}

# Base URL for fetching player bust images by UUID or name
BUST_API_URL = "https://visage.surgeplay.com/bust/"



async def request(url: str, headers: dict = None, return_type: str = "json"):
    """
    Perform a synchronous HTTP GET request wrapped in an async function.

    Args:
        url (str): The URL to request.
        headers (dict, optional): Additional HTTP headers to send.
        return_type (str): Expected response type; "json", "image", or "stream".

    Returns:
        The response content according to return_type, or None on failure.
    """
    # Merge default headers with user-provided headers
    all_headers = {**DEFAULT_HEADERS, **(headers or {})}

    try:
        # Synchronous GET request using requests library
        res = requests.get(url, headers=all_headers)
        res.raise_for_status()  # Raise on HTTP error codes

        # Return data according to requested return_type
        if return_type == "json":
            try:
                return res.json()
            except ValueError:
                logging.warning(f"Failed to parse JSON from {url}")
        elif return_type == "image":
            return res.content  # Return raw bytes
        elif return_type == "stream":
            return BytesIO(res.content)  # Return BytesIO stream
        else:
            logging.warning(f"Unsupported return_type: {return_type}")

    except RequestException as e:
        logging.warning(f"Request error while accessing {url}: {e}")
    except Exception as e:
        logging.warning(f"Unexpected error while accessing {url}: {e}")

    # Return None if any error occurs
    return None



async def request_with_csrf(csrf_url: str, url: str, return_type: str = "json"):
    """
    Perform a synchronous HTTP GET request that requires obtaining a CSRF token first.

    Args:
        csrf_url (str): URL to fetch and extract the CSRF token from cookies.
        url (str): The target URL to request with the CSRF token.
        return_type (str): Expected response type; "json", "image", or "stream".

    Returns:
        The response content according to return_type, or None on failure.
    """
    session = requests.Session()

    try:
        # Request to get CSRF token (typically from cookies)
        csrf_res = session.get(csrf_url, headers=DEFAULT_HEADERS)
        csrf_res.raise_for_status()

        csrf_token = session.cookies.get("csrf_token")
        if not csrf_token:
            logging.warning(f"CSRF token not found in cookies from {url}")

        # Use the obtained token to fetch the actual content
        headers = {
            **DEFAULT_HEADERS,
            "X-CSRF-Token": csrf_token,
            "Content-Type": "application/json"
        }

        res = session.get(url, headers=headers)
        res.raise_for_status()

        # Return data according to requested return_type
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
    except Exception as e:
        logging.warning(f"Unexpected error: {e}")

    return None



async def download_player_bust(session: aiohttp.ClientSession, name: str, filename: str, retry: bool = True):
    """
    Download a player's bust image by name, saving to the specified filename.

    Args:
        session (aiohttp.ClientSession): The async HTTP session to use.
        name (str): Player's in-game name.
        filename (str): Local file path to save the image.
        retry (bool): Whether to retry once if the first attempt fails.

    Returns:
        True if download succeeded, False if not found, None on failure.
    """
    from util.uuid import get_uuid_from_name

    try:
        # Attempt to resolve player UUID from name
        uuid = await get_uuid_from_name(name)
    except Exception as e:
        logging.error(f"Failed to resolve UUID for {name}: {e}")
        return None

    try:
        # Build bust URL using UUID if available, else fallback to name
        url = f"{BUST_API_URL}{uuid if uuid else name}.png"

        # Async GET request for the bust image
        async with session.get(url, headers=DEFAULT_HEADERS, timeout=2) as response:
            if response.status == 200:
                # Write image content to file
                content = await response.read()
                with open(filename, "wb") as f:
                    f.write(content)
                return True
            elif response.status == 404:
                # Bust image not found
                return False
            else:
                # Retry once on other HTTP errors
                if retry:
                    return await download_player_bust(session, name, filename, retry=False)
                else:
                    logging.warning(f"Failed to fetch {name} ({uuid}): HTTP {response.status}")
    except Exception as e:
        logging.error(f"Error fetching {name} ({uuid}): {e}")

    return None



async def fetch_player_busts(names: list[str]):
    """
    Download bust images for a list of player names concurrently.

    Skips downloading if a valid cached image exists in /tmp that is less than 24 hours old.

    Args:
        names (list[str]): List of player names to fetch bust images for.

    Returns:
        None
    """
    tasks = []
    now = time.time()

    async with aiohttp.ClientSession() as session:
        for name in names:
            filename = f"/tmp/{name}_model.png"

            # Skip if cached file exists and is recent (less than 24 hours old)
            if os.path.exists(filename) and now - os.path.getmtime(filename) < 24 * 3600:
                continue

            # Schedule bust download task
            tasks.append(download_player_bust(session, name, filename))

        # Run all download tasks concurrently
        await asyncio.gather(*tasks)
