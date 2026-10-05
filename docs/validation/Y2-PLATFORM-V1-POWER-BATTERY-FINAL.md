# Y2 Platform 1.0 power / battery investigation

2026-10-05. **IN_PROGRESS; MORE_WORK_REQUIRED.** The installed USB02 firmware has
confirmed software defects. A corrected kernel requires owner installation;
healthy-display, full-suspend and endurance qualification remain open.
The [machine report](data/y2-platform-v1-power-final.json) holds sanitized windows.
Private raw incident, network and media evidence stays ignored and is not exported.

## 1. INSTALLED FIRMWARE IDENTITY

| Item | Independently observed identity |
| --- | --- |
| Release | `1.0.0-platform-v1-usb-final-candidate.2` |
| Build | `Y2LINUX-PLATFORM-V1-USB-FINAL-02` |
| Kernel | `6.18.0-y2linux-platform-v1-usb-final-02` |
| Linux source | `0cb779267ca90740853dc02695166d75f36faa29` |
| Reborn source | `2444e0f65811e688250a8cd069a57dd780b2d6d3` |
| Root / Buildroot | `2025.02.18-platform-v1.26` / `2025.02.18` |
| API / feature contract / DATA / layout | 1 / 2 / 1 / 1 |
| Battery profile / low-battery policy | 1 / 2 |
| Loaded modules | `mediatek_drm`; power, audio and radios are built in |

SSH identity, persisted boots and the USB worktree's `usb-validation-02` manifest
agree. Fresh image hashes are BOOTIMG
`4fea3d1e0fac307d7cb444d38d560e0cbc4f29d5c4e6be574247dc6833047382` and Y2ROOT
`ab5a93da8a8642b587fd7eef50dbb76c2026825a90114145110e28b70c0587ce`.
Main and older baseline labels do not identify this installed image. Both dedicated
`codex/platform-v1-power-final` worktrees start at this exact pair. Yesterday's USB
transport, lifecycle, FIFO, DMA and responder queue changes remain inherited.
Manifest comparison and `git merge-base --is-ancestor` confirm both source ancestors.
The USB worktree remains at `0cb7792`; its uncommitted host benchmark, lab and
documentation work remains with the owner and changes no installed firmware source.

The 12-session campaign integrated CPU idle, suspend instrumentation/rollback,
USB/MTP, charging, radio workers, storage, GPU/input, Reborn performance, precision
observability, codecs and platform contracts. The installed USB02 descends from
that integration and subsequent baseline. Historical qualified UART01 C3 is kept
separate from current-image policy and endurance. Full resume was never promoted
by staged PM or source availability. Requested release documents, the 233-feature
matrix and newest subsystem reports were reconstructed before power modifications;
missing parallel-session/changelog/baseline-integration filenames map to the
actual final-session and baseline changelog records, not invented documents.

## 2. OVERNIGHT INCIDENT FORENSICS

The owner unplugged around 01:00, found the device dead around 09:00, and needed
wall charging to power it on. The preceding UI value was 88%, not a measured full
charge. Incident boot `6f2838c9-3b59-4320-b02f-1d02119a2359` records a declining
battery voltage and an orderly `shutdown_complete`, with no unclean boot.
The last retained low-voltage sample is **3.400268 V**, monotonic 22449.233 seconds.
This establishes a real voltage-floor shutdown, beyond a displayed 0%.
It does not establish battery-protection cutoff or a genuinely full starting pack.

The retained maximum is **3.920141 V**, `full=0`; no retained termination or sample
above 4.1 V establishes full charge. Voltage declines from approximately 3.8 to
3.4 V over six hours. Wi-Fi was enabled and associated, playback was paused, and
screen blanking was recorded. No full-system suspend occurred overnight. Exact
nighttime clocks, process activity, radio retries and C3 residency were not journaled.
Wall-clock/NTP jumps prevent assigning precise owner-local timestamps to all rows;
use monotonic differences. The retained SDP / 2000 uA USB allocation is a source
state, not pack current or proof contradicting physical cable removal.

The supported explanation is an incompletely evidenced starting charge followed
by hours of awake runtime idle with Wi-Fi and known recurring userspace/input work.
A concrete C3/PMIC slot defect also makes precharge reliability suspect, but the
last night lacks a matching register trace. Its exact energy contribution cannot
be retroactively measured. Battery degradation is not established.

A new bounded journal captures five-minute snapshots, coalesced state events,
immediate shutdown/suspend transitions, voltage, charging, radio/USB/backlight,
actual C1/C2/C3 counters, OPP counters, scheduler totals and runtime PM. It uses
existing safety samples, adds no timer, rotates two 256 KiB files, and never lets
write or lock failure disable battery protection.

## 3. BATTERY MEASUREMENT ARCHITECTURE

BAT0 voltage is a real MT6323 AUXADC measurement; absolute calibration has not been
checked externally. SOC is an estimate from filtered voltage. No validated pack
current, coulomb count or pack NTC temperature is exposed. BATSNS and ISENSE ADC
channels exist, but this board's shunt topology, value and offset are unproven.
Raw differential counts cannot be converted honestly to battery mA. PMIC die
and CPU die temperatures are distinct from battery temperature. Nominal capacity
is unknown; no repository label or verified stock capacity supplies a safe value.

## 4. CHARGER / MT6323 ARCHITECTURE

The built-in charger owns source classification, current-ceiling selection,
checked regulation/protection fields, ADC checks, engine sequencing, watchdog,
fault latching and voltage-limited hold/recharge. Its safety worker remains 1 Hz;
the hardware watchdog is four seconds, with a 2500 ms late-service fault.
USB provides an allocation, not measured current. Active charging holds a wake
source. Autonomous DORMANT PCM requests bypass normal regmap write validation,
so their PMIC-wrapper slots must point at VPROC before runtime C3 is admitted.

Primary field/sequence evidence is the pinned
[MT6582 vendor source](https://android.googlesource.com/kernel/mediatek/+/d53dd75c3ff77cac3f5be58fddfe660e94f94d64/),
plus exact stock Y2 disassembly retained in [the charging contract](../knowledge/m4-charging.md)
and [sensor acquisition](../knowledge/m4-battery-acquisition.md).
The vendor net-current/coulomb methods are stubs; a charger differential estimate
assumes a 68 milliohm shunt that has not been established on this Y2. Stock's
constant 25 C public temperature is not a measured NTC. Protections were never
experimentally bypassed or fault registers cleared to force charging.

## 5. SOC ALGORITHM

| Voltage, uV | Provisional percent |
| ---: | ---: |
| 3400000 | 0 |
| 3500000 | 5 |
| 3600000 | 10 |
| 3700000 | 25 |
| 3800000 | 45 |
| 3900000 | 65 |
| 4000000 | 80 |
| 4100000 | 95 |
| 4175000 | 100 |

The implementation filters over 30 seconds, requires 120 seconds of rest, uses a
15 mV deadband and 75 mV charging correction, and bounds movement to one percentage
point per minute. Charger Full with at least 4.160 V permits 100%. There is no
hard 88% cap in source. Voltage sag, relaxation, temperature, aging and unknown
capacity limit accuracy. The UI observation does not prove termination. SOC math
is preserved pending calibrated evidence; changing percentages cannot fix drain.
Reborn now reuses fresh same-boot protection-owner voltage, falling back to AUXADC
when the record is stale, absent or invalid.

## 6. SAFE CHARGING LIMITS

| Source / condition | Existing validated configured maximum |
| --- | ---: |
| SDP allocation at least 500 mA | 450 mA |
| SDP allocation 100–499 mA | 70 mA |
| SDP allocation below 100 mA | Inhibited |
| Detected DCP / CDP / eligible Apple source | 650 mA |
| Unknown eligible source | 70 mA |
| DCP deep-discharge / precharge | 450 mA |

CV stays **4.175 V**, independent upper guard **4.2 V**. Current, voltage,
temperature and low-voltage limits were not raised or disabled. A programmed
maximum is not measured actual charging or net battery current.

## 7. PC USB CHARGING

Current boot reports SDP, 500 mA USB allocation, 450 mA selected, Charging and
fault 0, with positive voltage trend and ECM/MTP available. This is a bounded
charging pass, not proof of actual mA or near-full termination. The first wall
fault stayed latched on PC reattachment until the one graceful diagnostic-module
removal/recovery reboot. The 1800.312-second PC window gained **3.881469 → 3.937500 V**, provisional
SOC **47 → 58%**, at the unchanged 450 mA ceiling with fault zero. CPU0 was online
throughout; C1 52492 entries / 6.2767%, C2 205957 / 85.7193%, C3 zero.
Recorded OPP residency was 90.605% at 598 MHz. IRQ rate was 164.046/s and context
switches 368.132/s. The original components were restored. Two brief SSH read
probes occurred; the frozen-display/C3-quarantined state prevents treating this
as optimized battery-only endurance or a matched after-fix result.

## 8. WALL CHARGING

| Bounded wall window | First | Second |
| --- | ---: | ---: |
| Duration | 300.620 s | 300.299 s |
| Source / selected maximum | DCP / 650 mA | DCP / 650 mA |
| C3 policy | Active | Automatically quarantined after DRM WARN |
| Voltage | Fell after fault | 3.701513 → 3.740185 V |
| SOC | Not a full-charge proof | 8 → 13% |
| Outcome | Protection fault 0x80 | Charging throughout, fault 0 |

In the first window, `CHR_CON0=0x62` at monotonic 1610.374 s loses HV-enable,
followed by verified charging inhibition. A matching read-only diagnostic module
found wider regulation-field losses. Fault protection worked; it was never bypassed.
The second test is a different boot and is an isolation observation, not matched
post-fix proof. Detached wall operation showed no enumeration dependency or
MUSB interrupt activity. Source current remains a configured ceiling.

## 9. CPU FREQUENCY

Governor `schedutil`; minimum 598000, maximum 1300000 kHz. Stats cover all five
OPPs: 598000, 747500, 1040000, 1196000, 1300000. Quiet PC windows predominantly
use 598 MHz. There is no evidence of a permanent overnight high-frequency/QoS
lock. Window frequency deltas are in JSON. OPPs and the existing voltage floor
are unchanged.

## 10. CORE PARKING

Natural hotplug parks secondaries after the existing adaptive post-burst hold.
Observer work can restore demand and prolong this hold. The second wall window
parked cores around 257/262/267 seconds. Endpoint online states and per-core wall
denominators are retained; no arbitrary forced offline or IRQ-affinity policy
was used.

## 11. C1

Real WFI entries occur in recorded windows. CPU0 in first wall window: 14426
entries, 83.5625% wall residency. Second: 7471 entries, 28.9026%.
Per-core values and exact denominators are in JSON.

## 12. C2

SLIDLE works. First wall CPU0: 1246 entries, 1.5491%; second: 18690 entries,
64.4756%. Existing restore guards remain. C1/C2 remain usable while charging
excludes C3; the charge watchdog does not require disabling C2.

## 13. C3

Implementation is present. The first wall window physically records CPU0 2554
DORMANT entries and 11.7177% residency. Historical UART01 65.245% is a different
image/workload. Current WARN boot records zero and remains quarantined.

The retained 480-word runtime PCM requests wrapper slots 5/6. Installed normal
CPU preparation initializes only slots 0–2; live slots 5–7 read **address 0,
value 0**. Full-suspend preparation would populate them, but runtime C3 does not
call it. These autonomous requests can address charger register 0 instead of
VPROC. The candidate initializes and reads back slots 5–7 to the active VPROC
bank with selector 72, retaining the verified **1.15 V** floor. Failed preparation
or voltage-owner checks close C3 admission. Source plus live readback proves the
slot defect; no PMIC bus trace proves every observed register loss resulted from it.
Physical after-fix proof is required.

## 14. C3 PRODUCTION POLICY

Installed USB02 fresh healthy boot: **Enabled, budget -1, state2 disable 0**.
It is not the historical fresh-boot budget-zero configuration. The incident boot
also logged startup Enabled. The later necessary reboot produced DRM WARN,
taint 512, and **Skipped / kernel_tainted_or_unknown / budget 0 / disable 1**.
That guard was respected. Candidate admission adds PMIC-slot readiness and
active-charger/watchdog exclusion; all UART, timer, topology, CONSYS, USB,
display, workload, deadline, context and CIRQ guards remain. Actual overnight
residency is unknown because the prior journal lacked those counters.

## 15. CPUIDLE BLOCKERS

| Blocker | Owner | Actual idle behavior | Fix / expected behavior |
| --- | --- | --- | --- |
| USB clocks | MUSB, ECM, configfs | Required when PC configured; detached off / no IRQ | Preserve current lifecycle and USB data |
| CONN / APDMA / BTIF | Shared CONSYS | Wi-Fi enabled owns clocks; radio off releases them | No invented clock gate; measure radio matrix |
| Core topology | Hotplug coordinator | Adaptive post-burst hold | Preserve demand restoration |
| Display warning | First DRM takeover | Stalled display quarantines C3 | Checked first-only inherited OVL stop; physical proof pending |
| Idle PMIC slots | PWRAP / SPM | Slots 5–7 uninitialized before runtime C3 | Initialize and verify active VPROC bank / 1.15 V |
| Active charge watchdog | Charger | Requires safe 1 Hz service | Explicit C3 exclusion; preserve C1/C2 |
| AFE / CS43131 | ALSA / codec | Paused PCM closed, codec suspended in healthy snapshots | Retain existing idle release |
| eMMC / SD | MSDC / source observer | Clock gate between requests; recurring UUID probes | Cache UUID using fresh mount and disk sequence identity |
| UART | UART PIO / SPM | Existing request / ACK ownership | Preserve bounded qualified handoff |
| Input | APT32F, keypad, GPIO keys | Wheel/keypad IRQ quiet; navigation polls at 50 Hz | Do not guess unsupported EINT routing |

Unknown owner states remain unknown; source availability is not hardware proof.

## 16. WAKEUP SOURCES

A unique whole-CPU wakeups/s counter is unavailable. `wakeup_sources` covers
system-suspend wake blockers, not every runtime idle exit. JSON separately keeps
IRQ rates, context switches, per-thread CPU, cpuidle entry/residency deltas and
available wakeup-source deltas. They are proxies, not battery mA or unique wakes.

## 17. IRQ OFFENDERS

Timer/IPI/scheduler activity dominates the retained short windows. Detached
MUSB interrupts were zero; untouched wheel/I2C0/keypad and inactive AFE show no
storm. JSON ranks per-window IRQ deltas. Hotplug can decrease per-core counters;
these discontinuities become unknown rates, never negative/overflow event counts.
More precise timer ownership requires healthy post-install windows.

## 18. USERSPACE POLLING

Matched component trials used PC-connected, radios-off, paused/dark 60-second
windows on the same WARN boot. The table measures thread context switches,
not uniquely attributable CPU wakeups or battery current.

| Offender | Before switches/s | Isolated after switches/s |
| --- | ---: | ---: |
| MTP receive thread | 49.7586 | 0 |
| Bluetooth reconnect main | 15.1216 | 0.1989 |
| Bluetooth reconnect GLib thread | 15.6356 | 0 |
| Reborn main | 20.1124 | Physical after measurement pending |

MTP now blocks on a signaled condition instead of 20 ms timeout polling, with
all cancel/stop writers signaling under the same mutex. Bluetooth watches a
private intent directory instead of unrelated `/run/y2/power.json` writes.
The sole reconnect owner is preserved. SSH uses passive rtnetlink and signal
wake descriptors, retaining its five-second readiness heartbeat and a 60-second
stable-address backstop instead of one-second `ip` subprocesses. Address changes,
child exit and shutdown still wake it immediately. No polling lab module ships.

## 19. REBORN IDLE

Before: main approximately 0.85% of one core / 20.11 switches/s; watchdog about
1.24%, with recurring source/voltage probes. The candidate waits up to one second
when paused/dark, 250 ms for lit static UI, 50 ms while playing, and 34 ms while
lit/dirty. Evdev, control and AVRCP descriptors wake it immediately; held keys
retain 15 ms pacing. AVRCP blocks on bus/state/shutdown descriptors instead of
200 ms polling. UUID caching is bounded to four fresh mount/device/diskseq keys;
card/CID/mount admission is still revalidated and failures are never cached.
Same-boot protection samples younger than five seconds avoid duplicate AUXADC.

A temporary ARM Reborn trial hit the pre-existing stalled DRM commit and its RPC
could not answer. There is no valid physical after window. The original binary
was restored and hash verified. ARM and workspace tests do not qualify actual
rendering, idle power or remote-command responsiveness on the device.

## 20. DISPLAY / GPU

The first healthy boot's dark state released scanout, Lima/MFG and backlight.
The recovery boot warned in vblank, then timed out in flip/commit/mutex paths;
the owner confirms black/frozen display even after brief Power. Taint 512 correctly
quarantines C3. DSI probe parks the loader stream and the mutex owner clears
membership, but installed OVL clock enable can leave loader EN=1, causing first
configuration to skip its required reset. The candidate stops and verifies OVL
and source layers only on first owned clock enable, then uses normal config/start.
No subsequent live-plane reset, timing/PLL/rail change or warning suppression.
Native clock/drop-write/non-Y2/subsequent-live-path tests pass; cold/warm physical
boot repair is **not yet proved**.

## 21. AUDIO / CS43131

Healthy paused/stopped snapshots show ALSA PCM closed, AFE/I2S clocks gated and
CS43131 runtime suspended. No temporary high-resolution lab module was installed.
Existing S16/44.1/48 paths, volume, buffering and codec PM rollback remain.
Retest audio idle/playback and post-full-resume restoration on the healthy candidate.

## 22. WI-FI

Incident Wi-Fi was enabled/associated and validly owned CONSYS. Nighttime scan,
retry and IRQ counts were not retained. Runtime off releases these blockers.
Campaign freshness, 30-second RSSI, inventory and DNS reuse are inherited. A
historical FAST_PSP trial was reverted to CAM and cannot count as proven savings.
Enabled/disconnected/connected battery-only comparisons remain open; no guessed
fullmac power mode, reconnect or keepalive changes were made.

## 23. BLUETOOTH

Off during isolated recorded windows, reconnect attempts/completions zero. The
measured wake load was unrelated directory notifications, not a peer retry storm.
The private intent directory reduces main to 0.199 switches/s and GLib to zero;
the actual native fixture preserves intent response. On/disconnected/connected
peer qualification remains open; an available headset is not assumed.

## 24. USB

Detached MUSB bus clock was off and its IRQ delta zero; the responder exits when
unplugged. Its PC-only 50 Hz receive polling therefore cannot alone explain last
night's disconnected drain. USB02 lifecycle, DMA/PIO, FIFO, ECM/MTP and 32 × 64 KiB
queue are inherited. The isolated wait fix passed a real KDE desktop **16 MiB
upload and download**, with device and returned SHA256
`84ebb5bc9e1e188628f3c87ff3c06906d45b775f2692555efc2be7deb7795696`.
Only the owned test file was removed. ECM/SSH returned in the same boot with
450 mA selected and fault zero. Original responder was restored and hash verified.
No competing desktop USB process was killed to force a libusb session.

## 25. STORAGE

Recurring UUID superblock probes every two seconds came from watchdog source
observations. The candidate caches only the UUID using freshly read mount/device/
diskseq identity; it preserves CID, mount and no-follow checks. Failed probes are
not cached. MSDC clocking, filesystem policy, database integrity and runtime PM
are unchanged. The persistent power journal writes at five-minute cadence in
steady state; no media rescan, forced cache drop or write suppression was added.

## 26. INPUT

APT32F is interrupt-driven, with an I2C read per valid data-ready IRQ. Untouched
wheel interrupts are quiet. Keypad and PMIC Power are IRQ-driven. Five GPIO
navigation buttons still use upstream `gpio-keys-polled` at 20 ms: a real **50 Hz
runtime-idle limitation**. Current pinctrl supports only established EINT lines;
exact navigation GPIO-to-EINT routing is not proven, and the pinned vendor GPIO
map is empty. No guessed remux or slower/lost controls. Qualified full suspend
would stop that runtime polling; held-key UI pacing remains responsive.

## 27. TIMERS / RTC

NO_HZ_IDLE and CPU_FREQ_STAT are enabled. GPT/local architectural timer/DORMANT
handoff remain. Required charge safety remains 1 Hz. Optional 20 ms MTP receive,
50 ms dark UI, 200 ms AVRCP and Bluetooth shared-directory work are addressed in
source. GPIO navigation at 50 Hz remains. The bounded audit collects endpoint
IRQ/softirq/context/OPP/idle/process counters without tracing during its interval.
Awake RTC alarm and full-suspend RTC wake are distinct acceptance gates.

## 28. FULL SYSTEM SUSPEND

Installed source includes campaign SPM context, BIU, normal PCM, timer and CIRQ
restoration, codec PM rollback/substep journaling and Reborn quiescence ACK.
Ordinary product sleep still refuses with `physical_qualification_required` or
`charger_active`. Overnight stayed in runtime idle indefinitely.
Historical Baseline02 RTC trial ended in watchdog reboot: DEVICES_RESUMING,
wake 0x20, PCM 596, reset stamp 0x59325253, unmatched CS43131 resume entry.
That is a failure, not same-boot resume. Current tainted/stalled-display boot is
unsuitable for new full sleep. After installation: freezer, devices, platform,
processors, core, then bounded RTC and Power wake with existing backstop. Require
positive actual residency, complete EXIT/restoration, same boot and working UI,
audio, USB, storage and radios. Automatic product sleep stays off until proven.

## 29. POWER-BUTTON POLICY

Paused short Power requests guarded full sleep and may only blank on refusal;
playing Power blanks, dark short Power wakes, long Power opens the shutdown
confirmation. Screen-off currently cannot promise deep sleep. No unqualified
five-/30-minute automatic suspend is activated. After repeated same-boot Power/
RTC success, add configurable paused-inactive sleep with playback, transfer,
update, scanner and unsafe charging exclusions. This investigation continues
through that gate after owner installation.

## 30. LOW-BATTERY POLICY

Independent floor **3400000 uV**; warning 3500000, recovery 3600000; five consecutive
one-second samples and ten-second grace. SOC alone cannot force shutdown. The
incident reached this actual voltage boundary and completed orderly shutdown.
The new journal retains reason and voltage. No lowered floor or intentional
protection cutoff/deep discharge was used.

## 31. BATTERY HEALTH EVIDENCE

Nominal/effective capacity is unknown and no pack-current integrator exists.
A verified full charge followed by controlled safe load characterization has
not been completed. There is no justified degradation diagnosis. Missing deep
sleep and software defects are real, but the exact fraction of overnight energy
explained is unknown. After software qualification, characterize normal idle/
playback with voltage, time, sag/relaxation and states, stopping before the
existing safety floor. Do not deliberately exhaust the pack.

## 32. BEFORE / AFTER POWER MATRIX

The machine report retains seven sanitized windows and raw-receipt hashes.
The long PC charge window is reported separately from the 60-second component
comparisons; its longer settling cannot be attributed to the candidate fixes.

| Same-boot PC comparison | Context switches/s | IRQ/s |
| --- | ---: | ---: |
| Original components | 383.11 | 259.87 |
| Only MTP wait fix | 289.54 | 211.70 |
| Only BT private intent fix; original MTP restored | 342.73 | 250.78 |

These are matched component comparisons, not a combined candidate or measured
battery current. Observer/hotplug constraints remain explicit. All healthy
final-build A–J states, 60-second and five-minute unplugged C3, playback, radio
peer and full sleep are pending. Different-boot wall tests establish association,
not an after-fix comparison.

## 33. LONG-IDLE RESULTS

Two five-minute wall windows completed: first faulted and voltage fell, second
charged with C3 gated. Optimized battery-only five-minute, 30-minute, two-hour and
overnight results are **NOT_RUN**. A PC charging window is a separate workload.
The audit uses approximately 0.62 CPU seconds of counter endpoint work in a
60-second interval (~1% of one core); approximately 1.8 CPU seconds of heavy
state descriptions are outside the counter window. It performs no scheduled
sampling during the declared interval. Longer intervals reduce endpoint bias.
Five read-only device trials of the journal counter collector averaged
**0.08886 CPU seconds** per due row (0.0296% of one core at five-minute cadence),
maximum encoded counter block 1847 bytes. This does not measure persistent-write
latency. No service was replaced for this collector measurement.

## 34. CHANGES MADE

Checked runtime PCM idle slots and readiness; active-charge C3 exclusion;
first mismatched protection-register diagnostics and correct callback context;
source-change-only USB supply notification; first-only OVL takeover;
signaled MTP receive wait; private Bluetooth intent watcher; passive SSH address
monitor; bounded persistent power/idle journal; duplicate ADC reduction;
Reborn workload-sensitive wait and AVRCP wake descriptor; identity-bound UUID
cache; endpoint-only power audit with discontinuity and observer accounting.
Main, installed images and yesterday's USB owner worktree remain untouched.

## 35. CHANGES REJECTED

No higher charging limits, lower voltage floor, forced protection-fault reset,
fabricated current/coulomb/capacity, unsafe 1.05 V idle selector, guessed pinmux,
forced core parking, taint bypass, unqualified autosuspend, wake-by-reboot success,
high-frequency journal or battery blame. Stock live comparison may later use
existing ADB; no original-firmware flash or SSH patch is required for this pass.

## 36. TESTS

Affected CPU/charger suite: 72 pass. Extended targeted suite: 146 cases,
145 pass / one emitted-kernel opt-in skip. Real charger callback/worker: four
pass after a review-caught context correction, with actual regmap identity checked.
Journal: six pass, including cumulative counters only when a row is due;
audit: two; display ownership: one; SSH/transfer: seven. MTP actual receive,
cancel, filesystem/protocol and native Bluetooth event fixtures pass.
Reborn `cargo fmt --all -- --check`, strict all-target workspace Clippy and
326 workspace tests pass. Prior failed receipts are retained and not called passes.
The final fresh source-bound kernel/modules/config/DT/ABI and ARM build pass.
The production profile has **498 cases: 487 pass, eleven locked-host dependency
skips**, all eleven covered by **59 passing native host cases**. Installed ARM/QEMU
imports cover 34 platform modules; SQLite, OpenSSL, null ALSA constraints, Reborn
defaults/library benchmark and codec contracts pass. ELF closure covers 384 files
and 1411 dependency edges. Package/privacy, inventory, legal-info collector and
source seal pass. The seal contains 451 source/license records and all successful
validation exit receipts. Legal-info warnings remain explicit; public distribution
is not asserted. Earlier cache-path/missing-input attempts are retained separately
and are not final passing receipts. The exact pinned source archives were used;
no parallel build output was substituted for the fresh rootfs.
Inherited vendor Wi-Fi warnings are retained; this pass does not rewrite that driver.

## 37. COMMITS

Implementation Linux `bff021e7dc5dc57ed4fe0a3d1ac527a252e6c639`, charger-context
correction `ffc1787e76c5b049e39ecbb8f4360c96322d60ea` and cumulative journal
`447bc9b4aaab12d68b6f8a2e0c52ab71eef15352`; compiled Linux
`fedc005ba68b3f5020a45258e38d641aa191b12a`; Reborn
`ccf450ac1388228dbd859318a05e13adf667c9aa`. Full compiled source pair is recorded
in candidate metadata; later documentation seal HEAD must not replace it.
Configured Git identity is preserved; no model attribution or push.

## 38. CANDIDATE / HASHES IF BUILT

Sealed owner-local candidate. Canonical destination:
`/home/luca/Dokumente/Code/Y2Linux/out/y2linux-platform-v1-power-final-candidate/`.
Build `Y2LINUX-PLATFORM-V1-POWER-FINAL-01`, kernel
`6.18.0-y2linux-platform-v1-power-final-01`, root `2025.02.18-platform-v1.27`.
One preserving BOOTIMG/Y2ROOT pair, no Y2DATA payload or reset.
BOOTIMG (7239680 bytes):
`716c686064764112310e0d1ef621d0308fafd4054650d57eb8b74d35e6fb2109`.
Y2ROOT (536870912 bytes):
`a23a03b8ee87492edca986b59e95b83ae41227204c7894a90df12245c822627d`.
SHA256SUMS, manifest, source archives, validation receipts and OWNER-HANDOFF
are included. The fallback is the exact installed USB02 BOOTIMG/Y2ROOT pair.
Use SPFT Download Only / preserving scatter, BOOTIMG and ANDROID only; DATA and
every other partition remain unselected.
The owner flashes; the agent does not. After confirmation, verify installed
identity and resume the pending matched matrix without restarting forensics.


Post-test restoration is verified on the same current boot: original Reborn, MTP,
Bluetooth helper and Python module match backups; saved Wi-Fi on is restored at
runtime; Bluetooth intent remains off; ECM/MTP Ready, charger fault zero, sole
loaded module mediatek_drm. DRM taint/C3 quarantine remains, not bypassed.
The supplied handoff contains the overnight procedure for use after five-/30-
minute and two-hour acceptance, and repeated same-boot RTC/Power success.

**Final verdict: MORE_WORK_REQUIRED.** The software candidate is complete and
needs owner installation. There is no claim that overnight drain, healthy
new-image C3, full resume or battery health is already qualified.
