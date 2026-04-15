<div align="center">

# manga_fetcher

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.7+-blue.svg" alt="Python 3.7+">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg" alt="Platform">
</p>
</dev>

<div align="left">

## 📖 Описание

Python-скрипт для автоматического скачивания манги с сайта **com-x.life** и **im.manga-chan.me**.

---

<dev align="left">

## 🔧 Установка

### Требования

- Python 3.7 или выше
- Google Chrome или Mozilla Firefox
- Аккаунт на com-x.life

### Linux

```bash
git clone https://github.com/shukuchi23/manga_fetcher
cd manga_fetcher
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# развилка с браузером(одно на выбор)
# если любишь хром
playwright install chrome
# если любишь firefox
playwright install firefox
```

### Windows (можете не использовать venv на ваше усмотрение)

```bash
git clone https://github.com/shukuchi23/manga_fetcher
cd manga_fetcher
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt

# развилка с браузером(одно на выбор)
# если любишь хром
playwright.exe install chrome
# если любишь firefox
playwright.exe install firefox
```

---

## 🚀 Использование

### Базовый запуск

Если Вам только и требуется, что скачать весь тайтл в формате **cbz**(Comic Book Zip), то смело выполняйте команду ниже.

```bash
python main.py
```

Если Вам не нравится формат **cbz**, то можно задать свой формат **архива**(zip, rar, cbr, ...).
Например, если все главы манги должны быть сохранены в архиве **rar**, команда будет следующая:

```bash
python main.py -e rar
```

### Использование

0. **Если вы только скачали программу, необходимо чтобы она создала файл ``browser-state.json`` (
   см. [Первый запуск](#первый-запуск-создание-файла-browser-statejson))**
1. **Введите название манги** — скрипт выполнит поиск введенной вами строки на сайтах манги, и предложит варианты
   для скачивания;
2. **Выберите один из предложенных вариантов** — введите номер, соответствующий вашей манге, если её нет, можно
   закончить работу с программой, введя '0';
3. **Ожидайте завершения программы**
4. **Читайте!** — Скачанную мангу можно найти в каталоге где лежит README.md в папке downloads/<имя_тайтла>

> ⚠️ Утилита работает по стратегии до качки: если вышли новые главы для уже скаченной манги, в `downloads/<имя_тайтла>`
> будет создан новый архив с припиской **__new_**. В этом архиве будут все новые(не скаченные ранее) главы манги.
>> ⭐ Все скаченные главы хранятся в файле ``downloads/<имя_тайтла>/chapter_list.txt``

#### Первый запуск (создание файла ``browser-state.json``)

1. **Откроется браузер с окном com-x.life** 
2. **Авторизуйтесь**. Если Вы не зарегистрированы на сайте, то это нужно сделать, т.к. без этого скачивание будет запрещено, а сайт хранит ну **ОЧЕНЬ** много тайтлов.
3. **Дождитесь автоматического сохранения cookies** — окно браузера закроется, и скрипт продолжит работу автоматически

> ⚠️ **Важно!** Авторизация требуется только при первом запуске. Cookies сохраняются в файл `browser-state.json`


</div>

