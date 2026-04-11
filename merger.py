import os
from zipfile import ZipFile, BadZipFile
import util

from rich.progress import Progress


def manga_file_count(folder_prefix) -> tuple[list[str], int]:
    files = os.listdir(folder_prefix)
    count = 0
    for f in files:
        try:
            n_file = os.path.join(folder_prefix, f)
            with ZipFile(n_file, "r") as z:
                namelist = z.namelist()
                count += len(namelist)
        except BadZipFile as b:
            print(f"error in {n_file}")
    return files, count


def merge(folder_prefix, power, rez_file_name: str, files: list[str], progress_bar: Progress = None, task_id = None):
    i = 0
    try:
        with ZipFile(rez_file_name, "w") as rez:
            for f in files:
                merge_filename = str(os.path.join(folder_prefix, f))
                with ZipFile(file=merge_filename, mode="r") as z:
                    for zf in z.namelist():
                        ext = zf[zf.rfind("."):]
                        filename = f'{i:0{power}}{ext}'
                        filename = os.path.join(folder_prefix, filename)
                        with open(filename, "wb") as tmp_pic:
                            tmp_pic.write(z.read(zf))
                        rez.write(filename=filename)
                        os.remove(path=filename)
                        i += 1
                        if progress_bar and task_id:
                            progress_bar.advance(task_id, 1)
        return True
    except:
        return False


def merge_into_archive(folder_prefix: str, title_name: str, merge_ext: str, progress_bar: Progress = None,  onefile=False):
    archive_list, page_count = manga_file_count(folder_prefix)
    archive_list.sort()
    print("Архивация...")
    task_id = None
    if progress_bar:
        task_id = progress_bar.add_task(description="Архивация", )
    rez_file_name = f'{title_name}{merge_ext}'

    def only_archive_pred(f: str):
        zip_extens = f.endswith(".cbz") or f.endswith(".cbx") or f.endswith("cbr") or f.endswith(
            ".rar") or f.endswith(".zip")
        return zip_extens and f != rez_file_name

    archive_list = [f for f in archive_list if only_archive_pred(f)]
    rez_file_name = os.path.join(folder_prefix, rez_file_name)
    can_delete_tmp = merge(folder_prefix=folder_prefix, rez_file_name=rez_file_name, power=util.get_max_power(page_count),
                     files=archive_list, progress_bar=progress_bar, task_id=task_id)
    with open(os.path.join(folder_prefix, "chapter_list.txt"), "w") as ch_list_file:
        ch_list_file.writelines("\n".join(archive_list))
    if can_delete_tmp and onefile:
        archive_list = [os.path.join(folder_prefix, x) for x in archive_list]
        for arch in archive_list:
            os.remove(arch)


if __name__ == '__main__':
    join = os.path.join(".", "downloads", "temp")
    merge_into_archive(folder_prefix=join, title_name="Старшая школа DxD", merge_ext=".cbz")
