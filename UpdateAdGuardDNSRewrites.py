#!/usr/bin/env python3

import os
import sys
import requests
import logging
import queue
import threading
import json
from typing import Any, Dict, List, Optional, Callable
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urljoin
from functools import wraps

JSON_URL = "https://raw.githubusercontent.com/uklans/cache-domains/master/cache_domains.json"
LOG_FORMAT = '%(asctime)s\t%(levelname)s\t%(message)s'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '3'))
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))
CACHE_FILE = os.getenv('CACHE_FILE', None)

def setup_logging():
    log_level = getattr(logging, LOG_LEVEL, logging.INFO)
    logging.basicConfig(level=log_level, format=LOG_FORMAT)

def get_env_variable(name: str, default: Optional[Any] = None, mandatory: bool = True, cast: Callable = str) -> Any:
    """Fetches and casts an environment variable.

    Parameters:
    name (str): Name of the environment variable.
    default (Optional[Any]): Default value if the environment variable is not found. Defaults to None.
    mandatory (bool): If True, raises an error when the variable is missing. Defaults to True.
    cast (Callable): A function to cast the variable value to the desired type. Defaults to str.

    Returns:
    Any: The value of the environment variable, possibly cast to another type.

    Raises:
    RuntimeError: If the variable is mandatory but not found, or if casting fails.
    """
    value = os.environ.get(name, default)
    if mandatory and value is None:
        raise RuntimeError(f"Environment variable {name} is not set.")
    try:
        return cast(value)
    except ValueError as e:
        raise RuntimeError(f"Error casting environment variable {name}: {e}")

def exception_handler(func):
    """A decorator for wrapping functions in a try-except block to handle exceptions cleanly.

    Parameters:
    func (Callable): The function to wrap.

    Returns:
    Callable: The wrapped function.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.RequestException as e:
            logging.error(f"Request error in {func.__name__}: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error in {func.__name__}: {e}")
            return None
    return wrapper

@exception_handler
def create_session(username: str, password: str) -> requests.Session:
    """Creates a requests session with HTTP Basic Authentication and retry strategy.

    Parameters:
    username (str): The username for authentication.
    password (str): The password for authentication.

    Returns:
    requests.Session: A session configured with HTTP Basic Authentication and retries.
    """
    session = requests.Session()
    session.auth = HTTPBasicAuth(username, password)
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PUT"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    logging.info("HTTP session to AdGuard Home created with basic authentication.")
    return session

def validate_json_structure(data: Dict, required_keys: List[str]) -> bool:
    """Validates if the specified keys exist in a JSON dictionary.

    Parameters:
    data (Dict): The JSON dictionary to validate.
    required_keys (List[str]): A list of keys expected to be in the dictionary.

    Returns:
    bool: True if all keys exist, False otherwise.
    """
    return all(key in data for key in required_keys)

@exception_handler
def download_file(session: requests.Session, file_url: str) -> List[str]:
    """Downloads a file and returns its contents as a list of strings.

    Parameters:
    session (requests.Session): The session to use for the request.
    file_url (str): The URL of the file to download.

    Returns:
    List[str]: The contents of the file, split into lines, or an empty list on error.
    """
    logging.debug("Starting download from URL: %s", file_url)
    response = session.get(file_url, timeout=10)
    response.raise_for_status()
    logging.debug("Download complete for URL: %s", file_url)
    return response.text.strip().split('\n')

def download_files_concurrently(session: requests.Session, file_paths: List[str], base_url: str,
                                lancache_server: str) -> List[Dict[str, str]]:
    """Downloads files with a worker pool to limit concurrent connections.

    Parameters:
    session (requests.Session): The session to use for the requests.
    file_paths (List[str]): A list of file paths to download.
    base_url (str): The base URL for constructing the full URL to download the files.
    lancache_server (str): The IP address or hostname of the lancache server for DNS rewrites.

    Returns:
    List[Dict[str, str]]: A list of dictionaries containing the domain as a key and the lancache server as its value.
    """
    logging.info("Starting file downloads. Number of files: %d with %d worker(s)", len(file_paths), MAX_WORKERS)
    def download_and_process(file_path: str) -> List[Dict[str, str]]:
        full_url = urljoin(base_url, file_path)
        domains = download_file(session, full_url)
        if domains is None:
            return []
        return [{"domain": domain, "answer": lancache_server} for domain in domains if
                domain and not domain.startswith('#')]
    results = []
    lock = threading.Lock()
    work_queue = queue.Queue()
    for file_path in file_paths:
        work_queue.put(file_path)
    def worker():
        while True:
            try:
                file_path = work_queue.get_nowait()
            except queue.Empty:
                break
            processed_data = download_and_process(file_path)
            with lock:
                results.extend(processed_data)
            work_queue.task_done()
    threads = [threading.Thread(target=worker) for _ in range(MAX_WORKERS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    logging.info("File downloads complete. Processed entries count: %d", len(results))
    return results

def get_specific_services_names(env_var_value: str) -> List[str]:
    """Parses a comma-separated string from an environment variable into a list of service names.

    Parameters:
    env_var_value (str): The raw string value of the environment variable containing service names.

    Returns:
    List[str]: A list of service names, stripped of whitespace.
    """
    return [name.strip() for name in env_var_value.split(',')] if env_var_value.strip() else []

@exception_handler
def get_available_services_names(session: requests.Session, json_url: str) -> List[str]:
    """Fetches and parses a list of available service names from a remote JSON file.

    Parameters:
    session (requests.Session): The session to use for the HTTP request.
    json_url (str): The URL of the JSON file containing the list of services.

    Returns:
    List[str]: A list of service names if the request is successful; an empty list otherwise.
    """
    response = session.get(json_url, timeout=10)
    response.raise_for_status()
    data = response.json()
    if validate_json_structure(data, ['cache_domains']):
        return [item['name'] for item in data['cache_domains']]
    return []

@exception_handler
def get_file_list_from_json(session: requests.Session, json_url: str, specific_service_names: List[str]) -> List[str]:
    """Fetches a list of file paths from a JSON file, filtering by specific service names if provided.

    Parameters:
    session (requests.Session): The session to use for the HTTP request.
    json_url (str): The URL of the JSON file containing the list of file paths.
    specific_service_names (List[str]): A list of service names to filter the file paths by.

    Returns:
    List[str]: A list of file paths based on the filtering criteria.
    """
    logging.info("Getting file list to download from %s", json_url)
    response = session.get(json_url, timeout=10)
    response.raise_for_status()
    data = response.json()
    file_paths = []
    if validate_json_structure(data, ['cache_domains']):
        for item in data['cache_domains']:
            if item['name'] in specific_service_names:
                file_paths.extend(item['domain_files'])
    return file_paths

@exception_handler
def fetch_current_rewrites(session: requests.Session, rewrite_endpoint: str) -> Dict[str, str]:
    """Fetches the current DNS rewrites from the server.

    Parameters:
    session (requests.Session): The session to use for the HTTP requests.
    rewrite_endpoint (str): The endpoint URL for fetching current DNS rewrites.

    Returns:
    Dict[str, str]: A dictionary of current DNS rewrites with domain as key and IP as value.
    """
    logging.info("Fetching current rewrites from %s", f"{rewrite_endpoint}/list")
    response = session.get(f"{rewrite_endpoint}/list", timeout=10)
    response.raise_for_status()
    rewrites = response.json()
    return {rewrite['domain']: rewrite['answer'] for rewrite in rewrites}

def batch_update_rewrites(session: requests.Session, rewrite_endpoint: str, dns_rewrites: List[Dict[str, str]],
                          current_rewrites: Dict[str, str], batch_size: int = BATCH_SIZE):
    """Updates DNS rewrites in batches to avoid overwhelming the server.

    Parameters:
    session (requests.Session): The session to use for HTTP requests.
    rewrite_endpoint (str): The endpoint URL for DNS rewrites.
    dns_rewrites (List[Dict[str, str]]): The list of DNS rewrite rules to update.
    current_rewrites (Dict[str, str]): A dictionary of current DNS rewrites for comparison.
    batch_size (int): Number of rewrites to update before logging progress.
    """
    added_count = 0
    updated_count = 0
    skipped_count = 0
    for i, rewrite in enumerate(dns_rewrites):
        domain = rewrite['domain']
        answer = rewrite['answer']
        if domain in current_rewrites:
            if current_rewrites[domain] != answer:
                logging.debug(f"Updating DNS rewrite for {domain} from {current_rewrites[domain]} to {answer}.")
                try:
                    session.put(f"{rewrite_endpoint}/update", json={"domain": domain, "answer": answer}, timeout=10)
                    updated_count += 1
                except Exception as e:
                    logging.error(f"Failed to update {domain}: {e}")
            else:
                skipped_count += 1
        else:
            logging.debug(f"Adding new DNS rewrite for {domain} to {answer}.")
            try:
                session.post(f"{rewrite_endpoint}/add", json={"domain": domain, "answer": answer}, timeout=10)
                added_count += 1
            except Exception as e:
                logging.error(f"Failed to add {domain}: {e}")
        if (i + 1) % batch_size == 0:
            logging.info(f"Progress: {i + 1}/{len(dns_rewrites)} processed. Added: {added_count}, Updated: {updated_count}, Skipped: {skipped_count}")
    logging.info(f"DNS rewrite updates complete. Added: {added_count}, Updated: {updated_count}, Skipped: {skipped_count}")

@exception_handler
def update_dns_rewrites(session: requests.Session, rewrite_endpoint: str, dns_rewrites: List[Dict[str, str]]):
    """Manages DNS rewrites by ensuring each is only added once and updates are handled correctly.

    Parameters:
    session (requests.Session): The session to use for the HTTP requests.
    rewrite_endpoint (str): The endpoint URL for managing DNS rewrites.
    dns_rewrites (List[Dict[str, str]]): The desired list of DNS rewrite rules.
    """
    current_rewrites = fetch_current_rewrites(session, rewrite_endpoint)
    logging.info("Updating DNS rewrites.")
    batch_update_rewrites(session, rewrite_endpoint, dns_rewrites, current_rewrites)

def load_cache(cache_file: str) -> Optional[Dict[str, List[Dict[str, str]]]]:
    """Loads cached DNS rewrites from file if it exists.

    Parameters:
    cache_file (str): Path to the cache file.

    Returns:
    Optional[Dict]: Cached data if file exists and is valid, None otherwise.
    """
    if not cache_file or not os.path.exists(cache_file):
        return None
    try:
        with open(cache_file, 'r') as f:
            logging.info("Loading DNS rewrites from cache: %s", cache_file)
            return json.load(f)
    except Exception as e:
        logging.warning(f"Failed to load cache: {e}")
        return None

def save_cache(cache_file: str, dns_rewrites: List[Dict[str, str]]):
    """Saves DNS rewrites to cache file.

    Parameters:
    cache_file (str): Path to the cache file.
    dns_rewrites (List[Dict[str, str]]): The DNS rewrites to cache.
    """
    if not cache_file:
        return
    try:
        with open(cache_file, 'w') as f:
            json.dump(dns_rewrites, f)
            logging.info("DNS rewrites cached to: %s", cache_file)
    except Exception as e:
        logging.error(f"Failed to save cache: {e}")

def main():
    """Main function orchestrating the script's operations."""
    setup_logging()
    logging.info("Script execution started.")
    logging.info("Retrieving environment variables.")
    try:
        fetch_all_services = get_env_variable('ALL_SERVICES', 'false', mandatory=False).lower() == 'true'
        specific_services_names_raw = get_env_variable('SERVICE_NAMES', '', mandatory=False)
        specific_services_names = get_specific_services_names(specific_services_names_raw)
        try:
            username = get_env_variable('ADGUARD_USERNAME')
        except RuntimeError:
            logging.error("ADGUARD_USERNAME environment variable is not set. Please ensure it is correctly set. "
                          "Example: export ADGUARD_USERNAME='your_username'")
            raise
        try:
            password = get_env_variable('ADGUARD_PASSWORD')
        except RuntimeError:
            logging.error("ADGUARD_PASSWORD environment variable is not set. Please ensure it is correctly set. "
                          "Example: export ADGUARD_PASSWORD='your_password'")
            raise
        try:
            lancache_server = get_env_variable('LANCACHE_SERVER')
        except RuntimeError:
            logging.error("LANCACHE_SERVER environment variable is not set. Please ensure it is correctly set with "
                          "the IP address or hostname of your lancache server. Example: export "
                          "LANCACHE_SERVER='192.168.0.100'")
            raise
        try:
            adguard_api = get_env_variable('ADGUARD_API')
        except RuntimeError:
            logging.error("ADGUARD_API environment variable is not set up properly. Please ensure it is set with the "
                          "full API endpoint, including the protocol and port if necessary. For example: "
                          "ADGUARD_API='http://adguard.example.com:3000'")
            raise
    except RuntimeError as e:
        logging.error(f"Critical configuration error: {e}")
        return 1
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        return 1
    session = create_session(username, password)
    if fetch_all_services:
        logging.info("Fetching all available services...")
        specific_services_names = get_available_services_names(session, json_url=JSON_URL)
        if not specific_services_names:
            logging.error("Failed to fetch available service names.")
            return 1
        logging.info(f"Will process {len(specific_services_names)} services: {', '.join(specific_services_names)}")
    elif not specific_services_names:
        logging.error("Neither ALL_SERVICES is set to true nor SERVICE_NAMES is specified. Fetching available service "
                      "names...")
        available_service_names = get_available_services_names(session, json_url=JSON_URL)
        if available_service_names:
            logging.info("Available service names: " + ", ".join(available_service_names))
            logging.info("Specify one or more service names in SERVICE_NAMES or set ALL_SERVICES to true to proceed.")
            return 1
        else:
            logging.error("Failed to fetch available service names.")
            return 1
    file_paths = get_file_list_from_json(session, JSON_URL, specific_services_names)
    if not file_paths:
        logging.warning("No file paths found for the specified services.")
        return 1
    dns_rewrites = download_files_concurrently(session, file_paths, JSON_URL, lancache_server)
    if not dns_rewrites:
        logging.warning("No DNS rewrites downloaded.")
        return 1
    save_cache(CACHE_FILE, dns_rewrites)
    rewrite_endpoint = f"{adguard_api}/control/rewrite"
    update_dns_rewrites(session, rewrite_endpoint, dns_rewrites)
    logging.info("Script execution finished successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())