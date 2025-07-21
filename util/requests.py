import requests, logging, aiohttp, asyncio, os, time

from io import BytesIO
from requests.exceptions import RequestException


DEFAULT_HEADERS = {
    'User-Agent': 'ano_valor/0.0.0'
}

BUST_API_URL = "https://visage.surgeplay.com/bust/"


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


async def download_player_bust(session: aiohttp.ClientSession, name: str, filename: str):
    from util.uuid import get_uuid_from_name

    try:
        uuid = await get_uuid_from_name(name)
    except Exception as e:
        return logging.error(f"Failed to resolve UUID for {name}: {e}")

    try:
        async with session.get(f"{BUST_API_URL}{uuid if uuid else name}.png", headers=DEFAULT_HEADERS, timeout=2) as response:
            if response.status == 200:
                content = await response.read()
                with open(filename, "wb") as f:
                    f.write(content)
                return True
            elif response.status == 404:
                return False
            else:
                logging.warning(f"Failed to fetch {name} of {uuid}: {response.status}")
    except Exception as e:
        logging.error(f"Error fetching {name} of {uuid}: {e}")
    return None


async def fetch_player_busts(names: list[str]):

    tasks = []
    now = time.time()

    async with aiohttp.ClientSession() as session:
        for name in names:
            filename = f"/tmp/{name}_model.png"

            if os.path.exists(filename) and now - os.path.getmtime(filename) < 24 * 3600:
                continue

            tasks.append(download_player_bust(session, name, filename))

        await asyncio.gather(*tasks)
