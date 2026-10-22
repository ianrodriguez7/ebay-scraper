# ebay-scraper

`ebay-dl.py` downloads the first 10 pages of eBay search results for a search term using `requests`, pulls every listing out of the HTML with Beautiful Soup, and saves the listings to `SEARCH_TERM.json`. For each item it records:

- `name`: the listing title
- `price`: price in cents (for a price range, the lower price)
- `status`: condition, like "Brand New" or "Pre-owned"
- `shipping`: shipping cost in cents (`0` for free shipping)
- `free_returns`: whether the listing offers free returns
- `items_sold`: how many have sold

Fields a listing doesn't show are saved as `null`.

eBay blocked live scraping when I ran it, so my three JSON files were made from the course's practice pages. The practice listings are the same for every search term, so the three files have the same listings under different names.

## How to run

Install the dependencies:

```
python -m pip install requests beautifulsoup4
```

Download and unzip the practice pages:

```
python -m zipfile -e practice-pages.zip .
```

Generate the three JSON files:

```
python ebay-dl.py --search "soccer cleats" --pages-dir practice-pages
python ebay-dl.py --search "video games" --pages-dir practice-pages
python ebay-dl.py --search "surfing" --pages-dir practice-pages
```

To scrape eBay live instead, leave off `--pages-dir`:

```
python ebay-dl.py --search "soccer cleats"
```

## CSV output (extra credit)

Add `--csv` to save `SEARCH_TERM.csv` instead of JSON:

```
python ebay-dl.py --search "soccer cleats" --pages-dir practice-pages --csv
python ebay-dl.py --search "video games" --pages-dir practice-pages --csv
python ebay-dl.py --search "surfing" --pages-dir practice-pages --csv
```

[Project page](https://csci40.rtealwitter.com/projects/02_webscraping/project.html)
