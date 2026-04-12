import os
import pathlib
import re
import sys
from threading import Thread

import requests
from bs4 import BeautifulSoup
from rich.progress import Progress, TaskID

import util
from abstract_info_fetcher import AbstractInfoFetcher, MangaChanInfoFetcher, \
    ComXLifeInfoFetcher
from chapter_fetcher import get_chapters
from merger import merge_into_archive
from util import get_max_power

chapter_fetcher_name = "a.zazaza.me"


def extract_ru_title(fetcher: AbstractInfoFetcher, title_name: str):
    if isinstance(fetcher, ComXLifeInfoFetcher) or isinstance(fetcher, MangaChanInfoFetcher):
        if title_name.count("(") > 0:
            title_name = title_name[title_name.index("(") + 1:title_name.index(")")]
        elif title_name.count("/") > 0:
            title_name = title_name.split("/", maxsplit=2)[1]
    return title_name.strip()


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

    i = get_max_power(size=len(rez))
    rez = [f'{folder_prefix}{j:0{i}}-{x}' for j, x in enumerate(rez)]

    return rez


def download_list(fetcher: AbstractInfoFetcher, progress_bar: Progress, increase_fun, download_url: list[str],
                  output_filenames: list[str], p_tasks: list[TaskID], err_list: list[str]):
    session = fetcher.get_download_session()
    try:
        for i, url in enumerate(download_url):
            task_id = p_tasks[i]
            if not fetcher.download(session=session, download_url=url, output_filename=output_filenames[i],
                                    progress_bar=progress_bar,
                                    task=task_id):
                err_list.append(url)
            progress_bar.update(task_id, visible=False)
            increase_fun()

    finally:
        if session:
            session.close()


def get_threads(fetcher: AbstractInfoFetcher, progress_bar: Progress, download_links: list[str],
                output_filenames: list[str], pure_chapter_names: list[str], er_lst: list[str]):
    rez = []
    size = len(download_links)
    task = progress_bar.add_task("Скачивание...", total=size)

    def increase_shared_progress_bar_func():
        progress_bar.advance(task, 1)

    if size < 8:
        for i in range(size):
            rez.append(Thread(name=f"Thread{i}", target=download_list,
                              args=(fetcher, progress_bar, increase_shared_progress_bar_func, [download_links[i]],
                                    [output_filenames[i]], [
                                        progress_bar.add_task(description=pure_chapter_names[i], start=False,
                                                              visible=False)], er_lst)))
    else:
        ids_lst = [[] for _ in range(8)]
        output_filenames_lst = [[] for _ in range(8)]
        pure_chapter_names_lst = [[] for _ in range(8)]
        tasks = [[] for _ in range(8)]
        for i, e in enumerate(download_links):
            ids_lst[i % 8].append(e)
            output_filenames_lst[i % 8].append(output_filenames[i])
            pure_chapter_names_lst[i % 8].append(pure_chapter_names[i])
            tasks[i % 8].append(progress_bar.add_task(description=pure_chapter_names[i], start=False, visible=False))

        for i in range(8):
            rez.append(
                Thread(name=f"Thread{i}", target=download_list,
                       args=(
                           fetcher, progress_bar, increase_shared_progress_bar_func, ids_lst[i],
                           output_filenames_lst[i],
                           tasks[i], er_lst)))

    progress_bar.start_task(task)
    return rez


def extract_num(line: str):
    index = line.index(".")
    num = line[6:index]
    return int(num)


def filter_exists(folder_prefix: str, chapter_names: list[str], pure_chapter_names: list[str],
                  download_links: list[str], already_exists: list[str]):
    if not already_exists:
        already_exists = {file for file in os.listdir(folder_prefix)}
        already_exists = {extract_num(x) for x in already_exists if
                          x != 'tmp' and not x.startswith(util.chapter_list_filename)}
    else:
        already_exists = {extract_num(x) for x in already_exists if x != "tmp"}
    remove_chapters = []
    remove_links = []
    remove_pure_chapter_names = []
    need_print_new_chapter_manga = len(already_exists) > 0
    for i, chapter_name in enumerate(chapter_names):
        finded_chapter = extract_num(chapter_name[chapter_name.index("Глава "):])
        if finded_chapter not in already_exists:
            if need_print_new_chapter_manga:
                print(f"Найдена новая  манга: {pure_chapter_names[i]}")
        else:
            remove_chapters.append(chapter_name)
            remove_links.append(download_links[i])
            remove_pure_chapter_names.append(pure_chapter_names[i])
    for remove_chapter in remove_chapters:
        chapter_names.remove(remove_chapter)
    for remove_link in remove_links:
        download_links.remove(remove_link)
    for remove_link in remove_pure_chapter_names:
        pure_chapter_names.remove(remove_link)


def download_manga(folder_prefix: str, progress_bar: Progress, fetcher: AbstractInfoFetcher, download_manga_url: str,
                   title_name: str, is_delta=False, is_onefile_mode=True):
    download_links = fetcher.get_download_links(title_url=download_manga_url)
    pure_chapter_names = get_chapters(title_name=title_name, dirty_len=len(download_links))
    info = util.read_chapter_info(title_name)
    output_filenames = None
    if folder_prefix:
        output_filenames = [os.path.join(folder_prefix, prepare_name(x)) for x in pure_chapter_names]
    link_count = len(download_links)
    log_files = pure_chapter_names.copy()
    filter_exists(folder_prefix=folder_prefix, chapter_names=output_filenames, pure_chapter_names=pure_chapter_names,
                  download_links=download_links, already_exists=info)
    if len(download_links) == 0 and len(download_links) != link_count:
        print(f"Манга '{title_name} полностью скачана'")
        if not info:
            util.append_chapter_list(title_name=title_name, n_chapters=log_files, add_new_file=False)
        return []

    print("[Данные о главах]")
    chapters_count = len(output_filenames)
    if chapters_count == 0 or link_count == 0:
        sys.stderr.writelines("Что-то не так...")
        print(f"\tНайдено в {chapter_fetcher_name} = {chapters_count}")
        print(f"\tНайдено в {fetcher.name} = {link_count}")
        exit(1)
    elif chapters_count != link_count:
        if chapters_count != len(download_links):
            min_size = min(chapters_count, link_count)
            print(f"\tНайдено в {chapter_fetcher_name} = {len(output_filenames)}")
            print(f"\tНайдено в {fetcher.name} = {link_count}")
            # print(f"Будет скачано минимально возможное кол.-во глав: {min_size}")
            output_filenames = output_filenames[:min_size]
            download_links = download_links[:min_size]
    else:
        print(f"\tНайдено в manga_hub = {len(output_filenames)}")
        print(f"\tНайдено в {fetcher.name} = {link_count}")
    error_lst = []
    threads: list[Thread] = get_threads(fetcher=fetcher, progress_bar=progress_bar, download_links=download_links,
                                        output_filenames=output_filenames, pure_chapter_names=pure_chapter_names,
                                        er_lst=error_lst)
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
    if len(error_lst) > 0:
        print('Повторное скачивание...')
        download_manga(folder_prefix, progress_bar, fetcher, download_manga_url, title_name)
    util.append_chapter_list(title_name=title_name, n_chapters=pure_chapter_names, add_new_file=not is_onefile_mode)
    return pure_chapter_names


if __name__ == '__main__':
    fetchers: list[AbstractInfoFetcher] = [ComXLifeInfoFetcher(), MangaChanInfoFetcher()]

    argv_ = sys.argv
    is_onefile_mode = "--onefile" in argv_
    is_delta_mode = "--delta" in argv_
    ext_flag = "-e" in argv_
    merge_arch_ext = '.cbz'
    if ext_flag:
        try:
            merge_arch_ext = f'.{argv_[argv_.index("-e") + 1]}'
        except IndexError:
            pass

    cur_fetcher = None
    title_name = None
    download_url = None
    mhub_url = None
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

    title_name = prepare_name(title_name)
    folder = util.construct_path_to_download(title_name)
    os.makedirs(name=folder, exist_ok=True)
    with Progress(expand=True) as p:
        downloaded_chapters = download_manga(folder_prefix=str(folder), progress_bar=p, fetcher=cur_fetcher,
                               download_manga_url=download_url, title_name=title_name, is_delta=is_delta_mode,
                               is_onefile_mode=is_onefile_mode)
        if is_onefile_mode:
            archive = merge_into_archive(folder_prefix=str(folder), title_name=title_name, merge_ext=merge_arch_ext,
                                         progress_bar=p)
        elif is_delta_mode:
            merge_into_archive(folder_prefix=str(folder), progress_bar=p, title_name=title_name, merge_ext=merge_arch_ext, files=downloaded_chapters, delta=True)
        util.append_chapter_list(title_name=title_name, n_chapters=downloaded_chapters, add_new_file=is_onefile_mode)
