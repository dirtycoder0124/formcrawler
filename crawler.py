import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
import time

visited_urls = set()
max_depth = 3  # Maximum recursion depth
concurrent_requests = 5  # Number of concurrent requests
crawl_delay = 1  # Delay between requests to avoid overloading the server
robot_disallowed = set()  # Set to store URLs disallowed by robots.txt

def is_valid_url(url):
    parsed_url = urlparse(url)
    return bool(parsed_url.scheme) and bool(parsed_url.netloc)

def get_robots_txt(url):
    try:
        response = requests.get(urljoin(url, "/robots.txt"))
        if response.status_code == 200:
            return response.text.splitlines()
        else:
            print("Failed to retrieve robots.txt:", url)
            return []
    except Exception as e:
        print("Error occurred while fetching robots.txt:", e)
        return []

def parse_robots_txt(robots_content):
    disallowed = set()
    for line in robots_content:
        if line.startswith("Disallow:"):
            disallowed_url = line.split(" ")[1].strip()
            disallowed.add(disallowed_url)
    return disallowed

def can_crawl(url):
    parsed_url = urlparse(url)
    if parsed_url.netloc in robot_disallowed:
        return False
    return True

def crawl_worker(url, depth):
    try:
        response = requests.get(url, allow_redirects=True, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        forms = soup.find_all('form')
        if forms and url not in visited_urls:
            print("\033[92mForm Found\033[0m:", url)  # Green color for "Form Found" message
            visited_urls.add(url)
        for link in soup.find_all('a', href=True):
            next_url = urljoin(url, link['href'])
            if is_valid_url(next_url) and can_crawl(next_url) and next_url not in visited_urls:
                crawl_queue.put((next_url, depth + 1))
    except Exception as e:
        pass

def crawl_worker_wrapper(args):
    crawl_worker(*args)
    time.sleep(crawl_delay)

def crawl_for_forms(starting_url):
    crawl_queue.put((starting_url, 0))
    while not crawl_queue.empty():
        url, depth = crawl_queue.get()
        if depth <= max_depth:
            with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
                executor.map(crawl_worker_wrapper, [(url, depth) for _ in range(concurrent_requests)])
        else:
            print("Maximum depth reached for URL:", url)

def main():
    domain = input("Enter the domain you want to crawl (e.g., example.com): ")
    starting_url = "http://" + domain
    robots_content = get_robots_txt(starting_url)
    global robot_disallowed
    robot_disallowed = parse_robots_txt(robots_content)
    crawl_for_forms(starting_url)

if __name__ == "__main__":
    crawl_queue = Queue()
    main()
