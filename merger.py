import os
import sys
from codecs import replace_errors
from zipfile import ZipFile, BadZipFile

from rich.progress import Progress

import util


def only_archive_pred(f: str):
    zip_extens = f.endswith(".cbz") or f.endswith(".cbx") or f.endswith("cbr") or f.endswith(
        ".rar") or f.endswith(".zip")
    return zip_extens


def manga_file_count(folder_prefix, in_files: list[str] = []) -> dict[str, int]:
    total_mode = len(in_files) == 0
    if total_mode:
        files = [x for x in os.listdir(folder_prefix) if only_archive_pred(x)]
    else:
        files = [x for x in os.listdir(folder_prefix) if x[:x.rindex(".")] in in_files and only_archive_pred(x)]
    rez = {}
    for f in files:
        try:
            rez[f] = 0
            n_file = os.path.join(folder_prefix, f)
            with ZipFile(n_file, "r") as z:
                namelist = z.namelist()
                f_page_count = len(namelist)
                rez[f] = f_page_count
        except BadZipFile as b:
            print(f"error in {n_file}")
    return rez


def merge(folder_prefix, power, rez_file_name: str, files: list[str], progress_bar: Progress = None, task_id=None,
          start_page=0):
    i = start_page
    try:
        with ZipFile(rez_file_name, "w") as rez:
            for f in files:
                merge_filename = str(os.path.join(folder_prefix, f))
                with ZipFile(file=merge_filename, mode="r") as z:
                    for zf in z.namelist():
                        ext = zf[zf.rfind("."):]
                        filename_pure = f'{i:0{power}}{ext}'
                        filename = os.path.join(folder_prefix, filename_pure)
                        with open(filename, "wb") as tmp_pic:
                            tmp_pic.write(z.read(zf))
                        rez.write(filename=filename, arcname=filename_pure)
                        os.remove(path=filename)
                        i += 1
                        if progress_bar and task_id:
                            progress_bar.advance(task_id, 1)
        return True
    except:
        return False


def merge_into_archive(folder_prefix: str, title_name: str, merge_ext: str, progress_bar: Progress = None,
                       onefile=False, files=[], delta=False):
    file_and_pages = manga_file_count(folder_prefix, files)
    archive_list = [f for f in file_and_pages.keys()]
    page_count = 0
    for x in file_and_pages.values():
        page_count += x

    archive_list.sort()
    print("Архивация...")
    task_id = None
    if progress_bar:
        task_id = progress_bar.add_task(description="Архивация", )

    if onefile:
        num = ""
    else:
        num = len(util.get_all_chapter_list_files(title_name)) - 1

    rez_file_name = f'{title_name}{num}{merge_ext}'
    start_page = 0
    if onefile and  rez_file_name in file_and_pages:
        start_page = file_and_pages[rez_file_name] + 1

    archive_list = [f for f in archive_list if only_archive_pred(f) and f != rez_file_name]
    rez_file_name = os.path.join(folder_prefix, rez_file_name)

    can_delete_tmp = merge(folder_prefix=folder_prefix, rez_file_name=rez_file_name,
                           power=util.get_max_power(page_count),
                           files=archive_list, progress_bar=progress_bar, task_id=task_id, start_page=start_page)
    if can_delete_tmp and (onefile or delta):
        archive_list = [os.path.join(folder_prefix, x) for x in archive_list]
        for arch in archive_list:
            os.remove(arch)
    return archive_list


if __name__ == '__main__':
    argv_ = sys.argv[1]
    join = os.path.join(".", "downloads", argv_)
    merge_into_archive(folder_prefix=join, title_name=argv_, merge_ext=".cbz", onefile=True)
