import os
import pathlib
import re
import sys
import threading
import time
from threading import Thread, Lock

import requests
from bs4 import BeautifulSoup

from abstract_info_fetcher import AbstractInfoFetcher, MangaChanInfoFetcher, \
    ComXLifeInfoFetcher
from chapter_fetcher import get_chapters

chapter_fetcher_name = "a.zazaza.me"
progres_bar = {}
progres_bar_lock = Lock()


def cursor_up(count):
    print(f"\x1b[{count}F", end="")


def cursor_down(count):
    print(f"\x1b[{count}E", end="")


def cursor_right(count):
    print(f"\x1b[{count}C", end="")


def print_progress_bar():
    progres_bar_lock.acquire()
    print("".join([f"{a}\t:{b[0]}\\{b[1]}\n" for a, b in progres_bar.items()]), end="", flush=True)
    progres_bar_lock.release()


# def find_manga_hub_url(title_name: str):
#     soup = BeautifulSoup(
#         requests.get(f"{mhub_base_url}/suggestions", params={"type": "title", "query": title_name}).text, "html.parser")
#     find = soup.find("a")
#     if find:
#         href_ = find.attrs['href']
#         print(f"MANGA_HUB: найдено {href_}")
#         return f"{mhub_base_url}{href_}"
#     else:
#         sys.stderr.write("Не удалось найти мангу на MANGA_HUB")
#
def extract_ru_title(fetcher: AbstractInfoFetcher, title_name: str):
    if isinstance(fetcher, ComXLifeInfoFetcher) or isinstance(fetcher, MangaChanInfoFetcher):
        if title_name.count("(") > 0:
            title_name = title_name[title_name.index("(") + 1:title_name.index(")")]
        elif title_name.count("/") > 0:
            title_name = title_name.split("/", maxsplit=2)[1]
    return title_name


def search_mode(fetcher: AbstractInfoFetcher, title_name: str) -> tuple:
    while title_name:
        finded = fetcher.find_anime(title_name)
        chooser = [x for x in finded.keys()]
        if not chooser:
            return None, None

        for i, x in enumerate(finded):
            print(f"[{i + 1}]  - {x}")
        print("Выберите номер, или введите другое название манги(0 - выход): ", end="", flush=True)
        title_name = sys.stdin.readline().replace("\n", "")
        if title_name.isdigit():
            select = int(title_name)
            limit = len(chooser)

            if select == 0:
                print("\nВыход\n")
                exit(0)
            elif select > limit or select < 1:
                sys.stdin.write("Введено некорректное значение. Попробуйте ещё раз\0\n")
                continue
            else:
                title_name: str = chooser[select - 1]
                manga_url = finded[title_name]
                print(f"url: {manga_url}")
                # manga_hub_chapter_url = find_manga_hub_url(title_name)
                title_name = extract_ru_title(fetcher, title_name)
                print(f"Выбрана манга: {title_name}")
                return title_name, manga_url
    return None, None


def search(fetcher: AbstractInfoFetcher, title: str) -> tuple:
    finded = fetcher.find_anime(title)
    chooser = [x for x in finded.keys()]
    for i, x in enumerate(finded):
        print(f"[{i + 1}]  - {x}")
    print("Выберите номер, или введите другое название манги(0 - выход): ", end="", flush=True)
    buf = sys.stdin.readline().replace("\n", "")
    if buf.isdigit():
        select = int(buf)
        limit = len(chooser)

        if select == 0:
            print("\nВыход\n")
            exit(0)
        elif select > limit or select < 1:
            sys.stdin.write("Введено некорректное значение. Попробуйте ещё раз\0\n")
            print("Введите мангу для скачивания: ", end="", flush=True)
            return search_mode(fetcher, sys.stdin.readline())
        else:
            title_name = chooser[select - 1]
            manga_url = finded[title_name]
            print(f"url: {manga_url}")
            title_name = extract_ru_title(fetcher, title_name)
            print(f"Выбрана манга: {title_name}")
            return title_name, manga_url
    return None, None, None


replace_html_trash_pattern = re.compile("\\s{2,}")


def prepare_name(name):
    # Заменяем символы, запрещенные в именах файлов
    # Windows: \ / : * ? " < > |
    # Unix: / (только слеш запрещен, но лучше перестраховаться)
    safe_name = re.sub(r'[\\/*?:"<>|]', '#', name)

    # Также можно заменить управляющие символы
    safe_name = ''.join(c for c in safe_name if ord(c) >= 32)
    return safe_name


def create_safe_folder(name):
    folder_path = pathlib.Path(prepare_name(name))
    folder_path.mkdir(parents=True, exist_ok=True)
    print(f"Папка создана: {folder_path.absolute()}")
    return folder_path.absolute()


def get_pretty_chapter_names(url: str, folder_prefix: str = ""):
    rez = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Connection": "keep-alive"
    }
    if folder_prefix:
        folder_prefix = folder_prefix + '/'

    soup = BeautifulSoup(requests.get(url).text, "html.parser")
    select = soup.select(selector="a.d-inline-flex.ms-2.fs-2.fw-medium.text-reset.min-w-0.flex-lg-grow-1")
    for s in select:
        rez.insert(0, prepare_name(replace_html_trash_pattern.sub(repl="", string=s.text)))

    i = 1
    p = 10
    link_len = len(rez)
    while p < link_len:
        i += 1
        p = p * 10

    rez = [f'{folder_prefix}{j:0{i}}-{x}' for j, x in enumerate(rez)]

    return rez


def download_list(fetcher: AbstractInfoFetcher, download_url: list[str], output_filenames: list[str]):
    session = fetcher.get_download_session()
    try:
        thread_name = threading.current_thread().name
        for i, url in enumerate(download_url):
            fetcher.download(session=session, download_url=url, output_filename=output_filenames[i])
            progres_bar_lock.acquire()
            progres_bar[thread_name][0] += 1
            progres_bar_lock.release()
    finally:
        if session:
            session.close()


def get_threads(size: int, fetcher: AbstractInfoFetcher, download_links: list[str], names: list[str]):
    rez = []
    if size < 8:
        for i in range(size):
            thread_name = f"Thread{i}"
            progres_bar[thread_name] = [0, 1]
            rez.append(Thread(name=thread_name, target=download_list, args=(fetcher, [download_links[i]], [names[i]])))
    else:
        ids_lst = [[] for _ in range(8)]
        names_lst = [[] for _ in range(8)]
        for i, e in enumerate(download_links):
            ids_lst[i % 8].append(e)
            names_lst[i % 8].append(names[i])
        for i in range(8):
            thread_name = f"Thread{i}"
            progres_bar[thread_name] = [0, len(ids_lst[i])]
            rez.append(Thread(name=thread_name, target=download_list, args=(fetcher, ids_lst[i], names_lst[i])))

    return rez


def download_manga(folder_prefix: str, fetcher: AbstractInfoFetcher, download_manga_url: str, title_name: str):
    chapter_names = get_chapters(title_name)
    # chapter_names = get_pretty_chapter_names(folder_prefix=folder_prefix, url=f"{manga_hub_chapter_url}/chapters")
    download_links = fetcher.get_download_links(download_manga_url)
    if folder_prefix:
        chapter_names = [os.path.join(folder_prefix, x) for x in chapter_names]
    print("[Данные о главах]")
    link_count = len(download_links)
    chapters_count = len(chapter_names)
    if chapters_count == 0 or link_count == 0:
        sys.stderr.writelines("Что-то не так...")
        print(f"\tНайдено в {chapter_fetcher_name} = {chapters_count}")
        print(f"\nНайдено в {fetcher.name} = {link_count}")
        exit(1)
    elif chapters_count != link_count:
        min_size = min(chapters_count, link_count)
        print(f"\tНайдено в {chapter_fetcher_name} = {len(chapter_names)}")
        print(f"\nНайдено в {fetcher.name} = {link_count}")
        print(f"Будет скачано минимально возможное кол.-во глав: {min_size}")
        chapter_names = chapter_names[:min_size]
        download_links = download_links[:min_size]
    else:
        print(f"\tНайдено в manga_hub = {len(chapter_names)}")
        print(f"\nНайдено в {fetcher.name} = {link_count}")

    for chapter_name in chapter_names:
        print(chapter_name)

    threads: list[Thread] = get_threads(fetcher=fetcher, size=link_count, download_links=download_links,
                                        names=chapter_names)
    thread_count = len(threads)
    for t in threads:
        t.start()

    fl = True
    while fl:
        t = True
        for t in threads:
            if t.is_alive():
                t = False
                break
        if t:
            fl = False
        else:
            print_progress_bar()
            print("Загрузка ", end="", flush=True)
            for i in range(4):
                print(".", end="", flush=True)
                time.sleep(1)
            cursor_up(thread_count)
    cursor_down(thread_count + 1)


if __name__ == '__main__':
    fetchers: list[AbstractInfoFetcher] = [MangaChanInfoFetcher(), ComXLifeInfoFetcher()]

    argv_ = sys.argv
    cur_fetcher = None
    title_name = None
    download_url = None
    mhub_url = None
    if len(argv_) > 1:
        while not title_name:
            for fetcher in fetchers:
                print(f"Поиск в {fetcher.name} ...")
                title_name, download_url = search(fetcher, argv_[1:])
                if title_name:
                    print("Манга найдена!")
                    cur_fetcher = fetcher
                    break
    else:
        while not title_name:
            print("Введите мангу для скачивания: ", end="", flush=True)
            readline = sys.stdin.readline()
            for fetcher in fetchers:
                print(f"Поиск в {fetcher.name} ...")
                title_name, download_url = search_mode(fetcher, title_name=readline)
                if title_name:
                    print("Манга найдена!")
                    cur_fetcher = fetcher
                    break

    folder = os.path.join(".", "downloads", prepare_name(title_name))
    os.makedirs(name=folder, exist_ok=True)
    download_manga(folder_prefix=str(folder), fetcher=cur_fetcher, download_manga_url=download_url,
                   title_name=title_name)
