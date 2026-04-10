import os
import pathlib
import re
import sys
from threading import Thread
from zipfile import ZipFile, BadZipFile

import requests
from bs4 import BeautifulSoup
from rich.pretty import pretty_repr
from rich.progress import Progress, TaskID

from abstract_info_fetcher import AbstractInfoFetcher, MangaChanInfoFetcher, \
    ComXLifeInfoFetcher
from chapter_fetcher import get_chapters

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

    i = 1
    p = 10
    link_len = len(rez)
    while p < link_len:
        i += 1
        p = p * 10

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
    return num


def filter_exists(folder_prefix: str, chapter_names: list[str], pure_chapter_names: list[str],
                  download_links: list[str]):
    listdir = {file for file in os.listdir(folder_prefix)}
    listdir = {extract_num(x): os.path.getsize(f'{"/".join(pathlib.Path(folder_prefix).parts)}/{x}') for x in listdir if x != 'tmp'}
    remove_chapters = []
    remove_links = []
    remove_pure_chapter_names = []
    need_print_new_chapter_manga = len(listdir) > 0
    for i, chapter_name in enumerate(chapter_names):
        finded_chapter = extract_num(chapter_name[chapter_name.index("Глава "):])
        if finded_chapter not in listdir or listdir[finded_chapter] < 8192:
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
                   title_name: str):
    download_links = fetcher.get_download_links(title_url=download_manga_url)
    pure_chapter_names = get_chapters(title_name=title_name, dirty_len=len(download_links))
    output_filenames = None
    if folder_prefix:
        output_filenames = [os.path.join(folder_prefix, prepare_name(x)) for x in pure_chapter_names]
    link_count = len(download_links)
    filter_exists(folder_prefix=folder_prefix, chapter_names=output_filenames, pure_chapter_names=pure_chapter_names,
                  download_links=download_links)
    if len(download_links) == 0 and len(download_links) != link_count:
        print(f"Манга '{title_name} полностью скачана'")
        return None

    print("[Данные о главах]")
    chapters_count = len(output_filenames)
    if chapters_count == 0 or link_count == 0:
        sys.stderr.writelines("Что-то не так...")
        print(f"\tНайдено в {chapter_fetcher_name} = {chapters_count}")
        print(f"\tНайдено в {fetcher.name} = {link_count}")
        exit(1)
    elif chapters_count != link_count:
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
        download_manga(folder_prefix, progress_bar, fetcher, download_manga_url, title_name)


def manga_file_count(folder_prefix) -> tuple[list[str], int]:
    files = os.listdir(folder_prefix)
    count = 0
    for f in files:
        # if f.endswith(".cbz"):
        #     f = f.replace(".cbz", "")
        # elif f.endswith(".cbr"):
        #     f = f.replace(".cbr", "")
        try:
            join = os.path.join(folder_prefix, f)
            with ZipFile(join, "r") as z:
                namelist = z.namelist()
                count += len(namelist)
        except BadZipFile as b:
            print(f"error in {join}")
    return files, count


def merge(folder_prefix, power, merge_ext: str, progress_bar:Progress, files:list[str], title_name=None, task=None):
    i = 0
    rez_file = os.path.join(folder_prefix, f'{title_name}{merge_ext}')
    # print(f"Создание результирующего файла: {rez_file}")
    with ZipFile(rez_file, "w") as rez:
        # print("Файл создан")
        for f in files:
            if not f.endswith(".cbz") and not f.endswith(".cbx") and not f.endswith("cbr") and not f.endswith(".rar") and not f.endswith(".zip"):
                print(f"Пропуск {f}")
                continue
            merge_filename = str(os.path.join(folder_prefix, f))
            # print(f"обрабатывается архив: {merge_filename}")
            with ZipFile(file=merge_filename, mode="r") as z:
                for zf in z.namelist():
                    ext = zf[zf.rfind("."):]
                    filename = f'{i:0{power}}{ext}'
                    filename = os.path.join(folder_prefix, filename)
                    # print(f"Взят файл {filename}")
                    with open(filename, "wb") as tmp_pic:
                        tmp_pic.write(z.read(zf))
                    # print(f"Разархивирован файл {filename}")
                    rez.write(filename=filename)
                    # print(f"файл добавлен в архив {merge_filename}")
                    os.remove(path=filename)
                    # print(f"файл удален {filename}")
                    i += 1
            progress_bar.advance(task, 1)
    # os.rmdir(tmp_dir)
    return rez_file


def merge_into_archive(folder_prefix: str, progress_bar: Progress, title_name: str, merge_ext: str):
    archive_list, page_count = manga_file_count(folder_prefix)
    archive_list.sort()
    i = 1
    p = 10
    link_len = page_count
    while p < link_len:
        i += 1
        p = p * 10
    task = progress_bar.add_task(description="Архивация в единый файл...", total=len(archive_list))
    # task = None
    print("Архивация...")
    filename = merge(folder_prefix=folder_prefix, power=i, progress_bar=progress_bar, merge_ext=merge_ext, files=archive_list, title_name=title_name, task=task)
    # archive_list = [os.path.join(folder_prefix, x) for x in archive_list]
    # for arch in archive_list:
    #     os.remove(arch)


if __name__ == '__main__':
    fetchers: list[AbstractInfoFetcher] = [ComXLifeInfoFetcher(), MangaChanInfoFetcher()]

    argv_ = sys.argv

    merge_mode = "--merge" in argv_
    merge_arch_ext = '.cbz'
    if merge_mode:
        try:
            merge_arch_ext = f'.{argv_[argv_.index("--merge") + 1]}'
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

    folder = os.path.join(".", "downloads", prepare_name(title_name))
    os.makedirs(name=folder, exist_ok=True)
    with Progress(expand=True) as p:
        download_manga(folder_prefix=str(folder), progress_bar=p, fetcher=cur_fetcher, download_manga_url=download_url,
                       title_name=title_name)
        if merge_mode:
            merge_into_archive(folder_prefix=str(folder), progress_bar=p, title_name=title_name,
                               merge_ext=merge_arch_ext)
