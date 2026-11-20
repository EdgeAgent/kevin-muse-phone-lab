"""Optional Playwright browser sessions for the eight local PhoneOps lanes."""
from pathlib import Path
from urllib.parse import quote_plus, urlparse
import ipaddress, threading, shutil
from concurrent.futures import ThreadPoolExecutor

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - optional Windows install dependency
    sync_playwright = None

class BrowserBackend:
    def __init__(self, runtime):
        self.runtime = Path(runtime)
        self.screens = self.runtime / "browser-screens"
        self.screens.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="phoneops-browser")
        self.playwright = None
        self.browser = None
        self.pages = {}
        self.meta = {}

    def _check_url(self, raw):
        value = str(raw or '').strip()
        if not value:
            raise ValueError('A website URL is required')
        if not value.startswith(('https://', 'http://')):
            value = 'https://' + value
        parsed = urlparse(value)
        host = (parsed.hostname or '').lower()
        if not host or host in {'localhost', 'localhost.localdomain'}:
            raise ValueError('Local and private websites are blocked by the browser bridge')
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address and (address.is_private or address.is_loopback or address.is_link_local):
            raise ValueError('Local and private websites are blocked by the browser bridge')
        return value

    def _ensure(self, phone_id):
        if sync_playwright is None:
            raise RuntimeError('Playwright is not installed. Run: pip install playwright && playwright install chromium')
        if self.playwright is None:
            self.playwright = sync_playwright().start()
            executable = shutil.which('chromium') or shutil.which('google-chrome')
            kwargs = {"headless": True}
            if executable:
                kwargs["executable_path"] = executable
            self.browser = self.playwright.chromium.launch(**kwargs)
        if phone_id not in self.pages:
            context = self.browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1)
            page = context.new_page()
            self.pages[phone_id] = (context, page)
            page.goto('https://example.com', wait_until='domcontentloaded', timeout=15000)
        return self.pages[phone_id][1]

    def _record(self, phone_id, page, query=''):
        text = ' '.join((page.locator('body').inner_text(timeout=3000) or '').split())[:240]
        meta = {"online": True, "url": page.url, "title": page.title()[:120], "query": query, "snippet": text}
        self.meta[phone_id] = meta
        return meta

    def _navigate(self, phone_id, url):
        with self.lock:
            page = self._ensure(phone_id)
            target = self._check_url(url)
            page.goto(target, wait_until='domcontentloaded', timeout=20000)
            return self._record(phone_id, page)

    def navigate(self, phone_id, url):
        return self.executor.submit(self._navigate, phone_id, url).result()

    def _search(self, phone_id, query, engine='duckduckgo'):
        text = str(query or '').strip()
        if not text:
            raise ValueError('A search query is required')
        base = 'https://duckduckgo.com/?q=' if engine != 'google' else 'https://www.google.com/search?q='
        with self.lock:
            page = self._ensure(phone_id)
            page.goto(base + quote_plus(text), wait_until='domcontentloaded', timeout=20000)
            return self._record(phone_id, page, text)

    def search(self, phone_id, query, engine='duckduckgo'):
        return self.executor.submit(self._search, phone_id, query, engine).result()

    def _screenshot(self, phone_id):
        with self.lock:
            page = self._ensure(phone_id)
            path = self.screens / f'{phone_id}.png'
            page.screenshot(path=str(path), full_page=True)
            return {"path": str(path), **self._record(phone_id, page)}

    def screenshot(self, phone_id):
        return self.executor.submit(self._screenshot, phone_id).result()

    def status(self, phone_id=None):
        with self.lock:
            if phone_id:
                return self.meta.get(phone_id, {"online": False, "url": "", "title": "Browser ready", "query": "", "snippet": ""})
            return {k: v for k, v in self.meta.items()}

    def close(self):
        def shutdown():
            with self.lock:
                if self.browser:
                    self.browser.close()
                if self.playwright:
                    self.playwright.stop()
                self.browser = None
                self.playwright = None
                self.pages.clear()
        self.executor.submit(shutdown).result()
        self.executor.shutdown(wait=True)
