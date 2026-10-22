#!/usr/bin/env python3
'''
Download the first 10 pages of eBay search results for a search term,
extract every listing, and save the listings as SEARCH_TERM.json
(or SEARCH_TERM.csv with --csv).

Examples:
    python ebay-dl.py --search "drill press"
    python ebay-dl.py --search "garden tools" --pages-dir practice-pages
    python ebay-dl.py --search "garden tools" --pages-dir practice-pages --csv
'''
import argparse
import csv
import json
import os
import re
import time

import requests
from bs4 import BeautifulSoup

URL = 'https://www.ebay.com/sch/i.html'
HEADERS = {'User-Agent': 'Mozilla/5.0'}
NUM_PAGES = 10
FIELDS = ['name', 'price', 'status', 'shipping', 'free_returns', 'items_sold']

CARD_SELECTOR = 'li.s-item, li.s-card, div.s-item, div.s-card'
NAME_SELECTORS = ['.s-item__title', '.s-card__title']
PRICE_SELECTORS = ['.s-item__price', '.s-card__price']
STATUS_SELECTORS = ['.SECONDARY_INFO', '.s-item__subtitle', '.s-card__subtitle']
SHIPPING_SELECTORS = ['.s-item__shipping', '.s-item__logisticsCost',
                      '.s-item__freeXDays']
CONDITIONS = ['brand new', 'new (other)', 'new', 'open box', 'refurbished',
              'certified', 'excellent', 'very good', 'good', 'acceptable',
              'pre-owned', 'used', 'parts only', 'for parts']
ROBOT_HINTS = ['pardon our interruption', 'captcha', 'verify you are a human',
               'are you a robot']


def to_cents(text):
    '''
    Return the first dollar amount in `text` as integer cents, or None.

    >>> to_cents('$1,234.50 to $2,000.00')
    123450
    >>> to_cents('+$4.25 shipping')
    425
    >>> to_cents('no price') is None
    True
    '''
    if not text:
        return None
    match = re.search(r'\$\s*([\d,]+(?:\.\d+)?)', text)
    if not match:
        return None
    dollars = match.group(1).replace(',', '')
    return int(round(float(dollars) * 100))


def first_text(card, selectors):
    '''Return the stripped text of the first matching selector, or None.'''
    for selector in selectors:
        tag = card.select_one(selector)
        if tag is not None:
            text = tag.get_text(' ', strip=True)
            if text:
                return text
    return None


def short_texts(card):
    '''Every short piece of text inside the card, used as a fallback search.'''
    texts = []
    for tag in card.find_all(True):
        text = tag.get_text(' ', strip=True)
        if text and len(text) <= 80:
            texts.append(text)
    return texts


def parse_name(card):
    title = card.select_one(', '.join(NAME_SELECTORS))
    if title is None:
        return None
    # eBay puts screen-reader labels inside the title; drop them.
    for extra in title.select('.LIGHT_HIGHLIGHT, .clipped'):
        extra.decompose()
    name = title.get_text(' ', strip=True)
    name = re.sub(r'^New Listing\s*', '', name)
    name = re.sub(r'\s*Opens in a new window or tab$', '', name)
    return name or None


def parse_status(card, texts):
    text = first_text(card, STATUS_SELECTORS)
    if text:
        return text.split('·')[0].strip()
    for text in texts:
        if text.lower() in CONDITIONS:
            return text
    return None


def parse_shipping(card, texts):
    text = first_text(card, SHIPPING_SELECTORS)
    candidates = [text] if text else []
    candidates += [t for t in texts
                   if 'shipping' in t.lower() or 'delivery' in t.lower()]
    if not candidates:
        return None
    text = min(candidates, key=len).lower()
    if 'free' in text:
        return 0
    return to_cents(text)


def parse_items_sold(texts):
    for text in sorted(texts, key=len):
        match = re.search(r'([\d,]+)\+?\s+sold', text, re.IGNORECASE)
        if match:
            return int(match.group(1).replace(',', ''))
    return None


def parse_free_returns(card, texts):
    '''True for free returns, False for paid returns, None if not listed.'''
    tag = card.select_one('.s-item__free-returns')
    if tag is not None:
        return 'free returns' in tag.get_text(' ', strip=True).lower()
    returns = [t.lower() for t in texts if 'return' in t.lower()]
    if not returns:
        return None
    return any('free returns' in t for t in returns)


def extract_items(html):
    '''Turn one search-results page (an HTML string) into a list of dicts.'''
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    for card in soup.select(CARD_SELECTOR):
        name = parse_name(card)
        if not name or name.lower() == 'shop on ebay':
            continue  # skip eBay's placeholder card
        texts = short_texts(card)
        items.append({
            'name': name,
            'price': to_cents(first_text(card, PRICE_SELECTORS)),
            'status': parse_status(card, texts),
            'shipping': parse_shipping(card, texts),
            'free_returns': parse_free_returns(card, texts),
            'items_sold': parse_items_sold(texts),
        })
    return items


def looks_like_robot_check(html):
    lower = html.lower()
    return any(hint in lower for hint in ROBOT_HINTS)


def read_saved_pages(pages_dir):
    items = []
    for page in range(1, NUM_PAGES + 1):
        path = os.path.join(pages_dir, f'page-{page}.html')
        with open(path, encoding='utf-8') as f:
            page_items = extract_items(f.read())
        print(f'page {page}: {len(page_items)} items')
        items.extend(page_items)
    return items


def download_pages(search):
    items = []
    for page in range(1, NUM_PAGES + 1):
        response = requests.get(URL, params={'_nkw': search, '_pgn': page},
                                headers=HEADERS, timeout=10)
        if response.status_code in (403, 429):
            print(f'page {page}: HTTP {response.status_code}, stopping')
            break
        response.raise_for_status()
        page_items = extract_items(response.text)
        if not page_items:
            reason = ('robot check' if looks_like_robot_check(response.text)
                      else 'no listing cards')
            print(f'page {page}: {reason}, stopping')
            break
        print(f'page {page}: {len(page_items)} items')
        items.extend(page_items)
        if page < NUM_PAGES:
            time.sleep(1)
    return items


def save_json(items, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def save_csv(items, filename):
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(items)


def main():
    parser = argparse.ArgumentParser(description='Download eBay search results.')
    parser.add_argument('--search', required=True, help='the search term')
    parser.add_argument('--pages-dir',
                        help='read page-1.html ... page-10.html from this folder '
                             'instead of downloading')
    parser.add_argument('--csv', action='store_true',
                        help='save SEARCH_TERM.csv instead of SEARCH_TERM.json')
    args = parser.parse_args()

    if args.pages_dir:
        items = read_saved_pages(args.pages_dir)
    else:
        items = download_pages(args.search)

    if args.csv:
        filename = args.search + '.csv'
        save_csv(items, filename)
    else:
        filename = args.search + '.json'
        save_json(items, filename)
    print(f'saved {len(items)} items to {filename}')


if __name__ == '__main__':
    main()
