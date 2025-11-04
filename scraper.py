import schedule
import requests
from bs4 import BeautifulSoup
import re
import time
from pathlib import Path

#url = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
URL_PREFIX = "https://books.toscrape.com/catalogue/"
FILE_NAME = "./artifacts/books_data.txt"

def get_book_data(book_url: str) -> dict:
    response = requests.get(book_url)
    if response.status_code == 200:
        return parse_book(response.text)
    else:
        raise Exception("Ошибка ", response.status_code, response.text)


"""
Соберите всю информацию, включая 
название, 
цену, 
рейтинг, 
количество в наличии, 
описание и 
дополнительные характеристики из таблицы Product Information. Результат достаточно вернуть в виде словаря.
"""

def parse_book(text: str) -> dict:
    soup = BeautifulSoup(text, "html.parser")
    book_info = {}
    article = soup.find("article", attrs={"class": "product_page"})

    book_info["name"] = article.find("h1").text.strip()

    book_info["price"] = article.find("p", attrs={"class": "price_color"}).text.strip()

    rating_tag = article.find("p", attrs={"class": "star-rating"})
    book_info["rating"] = {"One": 1, "Two": 2, "Three": 3,
                     "Four": 4, "Five": 5}.get(rating_tag.get("class")[1], 0)
    avlb_text = article.find("p", attrs={"class": "instock availability"}).text.strip()
    book_info["availability"] = re.search("\\d+", avlb_text).group()
    description_tag = article.find("div", attrs={"id": "product_description"})
    if description_tag:
        book_info["description"] = description_tag.find_next_sibling('p').text.strip()

    extra_table = article.find("table", attrs={"class": "table table-striped"})
    rows = extra_table.find_all("tr")
    for row in rows:
        if not book_info.get(row.find("th").text.strip(), None):
            book_info[row.find("th").text.strip()] = row.find("td").text.strip()
    return book_info


def get_books_urls(book_catalogue_url: str) -> list:
    response = requests.get(book_catalogue_url)
    print(book_catalogue_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        section = soup.find("section")
        rows = section.find_all("h3")
        books_url = []
        for row in rows:
            books_url.append(URL_PREFIX+row.find("a").get("href").strip())
        return books_url
    else:
        raise Exception(f"Ошибка, страница {book_catalogue_url} не найдена",
                        response.status_code, response.text)

def write_to_file(about_books: list) -> None:
    #file_name = "FILE_NAME
    file_path = Path(FILE_NAME)
    if file_path.exists():
        file_path.unlink()

    with open(FILE_NAME, "a", encoding="utf-8") as f:
        for book_info in about_books:
            for key, value in book_info.items():
                f.write(f'{key}  {value}')
                f.write('\n')

def get_page_counts() -> int:
    url = f"{URL_PREFIX}page-1.html"
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        pages_text = soup.find("ul", attrs={"class": "pager"}).text.strip()
        return int(re.search("of (\\d+)", pages_text).group(1))
    else:
        raise IOError("", response.status_code, response.text)

def get_interval(from_page, to_page):
    if from_page is None:
        from_page = 1
    if to_page is None:
        to_page = get_page_counts()
    if from_page > to_page:
        raise Exception("Ошибка", from_page, to_page)

    return from_page, to_page


def scrape_books(is_save=True, from_page=None, to_page=None):
    about_books = []
    interval = get_interval(from_page, to_page)
    for N in range(interval[0], interval[1] + 1):
        url_teml = f"{URL_PREFIX}page-{N}.html"
        list_books = get_books_urls(url_teml)
        for book_url in list_books:
            try:
                about_books.append(get_book_data(book_url))
            except Exception as e:
                print(book_url, e)
    if is_save:
        write_to_file(about_books)
    return about_books

def scrape_by_schedule(poll_interval_seconds: int = 50) -> None:
    # Запланировать запуск каждый день в 19:00 по локальному времени машины
    schedule.every().day.at("19:00").do(scrape_books)
    print("Планировщик запущен. Ожидаю 19:00 каждый день... (Ctrl+C для остановки)")
    try:
        while True:
            schedule.run_pending()
            time.sleep(poll_interval_seconds)  # проверяем расписание не постоянно, а раз в N секунд
    except KeyboardInterrupt:
        print("\n Остановлено пользователем.")

if __name__ == "__main__":
    scrape_books(from_page=50)
    #scrape_by_schedule()