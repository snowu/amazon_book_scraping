# Scraping books from Amazon using ScraperAPI
Using ScraperAPI to scrape Amazon book pages and save content in CSV sheet  


My initial approach was fully async but after testing for a while with Async ScraperAPI functionality, sadly I found some discrepancies with the data returned by batched scraping jobs despite using *identical* links for both sync and async approach.  
Data returned was consistently wrong (some with release date in the future ) and wouldn't update based on `qid` value as the sync API and the browseable page do.    
Not sure why this happens and I tried to use `qid` and `rnid` to clear any eventual caching on the side of ScraperAPI but the results are always the same and always inconsistent with 
what's actually present in the scraped pages.  
Documentation sadly is scarce and despite spending some time testing different setups and options, I wasn't able to fully understand why this happens but I'm assuming it's something to do with how async ScraperAPI jobs are processed.

For this reason, I ended up using a mixture of sync, asyncio and threading:  
]. Threading to scrape pages concurrently with a sync API endpoint  
]. Async to process scraped books and fetch additional details  
]. Sync for everything that wouldn't actually profit from being async but it's fast enough to not require threading  

Good news is, this "mixed" approach seems to be both faster and more precise than a fully async approach using ScraperAPI async features. So win win, I suppose.  

## Run the script
Final script is `book_scraping.py`.  
To protect ScraperAPI key the script uses env variable:   
- To setup just create `.env` with the API_KEY = "ACTUAL_API_KEY" variable inside. `.env.example` can be used as a template.  

The script is usable with 3 CLI parameters:  
`-d --destination_path`  
`-p --number_of_pages`  
`-l --log_file`  

- Default `number_of_pages` is 20.  
- Results will be written to `scraped_french_books.csv` by default unless `destination_path` is passed  
- Logs are printed in `log_file` console. Default is `amazon_scraping.log`  

To use the script:  
`virtualenv -p python3 env_name`  
`source env_name/bin/activate`  
`pip install -r requirements.txt`  
`python3 book_scraping.py -p 20 -d "book_scraping.csv" -l "book_scraping.log`  

All args have defaults so `python3 book_scraping.py` is fine as well  

I tested up to 1000 pages with additional books info fetched successfully in 340s~ but it's pointless going over 75 (n° of pages on amazon) since the upper limit with the given link is 16*75 = 1200 books.

## Scoring results

Essay about scoring can be found in `scoring.txt`  


## Demo of fully async approach

There's also available the version of the approach I would have used if I didn't encounter the problem where - as mentioned above - data is incorrect when fetching async jobs.  
Full async version is available in `fully_async.py`, usage is identical to `book_scraping.py` 

`python3 fully_async.py -p 20 -d "book_scraping_async.csv" -l "book_scraping_async.log`
