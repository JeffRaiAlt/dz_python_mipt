import sys
from pathlib import Path

import pytest
import requests

parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))

from scraper import (get_interval, parse_books_urls,
                     get_page_counts, get_book_data, scrape_books)


def test_interval():
    assert get_interval(from_page=1, to_page=1) == (1, 1), \
        "Не верно определен интервал"

    with pytest.raises(ValueError):
        get_interval(from_page=50, to_page=51)

    with pytest.raises(ValueError):
        get_interval(from_page=2, to_page=1)


def test_parse_books_urls():
    book_catalogue_url = ("https://books.toscrape.com"
                          "/catalogue/page-1.html")
    response = requests.get(book_catalogue_url)
    assert len(parse_books_urls(response.text)) == 20, \
        "Не верное число ссылок на страницы с информации о книгах"


def test_get_page_counts():
    assert get_page_counts() == 50, "Не верное число разделов"


def test_get_book_data():
    url = ("https://books.toscrape.com/catalogue"
           "/a-light-in-the-attic_1000/index.html")
    response = get_book_data(url)
    assert len(response) == 11, "Не верное число параметров страницы"

    assert len(response["Title"]) > 0, "Отсутствует Title"
    assert len(response["Price"]) > 0, "Отсутствует Price"
    assert len(response["Description"]) > 0, "Отсутствует Description"
    assert response["Rating"] is not None, "Отсутствует Rating"
    assert response["Availability"] is not None, "Отсутствует Availability"

    assert response["Title"] == "A Light in the Attic", \
        "Отсутствует название книги"

def test_scrape_books():
    assert len(scrape_books(is_save=False, from_page=2, to_page=3)) == 40, \
        "Не верное число страниц с информацией о книгах"
