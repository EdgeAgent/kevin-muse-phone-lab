# PhoneOps per-phone browser operations

PhoneOps can give each local phone lane its own isolated Chromium session. Each browser lane has separate cookies, history, page state, URL, title, and screenshot output. This is for public web research, QA, browsing, and repeatable website checks. It is separate from native Android Chrome; native Android browser control becomes available when the Google Play AVD is installed.

## Easiest Windows setup

1. Extract the PhoneOps package.
2. Double-click [`Setup-PhoneOps-Web.bat`](Setup-PhoneOps-Web.bat).
3. The script installs Playwright and Chromium, then starts PhoneOps.
4. Open `http://localhost:8787`.
5. Select a phone in **Per-phone web browser**.
6. Enter a search query or website URL.

Use `Setup-PhoneOps-GooglePlay.bat` separately when you want native Android Chrome and Play Store inside a real AVD.

## Dashboard workflow

The web console has three controls:

- **Search web**: searches from the selected phone using DuckDuckGo.
- **Open website**: navigates that phone’s browser to a public HTTP/HTTPS URL.
- **Capture page**: saves a full-page PNG for that phone under `.kevin-runtime/browser-screens/`.

Example assignments:

```text
Phone One: search “mobile QA regression tools”
Phone Two: open https://www.python.org/
Phone Three: open https://github.com/
Phone Four: search “Android emulator performance testing”
```

## API examples

Search from Phone One:

```powershell
$body = @{ query = "mobile QA regression tools" } | ConvertTo-Json
Invoke-RestMethod `
  -Uri "http://localhost:8787/api/phones/kevin-01/browser/search" `
  -Method Post -ContentType "application/json" -Body $body
```

Open a different website on Phone Two:

```powershell
$body = @{ url = "https://www.python.org/" } | ConvertTo-Json
Invoke-RestMethod `
  -Uri "http://localhost:8787/api/phones/kevin-02/browser/navigate" `
  -Method Post -ContentType "application/json" -Body $body
```

Capture Phone Two’s current page:

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8787/api/phones/kevin-02/browser/screenshot" `
  -Method Post -ContentType "application/json" -Body '{}'
```

## Parallel website checks

Send a different website to each lane from Python:

```python
import concurrent.futures, json, urllib.request

base = "http://localhost:8787"
websites = [
    "https://example.com",
    "https://www.python.org/",
    "https://www.wikipedia.org/",
    "https://github.com/",
    "https://docs.python.org/3/",
    "https://developer.mozilla.org/",
    "https://pypi.org/",
    "https://www.ietf.org/",
]

def open_site(item):
    phone_id, url = item
    request = urllib.request.Request(
        f"{base}/api/phones/{phone_id}/browser/navigate",
        data=json.dumps({"url": url}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    results = list(pool.map(
        open_site,
        [(f"kevin-{n:02d}", url) for n, url in enumerate(websites, 1)]
    ))

for result in results:
    print(result["phoneId"], result["browser"]["title"], result["browser"]["url"])
```

## Safety boundaries

The browser bridge only accepts public HTTP/HTTPS websites and blocks localhost and private IP destinations. It does not automatically log in, purchase, publish, send messages, or change accounts. Keep human approval for sensitive actions and use test accounts for QA.
