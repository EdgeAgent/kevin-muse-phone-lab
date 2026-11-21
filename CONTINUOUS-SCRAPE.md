# Continuous eight-lane scraping

PhoneOps now includes an application-native continuous scrape loop for the eight local browser lanes.

## Current behavior

- Eight named phone lanes run simultaneously.
- Each lane has a different public HTTPS source.
- The browser navigates to the assigned source and captures the page into that phone’s screen.
- The dashboard refreshes every two seconds.
- The scraper repeats on the configured interval.
- The default interval is 60 seconds. The audited sandbox run used 30 seconds.
- Use **Auto-scrape: ON/OFF** to pause or resume the loop.
- Use **Full-screen wall** to expand the phone wall.

The default public sources are Example Domain, Python.org, Wikipedia, GitHub, Python documentation, MDN, PyPI, and IETF. Replace these with sources you are authorized to collect from and respect each site’s terms, robots rules, rate limits, and API policies.

## Configuration

Windows PowerShell:

```powershell
$env:PHONEOPS_AUTO_SCRAPE = "1"
$env:PHONEOPS_SCRAPE_INTERVAL = "60"
py server.py --port 8787
```

The server enforces a minimum interval of 30 seconds to avoid an accidental request flood.

## API

```powershell
Invoke-RestMethod http://localhost:8787/api/scrape/status
Invoke-RestMethod http://localhost:8787/api/scrape/start -Method Post -Body '{}'
Invoke-RestMethod http://localhost:8787/api/scrape/stop -Method Post -Body '{}'
```

## Native Android mode

The current sandbox audit reports Android SDK, emulator, ADB, and AVD availability as false. The continuous scraper therefore runs in the local isolated Chromium browser mode. It does not claim to be a native Android emulator.

For actual Android Chrome and Play Store screens on Windows, run [`Setup-PhoneOps-GooglePlay.bat`](Setup-PhoneOps-GooglePlay.bat). That workflow installs the Google Play system image, creates the AVD, and exposes the Android/ADB backend. It requires Android Studio or the Android command-line tools, enough disk space/RAM, and explicit SDK license acceptance.
