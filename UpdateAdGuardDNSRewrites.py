#!/usr/bin/env python3

import os
import requests
import logging
import threading
from typing import Any, Dict, List, Optional, Callable
from requests.auth import HTTPBasicAuth
from urllib.parse import urljoin
from functools import wraps

# Constants
JSON_URL = "https://raw.githubusercontent.com/uklans/cache-domains/master/cache_domains.json"
LOG_FORMAT = '%(asctime)s\t%(levelname)s\t%(message)s'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()


def setup_logging():
    log_level = getattr(logging, LOG_LEVEL, logging.INFO)
    logging.basicConfig(level=log_level, format=LOG_FORMAT)


def get_env_variable(name: str, default: Optional[Any] = None, mandatory: bool = True, cast: Callable = str) -> Any:
    """
    Fetches and casts an environment variable.

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
    """
    A decorator for wrapping functions in a try-except block to handle exceptions cleanly.

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
        except Exception as e:
            logging.error(f"Unexpected error in {func.__name__}: {e}")

    return wrapper


@exception_handler
def create_session(username: str, password: str) -> requests.Session:
    """
    Creates a requests session with HTTP Basic Authentication.

    Parameters:
        username (str): The username for authentication.
        password (str): The password for authentication.

    Returns:
        requests.Session: A session configured with HTTP Basic Authentication.
    """
    session = requests.Session()
    session.auth = HTTPBasicAuth(username, password)
    logging.info("HTTP session to AdGuard Home created with basic authentication.")
    return session


def validate_json_structure(data: Dict, required_keys: List[str]) -> bool:
    """
    Validates if the specified keys exist in a JSON dictionary.

    Parameters:
        data (Dict): The JSON dictionary to validate.
        required_keys (List[str]): A list of keys expected to be in the dictionary.

    Returns:
        bool: True if all keys exist, False otherwise.
    """
    return all(key in data for key in required_keys)


@exception_handler
def download_file(session: requests.Session, file_url: str) -> List[str]:
    """
    Downloads a file and returns its contents as a list of strings.

    Parameters:
        session (requests.Session): The session to use for the request.
        file_url (str): The URL of the file to download.

    Returns:
        List[str]: The contents of the file, split into lines.
    """
    logging.debug("Starting download from URL: %s", file_url)
    response = session.get(file_url)
    response.raise_for_status()
    logging.debug("Download complete for URL: %s", file_url)
    return response.text.strip().split('\n')


def download_files_concurrently(session: requests.Session, file_paths: List[str], base_url: str,
                                lancache_server: str) -> List[Dict[str, str]]:
    """
    Downloads files concurrently and processes their contents based on the provided lancache server.

    Parameters:
        session (requests.Session): The session to use for the requests.
        file_paths (List[str]): A list of file paths to download.
        base_url (str): The base URL for constructing the full URL to download the files.
        lancache_server (str): The IP address or hostname of the lancache server for DNS rewrites.

    Returns: List[Dict[str, str]]: A list of dictionaries containing the domain as a key and the lancache server as
             its value.
    """

    logging.info("Starting file downloads. Number of files: %d", len(file_paths))

    def download_and_process(file_path: str) -> List[Dict[str, str]]:
        full_url = urljoin(base_url, file_path)
        domains = download_file(session, full_url)
        return [{"domain": domain, "answer": lancache_server} for domain in domains if
                domain and not domain.startswith('#')]

    results = []
    # Using a lock to manage concurrent access to the results list.
    lock = threading.Lock()

    def worker(file_path: str):
        nonlocal results
        processed_data = download_and_process(file_path)
        with lock:
            results.extend(processed_data)

    threads = [threading.Thread(target=worker, args=(path,)) for path in file_paths]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    logging.info("File downloads complete. Processed entries count: %d", len(results))

    return results


def get_specific_services_names(env_var_value: str) -> List[str]:
    """
    Parses a comma-separated string from an environment variable into a list of service names.

    Parameters:
        env_var_value (str): The raw string value of the environment variable containing service names.

    Returns:
        List[str]: A list of service names, stripped of whitespace.
    """
    return [name.strip() for name in env_var_value.split(',')] if env_var_value.strip() else []


@exception_handler
def get_available_services_names(session: requests.Session, json_url: str) -> List[str]:
    """
    Fetches and parses a list of available service names from a remote JSON file.

    Parameters:
        session (requests.Session): The session to use for the HTTP request.
        json_url (str): The URL of the JSON file containing the list of services.

    Returns:
        List[str]: A list of service names if the request is successful; an empty list otherwise.
    """
    response = session.get(json_url)
    response.raise_for_status()
    data = response.json()
    if validate_json_structure(data, ['cache_domains']):
        return [item['name'] for item in data['cache_domains']]
    return []


@exception_handler
def get_file_list_from_json(session: requests.Session, json_url: str, specific_service_names: List[str]) -> List[str]:
    """
    Fetches a list of file paths from a JSON file, filtering by specific service names if provided.

    Parameters:
        session (requests.Session): The session to use for the HTTP request.
        json_url (str): The URL of the JSON file containing the list of file paths.
        specific_service_names (List[str]): A list of service names to filter the file paths by.

    Returns:
        List[str]: A list of file paths based on the filtering criteria.
    """
    logging.info("Getting file list to download from %s", json_url)
    response = session.get(json_url)
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
    """
    Fetches the current DNS rewrites from the server.

    Parameters:
        session (requests.Session): The session to use for the HTTP requests.
        rewrite_endpoint (str): The endpoint URL for fetching current DNS rewrites.

    Returns:
        Dict[str, str]: A dictionary of current DNS rewrites with domain as key and IP as value.
    """
    logging.info("Fetching current rewrites from %s", f"{rewrite_endpoint}/list")
    response = session.get(f"{rewrite_endpoint}/list")
    response.raise_for_status()
    rewrites = response.json()
    return {rewrite['domain']: rewrite['answer'] for rewrite in rewrites}


@exception_handler
def update_dns_rewrite(session: requests.Session, rewrite_endpoint: str, domain: str, answer: str,
                       current_rewrites: Dict[str, str]):
    """
    Updates a single DNS rewrite by adding, deleting, or updating as necessary.

    Parameters:
        session (requests.Session): The session to use for HTTP requests.
        rewrite_endpoint (str): The endpoint URL for DNS rewrites.
        domain (str): The domain of the DNS rewrite.
        answer (str): The IP address or hostname for the DNS rewrite.
        current_rewrites (Dict[str, str]): A dictionary of current DNS rewrites for comparison.
    """
    if domain in current_rewrites:
        if current_rewrites[domain] != answer:
            # If the rewrite exists but is incorrect, delete and re-add it.
            logging.debug(f"Updating DNS rewrite for {domain} to {answer}.")
            session.delete(f"{rewrite_endpoint}/delete", json={"domain": domain})  # Assuming API supports this call
            session.post(f"{rewrite_endpoint}/add", json={"domain": domain, "answer": answer})
        else:
            logging.debug(f"DNS rewrite for {domain} already exists with correct answer. No action needed.")
    else:
        # If the rewrite does not exist, add it.
        logging.debug(f"Adding new DNS rewrite for {domain} to {answer}.")
        session.post(f"{rewrite_endpoint}/add", json={"domain": domain, "answer": answer})


@exception_handler
def update_dns_rewrites(session: requests.Session, rewrite_endpoint: str, dns_rewrites: List[Dict[str, str]]):
    """
    Manages DNS rewrites by ensuring each is only added once and updates are handled correctly.

    Parameters:
        session (requests.Session): The session to use for the HTTP requests.
        rewrite_endpoint (str): The endpoint URL for managing DNS rewrites.
        dns_rewrites (List[Dict[str, str]]): The desired list of DNS rewrite rules.
    """
    current_rewrites = fetch_current_rewrites(session, rewrite_endpoint)
    logging.info("Updating DNS rewrites.")
    for rewrite in dns_rewrites:
        update_dns_rewrite(session, rewrite_endpoint, rewrite['domain'], rewrite['answer'], current_rewrites)


def main():
    """
    Main function orchestrating the script's operations.
    """
    setup_logging()
    logging.info("Script execution started.")

    # Configuration validation and setup
    logging.info("Retrieving environment variables.")

    try:
        # Fetch and validate configuration from environment variables
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
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")

    if not fetch_all_services and not specific_services_names:
        logging.error("Neither ALL_SERVICES is set to true nor SERVICE_NAMES is specified. Fetching available service "
                      "names...")
        available_service_names = get_available_services_names(requests.session(), json_url=JSON_URL)
        if available_service_names:
            logging.info("Available service names: " + ", ".join(available_service_names))
            logging.info(
                "Specify one or more service names in SERVICE_NAMES or set FETCH_ALL_SERVICES to true to proceed.")
            return
        else:
            logging.error("Failed to fetch available service names.")
            raise RuntimeError("Failed to fetch available service names.")

    # Create HTTP session with basic authentication
    session = create_session(username, password)

    # Fetch and process file paths from JSON
    file_paths = get_file_list_from_json(session, JSON_URL, specific_services_names)
    dns_rewrites = download_files_concurrently(session, file_paths, JSON_URL, lancache_server)

    # Update DNS rewrites
    rewrite_endpoint = f"{adguard_api}/control/rewrite"
    update_dns_rewrites(session, rewrite_endpoint, dns_rewrites)

    logging.info("Script execution finished.")


if __name__ == "__main__":
    main()
