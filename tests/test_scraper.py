import pytest
import sys
from pathlib import Path

parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))

#from ..scraper import (get_book_data, get_books_urls,
#                     get_page_counts, get_interval, scrape_books)
from scraper import (get_interval, get_books_urls,
                     get_page_counts, get_book_data, scrape_books)

#from ..smth import line_eq

# Это вместо глобальных переменных, можно данные раздавать
@pytest.fixture
def create_fixture():
    return [1, 2, 3, 4, 5, 7]


def test_interval():
    assert get_interval(from_page=1, to_page=1) == (1, 1), "ага"


def test_get_books_urls():
    book_catalogue_url = "https://books.toscrape.com/catalogue/page-1.html"
    assert len(get_books_urls(book_catalogue_url)) == 20, "ага"


def test_get_page_counts():
    assert get_page_counts() == 50, "aua"


def test_get_book_data():
    url = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    assert len(get_book_data(url)) == 12, "gg"


def test_scrape_books():

    print(scrape_books(is_save=False, from_page=2, to_page=2))
    #assert scrape_books(is_save=False, from_page=2, to_page=2) == [1, 2, 3, 4, 5, 7]
