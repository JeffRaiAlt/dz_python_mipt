import re
import time
from pathlib import Path

import schedule
import requests
from bs4 import BeautifulSoup

URL_PREFIX = "https://books.toscrape.com/catalogue/"
OUTPUT_FILE_NAME = "./artifacts/books_data.txt"
REQUEST_TIMEOUT = 15

def get_book_data(book_url: str) -> dict:
    """
    Функция возвращает информацию о книге по её URL
    вида https://books.toscrape.com...
    Для этого отправляет HTTP-запрос по указанному адресу страницы книги,
    извлекает основные данные (название, автора, описание, рейтинг и т.д.)
    и собирает их в словарь.
    Args:
        book_url (str): URL адрес по которому находится описание книги
    Returns:
        dict: Словарь с полями:
            - "Title" (str): Название книги.
            - "Price" (str): Стоимость книги.
            - "Description" (str): Описание книги.
            - "Rating" (int): Средняя оценка.
            - "Availability" (int): Наличие
            и дополнительные характеристики из таблицы Product Information
    """
    response = requests.get(book_url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return parse_book(response.text)


def parse_book(text: str) -> dict:
    """
    Функция осуществляет непосредственный разбор переданного текста HTML
    страницы, выделяет основные параметры книги и возвращает их в виде
    словаря.
    Args:
        text: html страницы
    Returns:
        dict: Словарь с полями:
            - "Title" (str): Название книги.
            - "Price" (str): Стоимость книги.
            - "Description" (str): Описание книги, если доступно.
            - "Rating" (int): Средняя оценка, если указана.
            - "Availability" (int): Наличие
            и дополнительные характеристики из таблицы Product Information
    """
    soup = BeautifulSoup(text, "html.parser")
    article = soup.find("article", attrs={"class": "product_page"})
    if article is None:
        raise ValueError("Не корректная структура страницы: отсутствует "
                         "тэг article.")
    book_info = {"Title": article.find("h1").text.strip()}

    price_tag = (article.find("p", attrs={"class": "price_color"}))
    # Убираем Â перед ценой
    price = price_tag.get_text(strip=True).replace("Â", "")
    book_info["Price"] = price

    rating_tag = article.find("p", attrs={"class": "star-rating"})
    rating_map = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

    if (rating_tag and rating_tag.get("class") and
            len(rating_tag["class"]) > 1):
        book_info["Rating"] = rating_map.get(rating_tag["class"][1], 0)

    avlb_tag = article.find("p", attrs={"class":
                                            "instock availability"})
    if avlb_tag:
        avlb_text = avlb_tag.get_text(strip=True)
        match = re.search(r"\d+", avlb_text)
        if match:
            book_info["Availability"] = int(match.group())

    description_tag = article.find("div", attrs={"id":
                                                     "product_description"})
    if description_tag:
        book_info["Description"] = (description_tag.
                                    find_next_sibling('p').text.strip())
    extra_table = article.find("table", attrs={"class": "table "
                                                        "table-striped"})

    rows = extra_table.find_all("tr")
    for row in rows:
        # Убираем дублирующиеся данные
        if not book_info.get(row.find("th").text.strip(), None):
            book_info[row.find("th").text.strip()] = (
                row.find("td").text.strip()).replace("Â", "")
    return book_info


def get_books_urls(book_catalogue_url: str) -> list:
    """
    Извлекает ссылки на отдельные книги со страницы каталога.
    Функция отправляет запрос к странице каталога книг, парсит HTML
    и собирает все ссылки, ведущие на страницы отдельных книг.
    Args:
        book_catalogue_url (str): URL страницы каталога книг.
    Returns:
        list: Список строковых URL, каждый из которых ведёт на страницу книги.
    """
    response = requests.get(book_catalogue_url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    section = soup.find("section")
    rows = section.find_all("h3")
    books_url = []
    for row in rows:
        books_url.append(URL_PREFIX + row.find("a").get("href").strip())
    return books_url

def write_to_file(about_books: list) -> None:
    """
    Запись полученной информации в файл
    Args:
        about_books (list): данные о книгах
    """
    Path(OUTPUT_FILE_NAME).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE_NAME, "w", encoding="utf-8") as f:
        for book_info in about_books:
            for key, value in book_info.items():
                f.write(f'{key}: {value}')
                f.write('\n')


def get_page_counts() -> int:
    """
    Определяет общее количество страниц в каталоге.
    Функция обращается к первой странице каталога находит элемент,
    содержащий информацию о количестве страниц, и извлекает это число.
    Используется при пагинации для последовательного обхода всех
    страниц каталога.
    Returns:
        int: Количество страниц каталога.
    """
    url = f"{URL_PREFIX}page-1.html"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    pages_text = soup.find("ul", attrs={"class": "pager"}).text.strip()
    return int(re.search("of (\\d+)", pages_text).group(1))


def get_interval(from_page: int, to_page: int) ->  tuple[int, int]:
    """
    Возвращает диапазон страниц для обработки.
    Функция проверяет корректность границ диапазона (номер начальной
    и конечной страниц), а если верхняя граница не указана, получает ее
    запросив информацию с сайта, если нижняя не указана ставим по
    умолчанию 1.
    Args:
        from_page (int): Номер первой страницы (включительно).
        to_page (int): Номер последней страницы (включительно).
    Returns:
        tuple[int, int]: кортеж from_page, to_page.
    Raises:
        ValueError: если from_page > to_page или если верхняя граница
        to_page, превышает максимально доступную
    """
    if from_page is None:
        from_page = 1

    max_page_number = get_page_counts()
    if to_page is None:
        to_page = max_page_number

    if from_page > to_page:
        raise ValueError("Ошибка, должно быть from_page <= to_page",
                         from_page, to_page)

    if to_page > max_page_number:
        raise ValueError(f"Ошибка, максимальная доступная "
                         f"страница {max_page_number})")
    return from_page, to_page


def scrape_books(is_save=True, from_page=None, to_page=None) -> list:
    """
    Собирает данные о книгах с сайта https://books.toscrape.com
    Функция проходит по страницам каталога книг (либо по всем доступным,
    либо в указанном диапазоне), извлекает ссылки на книги, получает
    данные по каждой книге и формирует список результатов. При
    необходимости данные
    могут быть сохранены во внешний файл.
    Args:
        is_save (bool, optional): Если True, результат будет сохранён
            в файл books_data.txt. По умолчанию True.
        from_page (int | None, optional): Номер первой страницы для анализа.
            Если None, обработка начинается с первой доступной страницы.
        to_page (int | None, optional): Номер последней страницы для анализа.
            Если None, обработка ведётся до последней доступной страницы.
    Returns:
        list: Список словарей, где каждый словарь содержит данные о книгах.
    """
    about_books = []
    interval = get_interval(from_page, to_page)
    for page_num in range(interval[0], interval[1] + 1):
        url = f"{URL_PREFIX}page-{page_num}.html"
        print(url)
        list_books = get_books_urls(url)
        for book_url in list_books:
            try:
                about_books.append(get_book_data(book_url))
            except Exception as e:
                print(book_url, e)
    if is_save:
        write_to_file(about_books)
    return about_books


def scrape_by_schedule(poll_interval_seconds: int=50) -> None:
    """
    Периодически запускает процесс сбора данных о книгах (`scrape_books`)
    по расписанию каждый день в 19:00.
    Args:
        poll_interval_seconds (int, optional): Интервал между запусками
            процесса в секундах. По умолчанию 50 секунд.
    """
    # Запланировать запуск каждый день в 19:00 по локальному времени машины
    schedule.every().day.at("19:00").do(scrape_books)
    print("Планировщик запущен. Ожидаю 19:00 каждый день... "
          "(Ctrl+C для остановки)")
    try:
        while True:
            schedule.run_pending()
            # проверяем расписание не постоянно, а раз в N секунд
            time.sleep(poll_interval_seconds)
    except KeyboardInterrupt:
        print("\n Остановлено пользователем.")


if __name__ == "__main__":
    scrape_books()
    # scrape_by_schedule()
