# Device-resident power qualification harnesses

For DEEPSLEEP-FINAL-02, use **`deepsleep-clean-session.py`** after verifying
the installed source pair, USB/charging and taint zero. This collector checks
that exact identity and requires the captured boot ID. It takes a live
maintenance lock so automatic product sleep cannot race the owner helper
(which itself needs the activity lock). It also holds a durable product
quarantine through completion or failure, including resets. Clear that guard
only after the host has reviewed a real clean same-boot result; leaving it
pending would prevent the subsequent automatic-policy test.

The staged Power plan uses `--stages --wake power --alarm 300 --entry-after 180`
and schedules the one real entry against BOOTTIME. Prompt a short Power press
200 seconds after physical unplug. If the stage/archive deadline is missed,
the collector stops without a real entry. One-shot later trials omit `--stages`
and use an adequately long `--entry-after` for settling/archival. No retry is
automatic. Copy the current observer and qualifier beside the collector.
The older `deepsleep-single-session.py`/`deepsleep-endurance-session.py` require
tainted 04 diagnostic modules and must not be used unchanged on the clean image.

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
