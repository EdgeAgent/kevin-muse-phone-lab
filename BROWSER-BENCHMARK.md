# PhoneOps eight-browser benchmark

**Measured:** 2026-11-20T00:49:28+0000  
**Workload:** 8 simultaneous public website navigations, one isolated browser context per phone lane.

## Results

| Metric | Measured |
|---|---:|
| Parallel lanes | 8 |
| Wall-clock batch time | 2687.9 ms |
| Per-lane latency | 922.7 / 1943.9 / 2681.4 ms (min / avg / max) |
| Peak browser RSS | 2734.8 MB |
| Peak total PhoneOps RSS | 2851.4 MB |
| Browser process tree | 25 processes |
| Browser CPU | 410.7% of one core; 68.5% aggregate on 6 vCPU sandbox |

## Interpretation

The eight lanes completed successfully. The browser bridge uses one Chromium process tree with isolated contexts/pages rather than eight completely separate Chromium installations. The measured peak is approximately 341.9 MB of browser RSS per lane under this workload. Website response time is network-dependent; the slowest lane was 2681.4 ms.

These are sandbox measurements, not a guarantee for every Windows computer. Native Android AVD mode will consume substantially more RAM and CPU than this browser-only mode.

## Reproduce

```powershell
python benchmark_browser_farm.py
```

The raw machine-readable result is [`browser-benchmark.json`](browser-benchmark.json).
