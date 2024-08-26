import asyncio
import aiohttp
import requests
import time
import csv
import logging
import argparse
import os
from info_formatter import parse_book_data
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from dotenv import load_dotenv

load_dotenv()

class AmazonBookScraper():
    def __init__(self, scraper_api_key):

        self.scraper_api_key = scraper_api_key
        self.scraper_amazon_url = "https://api.scraperapi.com/structured/amazon/product"
        self.base_url = "https://api.scraperapi.com"
        self.url_to_scrape = "https://www.amazon.fr/s?i=stripbooks&bbn=301061&rh=n%3a301139%2cp_n_publication_date%3a183196031%2cp_n_feature_browse-bin%3a5272956031%2cp_n_binding_browse-bin%3a3973586031%7c492480011%7c492481011&s=date-desc-rank&dc"
        self.number_of_pages = 20
        self.csv_file = "amazon_scraped_books.csv" 

    def extract_book_info(self, html: str) -> list[dict[str, str]]:
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


    async def get_detailed_book_info(self, session: aiohttp.ClientSession, asin: str, title: str) -> dict[str, Any]:
        headers = {
            "Content-Type": "application/json"
        }
        params = {
            "api_key": self.scraper_api_key,
            "tld": "fr",
            "asin": asin,
        }

        async with session.get(self.scraper_amazon_url, params=params, headers=headers) as response:
            logging.info(f"Getting detailed info: {title}:{asin}...")
            return await response.json()


    async def process_book(self, session: aiohttp.ClientSession, book: dict[str, str]) -> dict[str, str]:
        details = await self.get_detailed_book_info(session, book["asin"], book["title"])
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


    def scrape_amazon_page(self, page_number):
        params = {
            'api_key': self.scraper_api_key,
            "tld": "fr",
            'url': f'{self.url_to_scrape}&page={page_number}'
        }
        response = requests.get(self.base_url, params=params)
        logging.info(f"Processing page: {page_number}")
        books = self.extract_book_info(response.text)
        return books


    async def run_scraper(self):
        logging.info(f"Scraping {self.number_of_pages} pages to {self.csv_file}...")
        init_time = time.time()


        page_numbers = [i for i in range(1, self.number_of_pages + 1)]
        all_books = []

        def consumer_function(books):
            return list(books)

        with ThreadPoolExecutor(max_workers=10) as exc:
            generators = list(exc.map(self.scrape_amazon_page, page_numbers))
            books = list(exc.map(consumer_function, generators))

            for chunk in books:
                all_books.extend(chunk)

        logging.info(f"Scraped {self.number_of_pages} pages and found {len(all_books)} books {time.time() - init_time:.2f} seconds")

        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            results = await asyncio.gather(*[self.process_book(session, book) for book in all_books])

        logging.info(f"Fetched additional info for {len(all_books)}: {time.time() - start_time:.2f} seconds")

        all_fields = set()
        for result in results:
            all_fields.update(result.keys())

        ordered_fields = ["ASIN", "Title", "Author", "Brand", "Release Date"]
        fieldnames = [field for field in ordered_fields if field in all_fields]
        fieldnames.extend(sorted(all_fields - set(ordered_fields)))

        with open(self.csv_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        logging.info(f"Total completion time: {time.time() - init_time:.2f} seconds")
        logging.info(f"Results saved in {self.csv_file}")

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("amazon_scraping.log"),
            logging.StreamHandler(),
        ]
    )

    scraper_api_key = os.environ.get("SCRAPER_API_KEY")
    if scraper_api_key:
        scraper = AmazonBookScraper(scraper_api_key)
        asyncio.run(scraper.run_scraper())
    else:
        logging.info("SCRAPER_API_KEY not configured in .env file. cp .env.example .env and change ACTUAL_API_KEY with the correct value")
