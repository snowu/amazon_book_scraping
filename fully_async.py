import asyncio
import aiohttp
import requests
import csv
import logging
import argparse
import os
import time
from datetime import datetime
from info_formatter import parse_book_data
from bs4 import BeautifulSoup
from operator import itemgetter
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY")  
SCRAPER_AMAZON_URL = "https://api.scraperapi.com/structured/amazon/product"
SCRAPER_ASYNC_URL = "https://async.scraperapi.com/batchjobs"
URL_TO_SCRAPE = "https://www.amazon.fr/s?i=stripbooks&bbn=301061&rh=n%3A301139%2Cp_n_publication_date%3A183196031%2Cp_n_feature_browse-bin%3A5272956031%2Cp_n_binding_browse-bin%3A3973586031%7C492480011%7C492481011&s=date-desc-rank&dc"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='Scrape books',
        description='Scrape amazon fr pages by new releases and save books to CSV')
    parser.add_argument('-d', '--destination_path', type=str, default="scraped_french_books.csv")
    parser.add_argument('-p', '--number_of_pages', type=int, default=20)
    parser.add_argument('-l', '--log_file', type=str, default='amazon_scraping.log')
    return parser.parse_args()


def extract_book_info(html: str) -> List[Dict[str, str]]:
    def _clean_string(string: str) -> str:
        return string.strip().replace(";", "")

    soup = BeautifulSoup(html, "html.parser")
    books = []
    for item in soup.select("div[data-asin]:not([data-asin=''])"):
        asin = item["data-asin"]

        title = item.select_one("h2 a span")
        title = _clean_string(title.text) if title else "N/A"

        info = item.select_one("div.a-row.a-size-base.a-color-secondary .a-row")
        info = info.text.split("|") if info else ["N/A"]
        author = _clean_string(info[0])
        release_date = _clean_string(info[1]) if len(info) > 1 else "N/A"

        books.append({"asin": asin, "title": title, "author": author, "release_date": release_date})

    return books


async def get_detailed_book_info(session: aiohttp.ClientSession, asin: str, title: str) -> Dict[str, Any]:
    headers = {
        "Content-Type": "application/json"
    }
    params = {
        "api_key": SCRAPER_API_KEY,
        "tld": "fr",
        "asin": asin,
    }
    async with session.get(SCRAPER_AMAZON_URL, params=params, headers=headers) as response:
        logging.info(f"Getting detailed info: {title}:{asin}...")
        return await response.json()


async def process_book(session: aiohttp.ClientSession, book: Dict[str, str]) -> Dict[str, str]:
    details = await get_detailed_book_info(session, book["asin"], book["title"])
    parsed_book = {
        "ASIN": book["asin"],
        "Title": book["title"],
        "Author": book["author"],
        "Brand": details.get("brand", "N/A"),
        "Release Date": book["release_date"]
    }

    formatted_infos = parse_book_data(details.get("product_information", {}))
    parsed_book.update({k.capitalize(): v for k, v in formatted_infos.items()})

    return parsed_book


def init_scrapers(number_of_pages: int) -> List[Dict[str, Any]]:
    now = int(datetime.now().timestamp())

    params = {
        "apiKey": SCRAPER_API_KEY,
        "urls": [f"{URL_TO_SCRAPE}&qid={now}&page={page_number}" for page_number in range(1, number_of_pages + 1)],
    }

    res = requests.post(url=SCRAPER_ASYNC_URL, json=params)
    return res.json()


async def fetch_scraper_job(session: aiohttp.ClientSession, scraper_job: Dict[str, Any]) -> Dict[str, Any]:
    while True:
        url = scraper_job["statusUrl"]
        page = scraper_job["page"]
        async with session.get(url) as response:
            scraper_job = await response.json()
            scraper_job["page"] = page
            if scraper_job["status"] == "finished":
                logging.info(f"Page {scraper_job['page']} scraped")
                return scraper_job
            await asyncio.sleep(1)


async def main(csv_file: str, number_of_pages: int) -> None:
    logging.info(f"Scraping {number_of_pages} pages to {csv_file}...")
    start_time = time.time()

    scraper_jobs = init_scrapers(number_of_pages)

    async with aiohttp.ClientSession() as session:
        for i, job in enumerate(scraper_jobs):
            job["page"] = i + 1

        scraped_pages = await asyncio.gather(*[fetch_scraper_job(session, job) for job in scraper_jobs])

        all_books = []
        for page in sorted(scraped_pages, key=itemgetter("page")):
            books = extract_book_info(page["response"]["body"])
            all_books.extend(books)

        logging.info(f"Scraped {number_of_pages} pages and found {len(all_books)} books {time.time() - start_time:.2f} seconds")

        results = await asyncio.gather(*[process_book(session, book) for book in all_books])
        logging.info(f"Fetched additional info for {len(all_books)}: {time.time() - start_time:.2f} seconds")

    all_fields = set()

    for result in results:
        all_fields.update(result.keys())

    ordered_fields = ["ASIN", "Title", "Author", "Brand", "Release Date"]
    fieldnames = [field for field in ordered_fields if field in all_fields]
    fieldnames.extend(sorted(all_fields - set(ordered_fields)))

    with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    logging.info(f"Total completion time: {time.time() - start_time:.2f} seconds")
    logging.info(f"Results saved in {csv_file}")

if __name__ == "__main__":
    args = parse_arguments()
    csv_file = args.destination_path
    number_of_pages = args.number_of_pages

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(args.log_file),
            logging.StreamHandler(),
        ]
    )

    if SCRAPER_API_KEY:
        asyncio.run(main(csv_file, number_of_pages))
    else:
        logging.info("SCRAPER_API_KEY not configured in .env file. cp .env.example .env and change ACTUAL_API_KEY with the correct value")
