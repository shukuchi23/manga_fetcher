import asyncio
import os

from playwright.async_api import Response as AResponse, async_playwright

storage_state_file = 'browser_state.json'


def has_auth():
    if os.path.exists(storage_state_file):
        with open(storage_state_file, "r") as f:
            line = ""
            for x in f:
                line += x
            return '"name": "dle_password"' in line
    else:
        return False


async def auth_async(url: str):
    async def resp_pred(a_resp: AResponse):
        context_cookies = await a_resp.frame.page.context.cookies(a_resp.url)
        rez = False
        for x in context_cookies:
            if x['name'] == 'dle_password':
                rez = True
                break
        return rez

    async def onResp(lst, resp: AResponse):
        request = resp.request
        if request.post_data:
            if await resp_pred(resp):
                await resp.frame.page.context.storage_state(path=storage_state_file)
                lst[0] = 1

    async def close(resp: AResponse):
        page = resp.frame.page
        if page:
            if not page.is_closed():
                await page.close()
            try:
                await page.context.close()
            except BaseException as b:
                pass
            try:
                await page.context.browser.close()
            except BaseException as b:
                pass

    async with async_playwright() as p:
        browser = None
        try:
            browser = await p.chromium.launch(headless=False)
        except Exception as e:
            browser = await p.firefox.launch(headless=False, timeout=0)
        context = None
        if os.path.exists(storage_state_file):
            context = await browser.new_context(
                storage_state=storage_state_file,
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
        else:
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}};
        """)

        lst = [0]
        context.on(event="response", f=(lambda x: onResp(lst, x)))
        page = await context.new_page()
        await page.goto(url, wait_until='load')
        while lst[0] == 0:
            await asyncio.sleep(3)

        print("success")
        await p.stop()


if not has_auth():
    try:
        asyncio.run(auth_async('https://com-x.life/main/'))
        os.system('cls' if os.name == 'nt' else 'clear')
    except BaseException as ignore:
        pass
