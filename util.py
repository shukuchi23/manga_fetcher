import os.path

from rich.progress import Progress


def get_max_power(size: int, base: int = 10):
    i = 1
    p = 10
    while p < size:
        i += 1
        p = p * base
    return i


chapter_list_filename = 'chapter_list'
download_folder = os.path.join(".", "downloads")


def construct_path_to_download(title_name: str):
    return os.path.join(download_folder, title_name)


def get_all_chapter_list_files(title_name: str):
    title_download_folder = construct_path_to_download(title_name)
    listdir = [f for f in os.listdir(title_download_folder) if f.startswith(chapter_list_filename)]
    listdir.sort()
    return listdir


def read_chapter_info(title_name: str):
    rez = []
    title_download_folder = construct_path_to_download(title_name)
    try:
        listdir = get_all_chapter_list_files(title_name)
        for f in listdir:
            with open(os.path.join(title_download_folder, f), "r", encoding="utf-8") as ch_l:
                rez.extend([x.replace("\n", "") for x in ch_l.readlines() if x])
    except:
        pass
    return rez


def append_chapter_list(title_name: str, n_chapters: list[str], progress_bar: Progress = None,
                        add_new_file: bool = False):
    list_of_ch_list = get_all_chapter_list_files(title_name)
    download = construct_path_to_download(title_name)
    file_name = os.path.join(download,
                             f'{chapter_list_filename}.txt' if not add_new_file else f'{chapter_list_filename}{len(list_of_ch_list)}.txt')
    with open(file=file_name, mode="a", encoding="utf-8") as f:
        size = len(n_chapters)
        task_id = None
        if size > 0:
            if progress_bar:
                task_id = progress_bar.add_task("Обновление chapter_list.txt", total=size)
            for ch in n_chapters:
                f.write(f'{ch}\n')
                if progress_bar:
                    progress_bar.advance(task_id, 1)
