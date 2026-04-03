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

```bash
python main.py
```


### Первый запуск

1. **Выберите браузер** (Chrome/Firefox)
2. **Авторизуйтесь** на сайте com-x.life в открывшемся окне браузера
3. **Дождитесь автоматического сохранения cookies** — скрипт продолжит работу автоматически

> ⚠️ **Важно!** Авторизация требуется только при первом запуске. Cookies сохраняются в файл `browser-state.json`


</div>

