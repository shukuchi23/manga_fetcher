import re

import requests
from bs4 import BeautifulSoup

zazaza_base_url = "https://a.zazaza.me"

base_header = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 YaBrowser/25.12.0.0 Safari/537.36"
}


def clone_and_update_header(header: dict, update_data: dict):
    copy = header.copy()
    copy.update(update_data)
    return copy


# отсюда попадаем на реальный сайт
def find_zazaza_url(title_name: str) -> str:
    header = clone_and_update_header(base_header, {
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": zazaza_base_url,
        "Referer": f'{zazaza_base_url}/search'
    })
    title_name = title_name.replace('×', "x")

    with requests.Session() as session:
        session.headers.update(header)
        session.get(url=zazaza_base_url, timeout=3000)
        search = session.get(url=f'{zazaza_base_url}/search/suggestion',
                             params={"query": title_name, "types[]": ["CREATION", "FEDERATION_MANGA"]}, timeout=30000)
        rez_lst: list[dict] = search.json()["suggestions"]
        lst_ = rez_lst[0]
        finded_name = lst_['value']
        # print(f'На сайте {zazaza_base_url} найдена информация о манге: "{finded_name}"')
        link_: str = lst_['link']
        rez_link = ""
        if link_.startswith("http"):
            rez_link = link_
        else:
            rez_link = f'{zazaza_base_url}{link_}'
        # print(f"Ссылка на сайт с главами: {rez_link}")
        return rez_link


replace_html_trash_pattern = re.compile("\\s{2,}")
replace_prefix_pattern = re.compile("\\d+\\s-\\s\\d+")


def numerate_chapters(chapters: list[str]):
    i = 1
    p = 10
    link_len = len(chapters)
    while p < link_len:
        i += 1
        p = p * 10

    return [f'Глава {j:0{i + 1}}.{r}' for j, r in enumerate(chapters)]


def parse_chapters(url):
    rez = []
    with requests.Session() as session:
        get = session.get(url=url, headers=clone_and_update_header(base_header, {"Referer": zazaza_base_url}))
        soup = BeautifulSoup(get.content, "lxml")
        for tr in soup.find("div", {"id": "chapters-list"}).find_all("tr", {"class": "item-row"}):
            item_title = tr.select_one("td.item-title")
            sub = replace_html_trash_pattern.sub(repl="", string=item_title.text)
            chapter_name = replace_prefix_pattern.sub(repl="", string=sub)
            if chapter_name and chapter_name[0] != " ":
                chapter_name = f' {chapter_name}'
            rez.insert(0, chapter_name)
    return rez


def get_chapters(title_name):
    url = find_zazaza_url(title_name)
    chapters = parse_chapters(url)
    return numerate_chapters(chapters)
