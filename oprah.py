from playwright.async_api import async_playwright
import asyncio
import logging
import aiohttp
from bs4 import BeautifulSoup
from fastapi import Request
from markdown_extractor import markdownify
from markdown_cleaner import MarkdownCleaner 
from dotenv import load_dotenv
load_dotenv()
from langchain.text_splitter import MarkdownTextSplitter
import time
from mdclense.parser import MarkdownParser
from aiohttp_socks import ProxyConnector
from functools import lru_cache
from os import getenv
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SEARCH_URL = getenv('SEARCH_URL')
markdown_cleaner = MarkdownCleaner()




@lru_cache(maxsize=128)
def get_parser_instance():
    """Return a cached parser instance to avoid recreation"""
    return MarkdownParser()

async def fetch_article(url, request:Request,timeout=10):
    """Robust fetch without Tor or proxy"""

    try:
        aiohttp_session = request.app.state.aiohttp_session
        async with aiohttp_session.get(url, allow_redirects=True) as response:
            logging.info(f"{url} -> status {response.status}")
            if response.status != 200:
                return f"[Fetch Failed: {response.status}] {url}"

            html = await response.text()
            # with open('wiki.html', 'w+', encoding='utf-8') as f:
            #     f.write(html)
            parsed_content = parse_html_content(html)
            # logging.info(3)
            if not parsed_content:
                return f"[Parse Failed] {url}"

            return parsed_content + f"\nSource: {url}\n"

    except asyncio.TimeoutError:
        logging.warning(f"Timeout when fetching {url}")
        return f"[Timeout] {url}"

    except aiohttp.ClientError as e:
        logging.warning(f"Client error fetching {url}: {e}")
        return f"[ClientError] {url}"

    except Exception as e:
        logging.warning(f"Unhandled error fetching {url}: {e}")
        return f"[UnhandledError] {url}"


async def fetch_with_browser(url, timeout=10):
    """Fetch article using a browser-based approach for difficult sites
    
    Args:
        url: URL to fetch
        timeout: Browser timeout in seconds
    
    Returns:
        Formatted article text with source URL or None if failed
    """
    try:
        # Use global browser instance or create a new one
        async with async_playwright() as p: 
            # Create a new page
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            await page.goto(url, wait_until="networkidle")
            
            # Wait for content to load
            await asyncio.sleep(2)
            
            # Extract HTML content
            html = await page.content()
            
            # Close this page but keep browser open
            await page.close()
        
        # Process the extracted HTML
        parsed_content = parse_html_content(html)
        if not parsed_content:
            logging.error(f"Browser method also failed to extract content from {url}")
            return None
            
        return parsed_content + f"\nSource: {url}\n"
    
    except Exception as e:
        logging.error(f"Browser scraping failed for {url}: {e}")
        # If the browser itself has an issue, clean it up for next attempt
        if '_browser' in globals() and _browser is not None:
            await _browser.close()
            _browser = None
        return None


def parse_html_content(html):
    """Parse HTML content into clean markdown text"""
    try:
        logging.debug("Parsing HTML with BeautifulSoup...")
        soup = BeautifulSoup(html, 'html.parser')

        logging.debug("Extracting relevant tags...")
        only_hp = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'a'])
        logging.debug(f"Found {len(only_hp)} elements to convert.")

        logging.debug("Converting HTML to markdown...")
        markdown = markdownify(html=str(only_hp))

        logging.debug("Cleaning markdown content...")
        cleaned_markdown = markdown_cleaner.clean(markdown)

        logging.debug("Splitting markdown into chunks...")
        splitter = MarkdownTextSplitter()
        split_text = splitter.split_text(cleaned_markdown)
        logging.debug(f"Split into {len(split_text)} chunks.")

        logging.debug("Parsing markdown chunks...")
        parser = get_parser_instance()
        mtext = ''
        for i, text in enumerate(split_text):
            logging.debug(f"Chunk {i+1}: {len(text)} characters")
            mtext += f"{text}\n"

        logging.debug("Running parser.parse()...")
        mrtext = parser.parse(mtext)

        # logging.debug("Writing parsed text to res.txt...")
        # with open('res.txt', '+a', encoding='utf-8') as f:
        #     f.write(mrtext)

        logging.debug("parse_html_content succeeded.")
        return mrtext

    except Exception as e:
        logging.exception("Failed to parse HTML content.")
        return None

    

async def get_news_urls(query):
    """Get URLs from search API based on query asynchronously
    
    Args:
        query: Search query string
        
    Returns:
        List of URLs from search results
    """
    f1 = time.time()
    headers = {
        "User-Agent": "Mozilla/5.0",
        "x-api-key": "easykey"
    }
    modified_query = query.replace(" ", "+")
    if "latest" in query.lower() or "current" in query.lower():
        modified_query = modified_query + "&time_range=day"
        logging.info(f"Query modified to: {modified_query}")
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{SEARCH_URL}?q={modified_query}&format=json", 
            headers=headers, 
            timeout=10
        ) as response:
            if response.status != 200:
                logging.warning(f"Search API returned status {response.status}")
                return []
            logging.info(f"Url: {SEARCH_URL}?q={modified_query}&format=json")
            data = await response.json()
            # json.dump(data, open('log.json', 'w+', encoding='utf-8'), indent=4)
    
    # Save search results for debugging
    # json.dump(data, open('log.json', 'w+', encoding='utf-8'), indent=4)
    
    # Extract URLs from results
    # logging.info(f"Search API returned {data.get('results', [])} results.")
    # sorted_results = sorted(data, key=lambda r: r.get("publishedDate", ""), reverse=True)
    sorted_results = data
    skip_set = {
        "https://uplegisassembly.gov.in/index_en.html"
    }

    urls = [
        result["url"]
        for result in sorted_results.get("results", [])
        if (
            result.get("url", "").startswith("https://")
            and not result["url"].lower().endswith(".pdf")
            and all(domain not in result["url"] for domain in [
                "britannica.com", "youtube.com", "youtu.be",
                "instagram.com", "facebook.com", "twitter.com", "x.com"
            ])
            and result["url"] not in skip_set
        )
    ][:6]


    # logging.info(f"Filtered URLs: {urls}")
    f2 = time.time()
    logging.info(f"Time to get urls: {f2-f1:.2f}s. Found {len(urls)} URLs.")
    return list(set(urls))


async def google_search(query, api_key, cse_id, num=5):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "key": api_key,
        "cx": cse_id,
        "num": num
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return [item['link'] for item in data.get('items', [])]
            else:
                logging.error("Google Search API Error:", response.status)
                return []



async def webscraper(query, request:Request):
    """Main function to scrape web content based on a query
    
    Args:
        query: Search query string
    """
    # GOOGLE_API_KEY = "AIzaSyCmJf2MYFJE7tm6kSgo60FVBKhuNUD1DzA"
    # CSE_ID = "27280ec5903f640c6"

    # urls = await google_search(query,api_key=GOOGLE_API_KEY, cse_id=CSE_ID)
    
    urls = await get_news_urls(query)

    if not urls:
        logging.warning("No URLs found for the given query.")
        return
    
    tasks = [fetch_article(url,request) for url in urls]
    results = await asyncio.gather(*tasks)
    
    return results
            




if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # query = "Best places to visit in India"

    # r = asyncio.run(webscraper(query))
    # with open('res.txt', 'r', encoding='utf-8') as f:
    #     text = f.read()

    urls = ['https://www.jagranjosh.com/general-knowledge/upcoming-elections-in-india-2025-to-2029-which-states-has-election-in-coming-years-1738743308-1', 'https://en.wikipedia.org/wiki/Elections_in_Uttar_Pradesh', 'https://en.wikipedia.org/wiki/2025_elections_in_India', 'https://indianexpress.com/elections/upcoming-elections-india/', 'https://results.eci.gov.in/', 'https://www.bankbazaar.com/voter-id/election-updates-in-india.html']
    for url in urls:
        result = asyncio.run(fetch_article(url))
        if result:
            print(result)
        else:
            print(f"Failed to fetch content from {url}")

    # r = asyncio.run(fetch_article("https://en.wikipedia.org/wiki/Elections_in_Uttar_Pradesh"))