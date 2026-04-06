# класс только качает файлы
import json
import os.path
import re

import requests
from bs4 import BeautifulSoup
from rich.progress import Progress, TaskID

import fucked_up_security


def clone_and_update_header(header: dict, update_data: dict):
    copy = header.copy()
    copy.update(update_data)
    return copy


def get_auth_cookie():
    if os.path.exists("browser_state.json"):
        with open("browser_state.json", "r") as f:
            cookies_ = json.load(f)['cookies']
            return cookies_
    return None


auth_cookie: list = get_auth_cookie()
download_try_limit = 3


class AbstractInfoFetcher:

    def __init__(self, base_url, search_url, name):
        self.__base_url = base_url
        self.__search_url = search_url
        self.__name = name
        pass

    def find_anime(self, title_name: str) -> dict:
        pass

    @property
    def name(self):
        return self.__name

    @property
    def base_url(self):
        return self.__base_url

    @property
    def search_url(self):
        return self.__search_url

    def get_download_links(self, title_url: str):
        pass

    def get_download_header(self, download_url: str) -> dict:
        pass

    def get_download_session(self):
        pass

    def get_download_response_and_file_ext(self, session: requests.Session, download_url: str) -> tuple[
        requests.Response, str]:
        pass

    def download(self, session: requests.Session, download_url: str, output_filename: str, progress_bar: Progress,
                 try_count=0, task: TaskID = None) -> bool:
        if try_count >= download_try_limit:
            return False
        try:
            response, ext = self.get_download_response_and_file_ext(session=session, download_url=download_url)
            file_len = int(response.headers["Content-Length"])
            if try_count == 0:
                progress_bar.update(task_id=task, visible=True, total=file_len)
                progress_bar.start_task(task)
            ext = ext if ext else ".zip"
            with open(f'{output_filename}{ext}', "wb") as file:
                for chunk in response.iter_content(8192):
                    file.write(chunk)
                    progress_bar.advance(task, len(chunk))
            return True
        except requests.exceptions.RequestException as e:
            print(f"Произошла ошибка при скачивании: {e}")
            progress_bar.stop_task(task)
            return False
        except Exception as e:
            if try_count == 0:
                print(f'[{output_filename}]Неожиданная ошибка: попытка скачать  {try_count + 1}')
            if not self.download(session, download_url, output_filename, try_count + 1):
                if try_count == 0:
                    import traceback
                    print(f"[{output_filename}] Неожиданная ошибка: {e}")
                    traceback.print_exc()
                    progress_bar.stop_task(task)
                    return False
            elif try_count == 0:
                print(f'[{output_filename}] - успешно скачан')
                return True


class MangaChanInfoFetcher(AbstractInfoFetcher):
    def __init__(self):
        super().__init__("https://im.manga-chan.me", "https://im.manga-chan.me/engine/ajax/search.php", "Манга-Тян")
        self.__download_header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "Connection": "keep-alive"
        }

    def find_anime(self, title_name: str) -> dict:
        soup = BeautifulSoup(requests.post(self.search_url, data={"query": title_name}).text, "html.parser")
        rez = {}
        for x in soup.find_all("a"):
            if "href" in x.attrs and x.text != "Все результаты":
                href_ = x.attrs["href"]
                rez[x.text] = f"{self.base_url}/download/{href_[href_.rfind('/') + 1:]}"

        return rez

    def get_download_session(self):
        return requests.Session()

    def get_download_links(self, title_url: str) -> list[str]:
        chapter_urls = f'{self.base_url}/download{title_url[title_url.rfind("/"):]}'

        soap = BeautifulSoup(requests.get(chapter_urls).text, "html.parser")
        table = soap.find("table", {"id": "download_table"})
        a_ = table.find_all("a")
        i = 1
        p = 10
        link_len = len(a_)
        while p < link_len:
            i += 1
            p = p * 10

        download_url_format = "https://dl.manga-chan.me/engine/download.php?id="
        rez = []
        for j, row in enumerate(a_):
            href_ = row.attrs["href"]
            id_index = href_.rfind("=") + 1
            if id_index > 0:
                rez.insert(0, f'{download_url_format}{int(href_[id_index:])}')
        print(f'Найдено глав: {len(rez)}')
        return rez

    def get_download_header(self, download_url: str) -> dict:
        return clone_and_update_header(header=self.__download_header,
                                       update_data={"Referer": self.base_url,
                                                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"})

    def get_download_response_and_file_ext(self, session: requests.Session, download_url: str) -> tuple:
        try:
            header = self.get_download_header(download_url)
            response = session.get(download_url, headers=header, stream=True,
                                   allow_redirects=True, timeout=30000)
            if response.status_code == 200:
                content_disposition = response.headers.get('Content-Disposition')
                if content_disposition and 'filename=' in content_disposition:
                    match = re.search(r'filename[=;"\']+([^"\']+)', content_disposition)
                    if match:
                        output_filename = match.group(1)
                        return response, output_filename[output_filename.rfind('.'):]
                return response, None
            elif response.status_code == 302 or response.status_code == 301:
                print(f"Редирект на: {response.headers.get('Location')}")
                # Если редирект, то следуем по нему вручную
                new_url = response.headers.get('Location')
                if new_url:
                    response2 = session.get(new_url, headers=header, stream=True, timeout=30000)

                    content_disposition = response2.headers.get('Content-Disposition')
                    if content_disposition and 'filename=' in content_disposition:
                        match = re.search(r'filename[=;"\']+([^"\']+)', content_disposition)
                        if match:
                            output_filename = match.group(1)
                            return response2, output_filename[output_filename.rfind('.'):]
                    return response2, None
                return None, None
            return None, None
        except requests.exceptions.RequestException as e:
            print(f"Произошла ошибка при скачивании: {e}")
            return None, None
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")
            import traceback
            traceback.print_exc()
            return None, None


class ComXLifeInfoFetcher(AbstractInfoFetcher):

    def __init__(self):
        super().__init__("https://com-x.life", "https://com-x.life/search/", "com-x.life")
        self.__header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"{self.base_url}/main",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "Connection": "keep-alive",
        }
        self.__session_not_browser = self.__create_session_test()
        self.__pre_init()

    def __del__(self):
        not_browser = self.__session_not_browser
        if not_browser:
            try:
                not_browser.close()
            except Exception as e:
                print(f"Что-то пошло не так при завершении сессии: {e}")

    def __pre_init(self):
        try:
            get = self.session_not_browser.get(f'{self.search_url}/Naruto')
            if get.status_code == 200 or (get.status_code == 400 and get.history[0].status_code == 302):
                pass
            else:
                print("Что-то тут не так...")
            return None
        except Exception as e:
            print(f"Ошибка инициализации: {e}")
            return None

    def __create_session(self):
        if not fucked_up_security.has_auth():
            print(f"Укажите ваши учётные данные")
            fucked_up_security.auth_async(self.base_url)

    def __create_session_test(self):
        try:
            session = requests.Session()
            session.headers = self.__header
            __fill_cookies__(session)
            session.get(f"{self.base_url}/main")
            return session
        except requests.exceptions.RequestException as e:
            print(f"Произошла ошибка при скачивании: {e}")
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")
            import traceback
            traceback.print_exc()

    @property
    def session_not_browser(self) -> requests.Session:
        return self.__session_not_browser

    def find_anime(self, title_name: str) -> dict:
        html = self.session_not_browser.get(f'{self.search_url}{title_name}', timeout=3000).text
        print()
        soup = BeautifulSoup(html, "html.parser")
        col_main = soup.find("main", attrs={"class": "col-main"})
        rez = {}

        for x in col_main.find_all("h3"):
            rez[x.text] = x.find("a").attrs["href"]
        return rez

    def get_chapters_list(self, manga_url):
        clean_url = manga_url.split('#')[0]
        response = self.session_not_browser.get(clean_url)
        if response.status_code != 200:
            print(f"✗ Ошибка при загрузке страницы: {response.status_code}")
            if "Just a moment..." in response.text or response.status_code == 403:
                print(
                    "✗ Похоже на защиту Cloudflare или бан. Попробуйте удалить comx_cookies.json и авторизоваться заново.")
            return None, None
        soup = BeautifulSoup(response.content, 'lxml')
        script_data = None
        for script in soup.find_all('script'):
            if script.string and 'window.__DATA__' in script.string:
                script_data = script.string
                break
        if not script_data:
            print("✗ Не удалось найти данные о главах (window.__DATA__)")
            return None, None
        try:
            json_match = re.search(r'window\.__DATA__\s*=\s*({.+?});', script_data, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                chapters = data.get('chapters', [])
                chapters.sort(key=lambda x: x.get('posi', 0))
                manga_title_raw = data.get("title", "Unknown Manga")
                manga_title = self.sanitize_filename(manga_title_raw)
                return chapters, manga_title
        except Exception as e:
            print(f"✗ Ошибка парсинга данных: {e}")
        return None, None

    @staticmethod
    def sanitize_filename(filename):
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        filename = re.sub(r'[\s_]+', ' ', filename)
        return filename.strip()

    def get_download_links(self, title_url: str) -> list[str]:
        chapters_list, _ = self.get_chapters_list(title_url)
        return [x["download_link"] for x in chapters_list]

    def get_manga_id_from_url(self, url):
        match = re.search(r'/(\d+)-', url)
        if match:
            return match.group(1)
        return None

    def get_download_header(self, download_url: str) -> dict:
        return clone_and_update_header(self.__header, {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": download_url,
            "X-Requested-With": "XMLHttpRequest",
            "Origin": self.base_url
        })

    def get_download_session(self):
        session = requests.Session()
        __fill_cookies__(session=session)
        return session

    def get_download_response_and_file_ext(self, session: requests.Session, download_url: str) -> tuple:
        header = self.get_download_header(download_url)
        api_url = f"{self.base_url}/engine/ajax/controller.php?mod=api&action=chapters/download"
        news_id, chapter_id = download_url[download_url.rfind("/") + 1:].split("-")

        payload = f"chapter_id={chapter_id}&news_id={news_id}"
        link_resp = session.post(url=api_url, headers=header, data=payload)

        if link_resp.status_code != 200:
            print(f"\r  ✗ Ошибка API: {link_resp.status_code} для [#{chapter_id}]")
            return None, None

        json_data = link_resp.json()
        raw_url = json_data.get("data")

        if not raw_url:
            print(f"\r  ✗ API не вернул ссылку для [#{chapter_id}] (error: {json_data.get('error')})")
            return None, None

        download_url = "https:" + raw_url.replace("\\/", "/")
        response = session.get(download_url, headers=header, stream=True, timeout=60)
        content_disposition = response.headers.get('Content-Disposition')
        if content_disposition and 'filename=' in content_disposition:
            match = re.search(r'filename[=;"\']+([^"\']+)', content_disposition)
            if match:
                output_filename = match.group(1)
                return response, output_filename[output_filename.rfind('.'):]
        return response, None


def add_cookies_to_session(session, cookies_data):
    """
    Добавляет куки из словаря в requests.Session

    Args:
        session: requests.Session объект
        cookies_data: список кук в формате, который вы предоставили
    """
    for cookie in cookies_data:
        session.cookies.set(
            name=cookie['name'],
            value=cookie['value'],
            domain=cookie.get('domain'),
            path=cookie.get('path', '/'),
            secure=cookie.get('secure', False),
            rest={'HttpOnly': cookie.get('httpOnly', False)}  # Для совместимости
        )

    return session


def __auth__():
    print("Необходима авторизация")
    fucked_up_security.auth_async('https://com-x.life')


def __fill_cookies__(session: requests.Session):
    if auth_cookie:
        add_cookies_to_session(session, auth_cookie)
        print()
    else:
        __auth__()
        __fill_cookies__(session)
