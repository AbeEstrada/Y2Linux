# Device-resident power qualification harnesses

Run on the Y2 from `/run/y2` (copied there over SSH; `/run` is tmpfs). They survive
USB removal because they run detached (`setsid nohup python3 ... &`) and write to
`/data/logs/power-final-02-*`.

- `suspend-session.py` waits for USB unplug, blocks Wi-Fi at runtime, runs 60 s and 300 s idle
  windows, the five staged pm_test stages and ONE bounded RTC suspend (backstop 30 s).
  Needs `suspend_platform_device.py` and `qualify-platform-v1-suspend.py` from
  `tools/development/` copied beside it, plus `power-screen.py` and `dac-readback.sh`.
- `battery-idle-session.py` Wi-Fi CAM vs FAST_PSP (5 min each) then 30 min radios-off.
- `dac-readback.sh`, `proc-rates.sh`, `power-press.sh` read-only probes (DAC rails, per-process
  wake rates, synthetic Power presses).

Take `/tmp/y2-platform-v1-device.lock` first. Never retry a suspend entry. Candidates for merging
into the existing `qualify-*` tools once the suspend stall is fixed.
