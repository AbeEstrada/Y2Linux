# Y2 Platform 1.0 — final deep-sleep investigation

Investigation opened 2026-10-07; **IN PROGRESS, no readiness promotion**.
Latest boundary: owner-installed DEEPSLEEP-FINAL-01 has a USB enumeration and
charging regression. No clean successor suspend testing has begun. The defect
is reproduced in the actual clock/probe functions and corrected in source;
DEEPSLEEP-FINAL-02 is being validated. Preserve 01 as failed hardware evidence.
Owner target: real system suspend and approximately <=1 percentage point per
normal night if the hardware permits. Voltage/current safety policy and SOC
scaling are unchanged. No autonomous flash. Screen-off, runtime C1/C2/C3 and
whole-system suspend are separate evidence categories throughout this report.

Authoritative continuation: [newest handoff](../planning/NEXT-SESSION-HANDOFF.md),
then [boundary audit](../planning/roadmap-gap-audit.md#deep-sleep-continuation-admission--2026-10-07).
The handoff's earlier installed-device assumption is superseded by fresh SSH.
Private raw evidence: `out/deep-sleep-final/evidence/20261007/00-initial/`.
Archives and SHA256 receipts stay local; no private logs are published.

## 1. Installed firmware

Fresh exclusive-lock SSH, initial uptime 638.83 s, kernel taint 0:

| Field | Installed value |
| --- | --- |
| Release | `1.0.0-platform-v1-power-final-candidate.4` |
| Build | `Y2LINUX-PLATFORM-V1-POWER-FINAL-04` |
| Kernel | `6.18.0-y2linux-platform-v1-power-final-04` |
| Root | `2025.02.18-platform-v1.30`, Buildroot 2025.02.18 |
| Linux source | `5aeba051c428451483402e5874dcf8222afca259` |
| Reborn | `0.2.0`, source `8cd365da5f3454c8e3189df1434b966edbd06575` |
| Boot ID | `dbcb3854-d028-4882-94aa-cc86b5af091e` |

Installed metadata matches candidate 04 and its newest owner handoff; this is
not a readback hash of the installed partitions. Current Linux documentation
baseline `3e562e7` follows that implementation without changing it. Both working
branches are `codex/platform-v1-deep-sleep-final`. No stale power worktree used.
After the first idle collection, four userspace instrumentation files were
deployed with before/after hashes and a durable backup under
`/data/logs/deepsleep-final-userspace-backup-dbcb3854`. The kernel and Reborn
remain installed 04. Boot capture changes activate on the next boot; suspend
receipt calls use the improved journal immediately. No service was restarted
and SOC state was not reset for this deployment.

## 2. Overnight 88% → 30% incident

Owner observed ~58 displayed percentage points lost in ~6 hours on the most
recent tested night, then charged briefly and turned the device off. Do not
rewrite this account as an observed morning low-battery shutdown. Retained long
04 boot `74a4645d-de94-46c5-8457-8a46b01c6cc1` contains a ~6.72 h screen wake
and a later ~13.8 h low-battery shutdown, followed by charging/user-shutdown
boots. Exact local-time mapping is unavailable: the device uses build-floor
wall time and RTC was in 2022. Boot IDs and monotonic intervals are authoritative.

## 3. Retained evidence recovered after reboot

Archived `/data/logs`, `/data/system/platform`, prior CPU qualification,
Reborn logs/diagnostics/state and installed power/version configuration before
any trial. Successful raw archives: `retained-evidence.tar` and
`pstore-reborn.tar`, each with a SHA256 receipt. The failed initial compressed
archive attempt is retained as a failed command, not counted as evidence.

`/sys/fs/pstore` existed but was **unmounted**. Explicitly mounting pstore
recovered `console-ramoops-0` (222 bytes) and `dmesg-ramoops-0` (60,771 bytes).
Both were copied without deleting the kernel entries. Some bytes are visibly
corrupted; do not interpret damaged text as a trustworthy register value.

Current retained SRAM journal: `valid=0`, stage NONE, no previous device ring;
this does not prove there was no earlier warm-reset attempt. No persistent
journald exists; `/var/log` is volatile and BusyBox syslog persists under
`/data/logs`. Boot history, suspend receipt, power journals and Reborn JSONL
survived. Four invalid Reborn JSONL lines are preserved, not parsed as facts.

## 4. Reset / shutdown evidence

The long boot's power journal records five critical-voltage samples then
`shutdown_execute`, reason `low_battery`, near 3.400 V. Later charging boot
`7e94bd22-ea3f-41b7-ac2e-3e1726685403` ends with user poweroff.

The surviving panic belongs to the **later short user-shutdown boot**
`d1a8b50d-b525-4ff8-aaf8-e0d24dac97cb`: Power down at 88.82 s,
`mt6323_do_pwroff` warning at 89.82 s, “Unable to power off system”, then
“Attempted to kill init” panic at 90.82 s. It is a separate poweroff defect,
not evidence that suspend panicked during the six-hour window. Boot journal
`shutdown_complete` proves userspace shutdown preparation, not electrical off.
RGU raw status zero / `none_reported` is inconclusive, not proof of a power-on reset.

## 5. Battery voltage / SOC interpretation

Retained system log has 690 consecutive minute-spaced discharging-voltage samples,
from 3.900146 V at 8,281.84 s (~2.3 h) to 3.403564 V at 49,621.84 s; the final
battery journal then reaches ~3.400 V near 49,670 s. Around the observed
morning wake, voltage is ~3.74–3.76 V. Charger source/current allocation are zero
and faults zero in these rows. This is actual depletion; SOC imperfections
cannot explain away the sustained voltage decline. No measured battery mA exists.

Power JSONL rotation lost the starting 88% row. Surviving long-boot rows cover
38,899.8–49,674.6 s: 3.576928 V / 9% to 3.399609 V / 0%. Initial 88% voltage,
charge termination and exact six-hour endpoint cannot be recovered from these
rows. Voltage under load is not a calibrated capacity measurement.

![Retained runtime-idle voltage decline, with missing early samples marked](data/y2-deep-sleep-retained-voltage.svg)

The [voltage-only CSV](data/y2-deep-sleep-retained-voltage.csv) retains source
line numbers; [provenance](data/y2-deep-sleep-retained-voltage.json) records the
private source-log hashes. No missing 88% voltage or local timestamp is invented.

## 6. Normal product power policy

Installed `sleep.request()` always refuses with `charger_active` or
`physical_qualification_required`; there is no ordinary auto-suspend transition.
Paused short Power attempts that guarded request, then blanks the screen after
refusal. Playing short Power blanks. Dark short Power wakes the display; long
Power presents shutdown confirmation. Screen-off remains runtime idle at
1/5/30 minutes and hours. Full sleep is only the explicit owner helper.
Thus the product does not enter full suspend overnight by itself.

## 7. C1

Long-boot retained 10,774 s interval: CPU0 WFI ~5.92% residency. Current 60.30 s
unplugged window: CPU0 WFI 98.60%, four CPUs online, C2/C3 zero. The following
300.28 s window transitions from four CPUs to CPU0 only: WFI 37.65%. A secondary
CPU's endpoint WFI delta exceeds wall time across hotplug; that secondary
residency is invalid, not >100% useful residency.

## 8. C2

Same retained interval: CPU0 SLIDLE ~85.57%. This is runtime idle with Linux
services and timer wakes, not whole-system sleep. Current five-minute window:
SLIDLE 2.98% (2,403 entries).

## 9. C3

Long-boot cumulative DORMANT usage and time remain **zero**, including the final
snapshot. Therefore this boot never entered C3 before the observed endpoints.
The clock veto is PERI `1024` = bit 10, the USB bus clock. Radio, display/GPU,
audio and storage runtime states do not explain that particular clock bit.
Current five-minute post-USB-detach window: DORMANT **55.82%, 8,301 entries**,
without changing policy. USB bus gate is verified off, failures zero; early
window includes SMP residency before automatic CPU parking. The owner reattached
USB after ~21 minutes, interrupting the thirty-minute window. Only 60 s/300 s
are valid complete windows from that first collection. The later complete
30-minute follow-up is recorded in section 10 with its diagnostic taint explicit.

## 10. C3 normal-boot policy

Current and retained normal policy: Enabled, budget `-1`, C3 disable `0`.
No manual enabling was done. This is an entry veto, not a disabled production
policy. Source establishes a missing clock owner on a no-cable cold boot:
USB probe enables its bus clock, but registers a MUSB child only after a valid
data-source attach. Without a child there can be no child runtime suspend to
release that clock. After an actual USB session, detach follows a different
path. The running unplugged test deliberately measures that distinction.

### Complete thirty-minute runtime observation

`20-idle30-return/` completes **1800.282208723 s** without SSH, playback, scan,
USB or radios. Screen remains off, same boot `404ef43c...`, no system suspend
requested. External context/retained-console modules remain loaded (taint 4096),
so this complements rather than replaces the earlier untainted baseline.
CPU0 C1/C2/C3: **37.6814 / 2.0512 / 56.7212%**, entries
19,315 / 13,095 / 49,755. CPU0 idle exits 45.6401/s. CPU topology changes 0–3→0,
so per-IRQ whole-system rates are unknown; `/proc/stat` totals remain valid:
**77.2957 interrupts/s, 136.3142 context switches/s**. CPU0 IRQ lower bounds:
GPT 34.8057/s, architectural timer 12.6825/s. 598 MHz residency 98.1814%.
BAT0 active/event +30, wakeup_count +0; other registered sources unchanged.

Fresh voltage **4.062963→4.030664 V**, −32.299 mV; daemon SOC **91→85%**.
Separate daemon ADC samples 4.054614→4.032202 V; never mix these with the fresh
endpoint series. Charging relaxation is still a limitation. This independently
shows the estimate can exceed 88%; it does not recover the missing start-of-night
charge/voltage record. Primary worker switch rates: events_freezable 27.6168/s,
RCU 7.2516/s, secondary freezable worker 5.3486/s, charger 4.8115/s,
idle-demand 2.6263/s, power daemon 2.2646/s, audio 2.2346/s, Reborn main 2.1486/s.
These are context-switch rates, not asserted unique hardware wake rates.

Raw SHA256: first-return.json `dfdb28df8d516397a88c21acae643fc2420240b7278390649bdba248aec1eca3`;
retained-sysfs.tar `6cd92d9777db9a8bf1561126d66446bf4b73f4df35caa9065da0ea4b87ecba00`;
persistent.tar `f76b664ca24895a744202475a0449ae54f59393796d94b0ed7267705f576686f`.

## 11. Wakeup sources

Current five-minute window: 79.00 total IRQ/s, 138.65 context switches/s;
registered wakeup sources show BAT0 event/active count +5 (periodic notification),
all wakeup_count deltas zero and other sources unchanged. Kernel endpoints do
not expose independent unique CPU wakes; do not relabel context switches as
measured wakeups. C3 did enter despite these runtime events.

## 12. IRQ offenders

| Five-minute IRQ source | CPU0 lower bound/s | Interpretation |
| --- | ---: | --- |
| IRQ24 / SYSIRQ112 `timer@10008000` | 38.45 | GPT clockevent, including scheduled work; exact worker attribution below |
| IRQ25 arch timer | 14.19 | CPU0 clockevent; other CPU columns disappear during hotplug |
| IPI3 function call | 1.95 | CPU0 interprocessor work |
| IPI5 IRQ work | 1.62 | CPU0 IRQ work |
| IRQ221 / SYSIRQ40 `11240000.mmc` | 0.96 | SD host |
| IRQ220 / SYSIRQ39 `11230000.mmc` | 0.55 | eMMC host |
| USB, AFE, Wi-Fi/BT, input, RTC | 0 | No CPU0 IRQ delta in this window |

Reanalysis preserves the original raw endpoints and records a new
`B300-hotplug-aware-summary.json`. The CPU header changes from four CPUs to one:
subtracting aggregate columns can silently undercount even if the difference is
positive. Whole-system per-IRQ rates are therefore unknown for this window;
the table reports common CPU0 counters only. `/proc/stat` total IRQ/s remains
valid. The unchanged-header 60-second window has whole-system arch timer
59.75/s, GPT 24.76/s, function-call IPI 10.51/s, SD 0.96/s, eMMC 0.83/s.

The earlier all-core 60 s window had arch timer 59.75/s, GPT 24.76/s,
function-call IPIs 10.51/s and total IRQ 97.91/s. CPU parking therefore matters.

## 13. Userspace offenders

Retained Reborn log: paused startup, dark screen except brief user interaction,
no overnight scan/playback activity. Installed 04 includes the earlier blocking
connectivity supervisor fix. Current five-minute context-switch ranking:
freezable CPU0 worker 30.29/s; RCU 7.42/s; CPU2 worker 6.25/s; charger worker
4.81/s; idle-demand worker 2.61/s; power daemon 2.40/s (~1.14% one CPU);
Reborn watchdog 2.05/s, playback 2.01/s, audio 1.99/s. Other workers remain in
the raw endpoint audit. These are context-switch rates, not unique wake counts.
Source review finds database/scanner one-second receive-timeout loops and
paused audio/playback timer waits; exact fixes and remeasurement remain pending.

## 14. Audio / DAC power

Installed 04 includes idle-bias-off fix. Current same-boot readback after cable
return: PCM closed, codec and AFE runtime suspended, all three DAPM biases Off,
GPIO15/18/20 output low, audio/AFE bus clocks count zero, AFE IRQ count zero.
The upstream VGP2 audio supply has enable count 1 at 1.8 V while downstream
DAC enables are off; do not claim every analog supply is electrically off.

## 15. Display / GPU power

Retained dark-state runtime records report suspended display/GPU; collector
records current backlight, runtime PM and process counters. Full-resume display
and input qualification remains separate.

Both endpoints of the complete 30-minute runtime window have `bl_power=4`,
Lima `13010000.gpu`, OVL, RDMA and `mediatek-drm` runtime suspended. Brightness
32 is the saved level, not proof the backlight is on. No screen-off rendering
loop is present in Reborn's draw admission. Owner-observed Power resume restores
the display/input; repeated clean-successor coverage remains.

The endpoint clock summary still owns UART (26 MHz), GPT system clock (13 MHz),
26-MHz parents/keypad/PWRAP/efuse and AXI/thermal/AUXADC. These are awake runtime
observations, not measurements during SoC sleep. SPM requests and verifies UART
sleep acknowledgement, but current full suspend deliberately retains
infrastructure/DDRPHY; it does not claim deepest infrastructure power collapse.
The autonomous thermal monitor retains its clocks and protection. The VGP2
audio parent is also always-on in DT. Quantifying these remaining electrical
costs requires the longer voltage observations or a real external current
measurement; software enable counts cannot establish mA or a 1% hardware floor.

## 16. USB power

**Successor 01 regression:** owner installed the sealed pair, reports Reborn
running and Wi-Fi connected, but neither USB enumeration nor charging works.
Host sees preloader at 21:22:01 UTC, disconnect at 21:22:42, then no normal USB
device/interface. USB SSH times out; production SSH is USB-bound, so Wi-Fi does
not provide an alternate listener. Owner saved Export Diagnostic Report before
a single unplug/replug, which did not recover USB. Exact on-device version and
failure registers await transport recovery; host archive is
`25-successor-usb-enumeration/`.

The exact source defect is an omitted cross-owner transition. CCF initializes
USB with `inherited=true`; `y2_disable()` preserves that loader clock until
`y2_ccf_usb_claim()`. Previously only MUSB initialization claimed it. The new
childless worker gates before MUSB exists, so `clk_disable()` leaves hardware
on, gate readback fails -EIO, and `y2_usb_finish()` terminally stops USB. Later
BC1.1 cannot acquire its PHY; charging stays inhibited without changing limits.
The earlier tests mocked clock-disable as unconditional and missed the inherited
state. A new native regression combines the actual USB probe and actual CCF
callbacks, reproduces the pre-fix failure, and passes with the fix.

The correction claims CCF ownership after existing verified idle-DMA/digital
recovery and successful PHY mapping, before first worker scheduling. All failed
or incomplete recovery paths keep inherited protection. There are no new MMIO
sequences, relaxed safety masks or charger limits. A corrective candidate has
new DEEPSLEEP-FINAL-02/root v1.32 identity; do not qualify or reinstall failed 01
as though its software profile established physical USB behavior.

Uninstalled source fix adds one verified bus-clock gate/restore owner shared by
childless lifecycle, BC1.1 and child registration. Existing MUSB DMA/FIFO/session/
IRQ guards remain intact. Gate/readback failure is terminal and cannot become
false C3 admission. 32 targeted native tests pass; physical cold-no-cable proof
requires a matching new kernel. No cable-present result is called battery-only.

The same fix set now removes the detached worker's four-per-second poll.
Verified cable absence parks it; the charger's existing `y2-usb-presence`
notifications wake it on cable/source transitions. Attached sessions and invalid
PMIC observations retain bounded polling and terminal fault handling. Battery
sampling and gadget-budget notifications do not wake the parked worker. Role
changes and PM completion request a fresh observation; failed PM preparation
restores monitoring. Native event/filter/fault tests and ARM usb.o pass. This
is source validation; no post-fix physical wake-rate reduction is claimed yet.

## 17. Wi-Fi power

Retained long boot has Wi-Fi off; current initial controller powered 0/functions
0. Collector uses runtime-off preserving saved intent. Installed policy also
parks Wi-Fi after five dark/paused/battery minutes; associated radio drain is
not the retained long-boot explanation.

## 18. Bluetooth power

Retained health reports off, current controller functions 0. Rfkill unblocked
alone does not mean controller powered. Collector requests runtime-off and
restores saved intent afterwards.

## 19. Storage power

Retained eMMC/SD runtime states suspended. Current audit captures clock/runtime
and IRQ deltas; full-resume filesystem progress remains an open distinct gate.
No storage partition/raw write performed.
The complete runtime window confirms both MSDC hosts suspended at both endpoints.
After the focused Power return, ordinary filesystem tests sync and read back
262,144-byte files on internal data and SD with matching hashes; five-second
PCM playback advances normally before being paused/closed. This is narrow
functional restoration, not long-term storage endurance or raw-partition writing.
The SD slot declares `broken-cd`, so `mmc_rescan()` schedules its detection work
at HZ (once per second). This is an identified periodic source; the complete SD
IRQ rate cannot be attributed to that timer alone without a dynamic trace.

## 20. Input power

Installed-source navigation GPIO polling is 20 ms; APT32F wheel is interrupt
driven. Freezable-worker context-switch rates are measured above, but are not a
per-function wake count. No speculative pinmux
change made to turn unqualified pins into IRQs.

## 21. Full-suspend original failure

Newest retained 02 trial returned from SPM and completed device resume. Final
successful breadcrumb: **TASKS_THAWED**. Next expected: **FILESYSTEMS_THAWED**,
then POST_SUSPEND_NOTIFIED, CONSOLE_RESTORED, EXIT and Reborn restoration.
Backstop reset is a failed resume, never a pass. Removing SD did not cure it.

## 22. Root cause

Runtime C3 regression: childless USB bus-clock ownership gap, supported by
retained bit-10 veto and source. Physical correction still pending.
Full-suspend post-thaw wait: reproduced on installed 04 after all five staged
tests passed. Real entry began at monotonic 2752.85 s on boot `dbcb3854...`.
After CPU reset return and all device callbacks, retained sequence 156 is
TASKS_THAWED, error 0; ring ends at monotonic 2757.226 s. The expected next
mark is FILESYSTEMS_THAWED. Neither the 3 s nor 15 s deferred sampler ran.
`freeze_filesystems=0` before entry, but **the Linux 6.18.0 conditional is
inverted**: this value actually freezes all eligible filesystems. This
corrects the initial assumption that zero meant no ordinary filesystem freeze.
Upstream fixed it in commit `222047f68e8565c558728f792f6fef152a1d4d51`, stable
backport `b107196729ff6b9d6cde0a71f49c1243def43328` (CVE-2025-71106).
The exact one-line backport is now included in overlay 0066. Native execution
of the patched callback proves ordinary filesystems are untouched by default,
explicit opt-in freezes them, and FS_POWER_FREEZE filesystems remain protected.
Source: [upstream-authored stable backport](https://github.com/gregkh/linux/commit/b107196729ff6b9d6cde0a71f49c1243def43328.patch).
This inversion exposes the filesystem-thaw I/O path; it does not by itself
explain the missing timer interrupts. New boot
`697282e9-b617-444a-bafd-baa5596f2b70` proves
failure to resume the same boot. The 30 s backstop was armed, but RGU status
reads zero, so no hardware reset-cause bit independently attributes the reset.

All returned evidence is archived under `03-suspend-return/`. The early-boot
retained archive captured PM before services, with no capture errors and no
pstore deletion. Pstore still contains the older, partly corrupted poweroff
panic, not a fresh panic from this suspend. Console loglevel was 3, which
suppresses informational resume lines and scheduler stack output from console
capture. A matching optional module now observes timer registers at CPU/system
resume and prints bounded suspender/blocked-task stacks; a separate diagnostic
trial raises console verbosity and records external-module taint 4096. That
trial cannot count as clean product qualification.

The next RTC-only diagnostic also reset, to boot `a9007f1a...`. Its recovered
console (`05-diagnostic-return/`) records **two CPU_PM_ENTER notifications**
and two CPU_PM_EXIT notifications in one real suspend. The SPM timer reports
844,496 ticks at 32,768 Hz (25.77 s asleep); the requested RTC alarm was 30 s
from programming, before preparation. Resume again stops at TASKS_THAWED,
sequence 227, monotonic 449.119 s. Even the one-second syscore sampler never
executes. No fresh kernel panic was recovered.

The duplicate context owner is exact: Linux `cpu_pm_syscore_ops.suspend`
already calls CPU/cluster PM entry. `y2_spm_enter()` calls them again **after
`y2_cirq_begin()` masks every device SPI except SPM**. GIC has one
`saved_spi_enable[]` array, so the second save overwrites the original mask.
Platform exit first restores that masked state, then CIRQ restores the original
mask. Later core `syscore_resume()` restores the overwritten mask again,
disabling storage and GPT interrupts. This explains both the first thaw-I/O
wait and the missing timer-driven diagnostic. The CPU PM API explicitly forbids
another entry before exit. A bounded diagnostic suppressing only that nested
notification pair was armed; subsequent complete returns are recorded below.

That comparison encountered an earlier device-phase stall during its preliminary
`core` test, before any core CPU PM entry. Recovered boot is `404ef43c...`;
sequence 235 is DPM_PREPARED. The final device-ring entry is a successful
`11008000.i2c` suspend return at 623.088 s; CS43131 and both MMC device callbacks
also completed. No real SPM entry was attempted, so this is **not** a negative
test of the context fix. Ramoops ends at console suspension, hiding the scheduled
stack capture. The next single bounded diagnostic uses the standard
`console_suspend=N` option to retain stacks if that earlier wait recurs. This
can retain UART power and is excluded from drain/clean-product qualification.

**Controlled correction: first complete RTC resume.** On boot `404ef43c...`,
the next core test and one real RTC trial both returned. The original GIC
enable banks were `2000ffff,00000000,00043181,00000180,00330110,23000000,0200fc00`.
The suppressed nested save saw only `2000ffff,0,0,0,00200000,0,0`, proving the
second save would overwrite device enable bits. After core restore the banks
match the original exactly. Both notification depths return to zero. PM reaches
COMPLETE, sequence 313, error 0, with one SPM entry/resume, no abort and no
restore failure. RTC child IRQ advances, the alarm clears, and Reborn restores.
SPM counts 847,765 ticks = 25.872 s; the boottime-minus-monotonic proxy is
26.260 s. This is an actual deep-suspend/same-boot diagnostic success, not a
clean qualification: external-module taint 4096 and console-debug mode remain
explicit exclusions in the unchanged verdict.

Evidence: `09-console-return/`, including raw captures, result and strict
verdict. Subsequent 262,144-byte synced internal/SD scratch files read back
with matching hashes and were removed. Reborn resumed playback for five
seconds, PCM was RUNNING with hardware pointer advancing, then closed on pause;
XRUN/decode/playback errors remain zero. Original position and volume restored.
The earlier device-phase stall remains unresolved. A repeated-cycle batch uses
normal console suspension; a companion diagnostic only reactivates the RAM
console after a four-second stall so the existing stack sampler can be retained
without changing UART PM. The installed kernel cannot unload modules, so the
companion avoids discarding the successful boot merely to replace a probe.

`11-cycle-return/` then captures a successful core test and **four additional
real same-boot RTC returns with console_suspend=Y**. SPM residence ticks are
838,247 / 839,439 / 841,701 / 1,832,680 (25.58 / 25.62 / 25.69 / 55.93 s).
Every real trial has one entry/resume, RTC child IRQ +1, Power child IRQ +0,
COMPLETE/error 0, Reborn restored and all three ext4 error counters still zero.
The last trial was intended for Power; its actual wake was the RTC fallback.
Owner presses occur after that receipt (later Power count 12), not within its
recorded wake interval. The batch stops, and the five-minute trial never starts.

The batch's Power scheduling used CLOCK_MONOTONIC, which excludes the preceding
suspend residence; the first host prompt was therefore early. A corrected
prompt was sent, but exact physical press times were not supplied. Neither
the UI response nor the RTC fallback is claimed as Power-wake proof. The
collector now schedules owner gestures against CLOCK_BOOTTIME, and a separate
one-shot Power trial uses a five-minute fallback without earlier cycles.
USB returned at host 18:48:55 UTC, after this batch had already finished.

## 23. Fix

USB clock lifecycle fix is built into the successor, not yet installed.
Persistent journal now retains two 2 MiB
files at unchanged five-minute/event cadence, reads actual suspend receipt,
and records monotonic/boottime for residence attribution. Early boot mounts
pstore and archives bounded raw pstore plus retained PM before services, keeping
eight private boot archives without clearing pstore. SOC scaling and charging
limits are unchanged; the separate elapsed-time reporting correction is in §33.
The full-suspend source now removes the nested CPU/cluster PM pair. Core PM
alone owns the full-suspend save/restore. A built-in syscore resume callback,
registered after core CPU PM, restores/replays CIRQ after the GIC restore;
entry-abort paths also balance CIRQ. Runtime C3 keeps its separate valid CPU PM
ownership. Actual-function native tests cover success, entry refusal, CPU
suspend failure, early vector/CIRQ failure and restore quarantine; ARM spm.o
compiles. This source is not installed yet. Poweroff remains a separate defect.

## 24. Power wake

FAIL for the first current real trial: owner reported reboot after the short
press and boot ID changed. The requested Power prompt was 36 s late, adjacent
to the RTC fallback, so wake-source attribution is additionally inconclusive.
SPM EINT wake bit 0x20 cannot distinguish the RTC and Power PMIC children.
Same boot, child-IRQ attribution, restored display/input/storage/audio/Reborn
and repeated cycles remain required.
The next intended Power cycle returned successfully via RTC before the physical
presses; Power routing is not evaluated by that result. A subsequent USB return
after 18 seconds was refused during device prepare (-16), with no actual sleep.

**Focused Power wake succeeds** in `15-power-return/`: same boot `404ef43c...`,
Power child IRQ 24→26, RTC remains 5, alarm cleared, COMPLETE sequence 605,
error 0, Reborn restored and all ext4 errors zero. SPM reports 1,485,987 ticks
(45.349 s), boottime-minus-monotonic proxy 44.591 s. Owner observes normal
screen return. No reboot. Normal console suspend is enabled; matching-module
taint 4096 remains, so this is diagnostic proof, not clean release acceptance.

## 25. RTC wake

First complete same-boot RTC wake now observed with the context diagnostic:
alarm programmed/armed, SPM EINT wake, RTC child IRQ delta, alarm cleared,
kernel/helper/Reborn restoration complete. Alarm-clear fields in these older
receipts are **after explicit fallback cleanup**; automatic driver disarming
was not independently sampled. The updated observer captures pre-cleanup RTC
state for the next endurance trial. Five more RTC returns now repeat
with normal console suspension, including the 305.85-second measurement. Untainted successor qualification remains.

`22-endurance30-return/` adds two 600-second-alarm RTC cycles. Both show
`alarm_IRQ: no`, `alrm_pending: no` and empty wakealarm **before cleanup**,
plus RTC child IRQ delivery and same-boot completion. Thus automatic one-shot
disarming is now directly observed. A third cycle wakes early on USB insertion
while its future alarm remains armed; that is not an RTC-wake test or failure
to disarm a fired alarm. The collector clears that unused fallback and stops.

The complete repeat in `24-endurance30-repeat-return/` adds four attributed
RTC returns. Every alarm is disabled before cleanup, each IRQ reaches the
same-boot resume path, and all kernel/helper/filesystem checks pass except the
explicit external-module taint exclusion. This is repeatable diagnostic proof;
the built-in successor remains untested.

## 26. Same-boot resume

Fourteen complete real-suspend diagnostic returns on boot `404ef43c...`,
preserving the original Reborn process/session: twelve RTC, one Power and one
USB wake. The USB return fails its intended RTC/duration criterion. These
returns do not convert earlier backstop reboots into passes or remove the
remaining clean-image qualification gate.

## 27. Suspend cycle test

Freezer, devices, platform, processors and core: **5/5 PASS**, same boot,
taint 0, helper return 0, complete PM exit and unchanged zero ext4 error counts.
No SPM entry/resume delta during these staged tests. The core test's 4.27 s
boottime-minus-monotonic delta reflects timekeeping suspension during its busy
test delay, not real SoC sleep. The subsequent single real trial failed after
TASKS_THAWED. No automatic retry occurred.

Diagnostic follow-ups: one original-path RTC failure; one preliminary core
device-phase failure (no real attempt); then **1/1 complete real RTC return**
with nested context suppression and console debugging. The next batch returns
core + three RTC + the intended Power cycle on the same boot. Its actual wake
is RTC, so the wake-source check fails and no five-minute trial is attempted.
Total corrected-context real returns: **5/5 same boot**, all RTC; external
taint still excludes all five from clean release qualification.
The focused Power trial adds one attributed same-boot success: **6/6 actual
returns** (five RTC, one Power). The separate early-cable refusal never entered
SPM and is excluded from that denominator. The five-minute RTC trial adds the
seventh: **7/7 actual returns**, six RTC and one Power, with six using normal
console PM. Repeated Power and clean-kernel qualification remain.

The first endurance batch adds three actual same-boot returns: two RTC and one
early USB wake. Current total: **10/10 kernel returns**, eight RTC/one Power/
one USB. The USB segment fails its intended RTC wake check and is excluded
from RTC and completed-duration acceptance; all remain diagnostic/tainted.

The complete repeat adds four RTC returns: **14/14 actual kernel returns**,
twelve RTC/one Power/one USB, thirteen meeting their intended wake criteria.
SPM entries=resumes=14, aborts=0, restore failures=0; final PM COMPLETE sequence
997/error 0, all three ext4 error counters zero. Only one attributed Power
cycle exists. Clean-image repetition and the earlier device-phase wait remain
open; a returned kernel alone does not establish an overnight-drain pass.

## 28. Product auto-suspend policy

Missing in installed 04. New source requests full sleep after 60 seconds dark,
paused and inactive; recent playback/work and refusals reset a bounded retry
interval. Playing/Buffering never admits full suspend. Short Power retains
Product v2's immediate sleep request when paused and display blanking while
playing; long Power retains shutdown confirmation.

The new kernel exports immutable `system_sleep_abi=1` for its context/CIRQ fix.
Old 04 and tainted diagnostic boots cannot enable this product path. The helper
inherits the request's actual flock, acknowledges asynchronously, locks radio/
transfer, update and maintenance ownership, checks live bounded workload leases,
fresh battery safety state and USB absence, and requires Reborn's explicit
quiescence/DB FIFO barrier/closed PCM/display-off acknowledgement. Updates and
platform transfers/maintenance also take the shared operation lock. Expired
leases and leftover files cannot inhibit forever; process death releases locks.

A wakeup-count handshake (bounded to two seconds if a wake source stays active)
and child-IRQ comparison cancel a new Power/RTC event
during preparation or maintenance. A durable same-image unfinished-attempt guard
prevents automatic crash/sleep loops. Each actual entry arms the existing
30-second one-shot RGU backstop, paused only during SPM residence; a recovery
reset is never a resume pass. Clean explicit owner success or a new
source identity can recover it. Reborn checks live lock ownership if preparation
is abandoned, restores input and reports failure instead of swallowing input.

The existing 600-second PCM timer/630-second recovery watchdog remain unchanged.
Only BSP-attributed timer-only returns (no assertion, TWAM, CPU wake or child
Power/RTC IRQ change) may keep the screen/radios quiesced for a fresh battery
check and re-entry. Other wakes restore normally. Receipts record endpoints,
SPM ticks, accumulated suspended seconds, cycles and maintenance wake counts.
This is software-tested source, not installed product/endurance qualification.

## 29. 5-min suspend drain

`17-five-minute-return/`: one real battery-only suspend, normal console PM,
same boot `404ef43c...`, external-module taint 4096. USB unplugged at host
19:01:48 UTC and returned 19:09:47; the resident result was stored before USB.
RTC was programmed for 310 seconds after 60 seconds of unplugged settling.

- SPM residence: 10,022,080 ticks / 32768 = **305.849609375 seconds**.
- Boottime-minus-monotonic residence proxy: 306.599490353 seconds.
- Fresh BAT0 voltage: **3.983422 → 3.950244 V**, delta **−33.178 mV**.
- Displayed SOC: **76 → 76%**, still a provisional voltage estimate.
- RTC child IRQ 6→7; Power 26→26; one expected wake, no unexpected wake.
- COMPLETE sequence 654/error 0; entries=resumes=7, no abort/restore failure;
  Reborn restored, alarm cleared, ext4 error counters all zero.

The separate daemon samples are 3.988037→3.942553 V. They are not substituted
for the endpoint ADC reads. Recent charging relaxation and the SOC filter make
this short voltage delta unsuitable for an overnight-rate extrapolation; the
unchanged percentage is not evidence of zero consumption. The strict original
verdict still refuses clean qualification solely for taint, as intended.

Raw archive SHA256: first-return.json `54c1be10e6316cfc19c749402aca0dc04aeef90fe657b93d558f46b5563531d7`;
retained-sysfs.tar `6cd92d9777db9a8bf1561126d66446bf4b73f4df35caa9065da0ea4b87ecba00`;
persistent.tar `9f11fccc82dfb393d01e19c564377c9c5d14a15b9b5e488c9a8dc99e0a7d48f9`.

Installed PCM has a **600-second wake timer** and 630-second recovery WDT.
No continuous 30-minute/2-hour/overnight result can be claimed on that policy.
Product maintenance wakes must be counted and suspended residence accumulated;
the screen/radios must stay asleep through an attributable maintenance wake.

## 30. 30-min suspend drain

First attempt is **INCOMPLETE**, archived in `22-endurance30-return/`. USB was
removed at 20:05:07 UTC and reconnected at 20:35:30, before the requested
34-minute window ended. After 120 s settling, two RTC segments completed with
595.848907471 and 595.285644531 s SPM residence. A third resumes on cable
insertion after 487.923645020 s. Total actual residence 1679.058197022 s is
below 1800; no complete thirty-minute drain result is claimed.

The two uncontaminated segment endpoint series are 4.055712→4.021435 V and
4.032861→4.016381 V, daemon SOC 86→86 both. The third endpoint is Charging and
is excluded from depletion analysis. Its intended-RTC/auto-disarm checks fail
because the alarm had not fired; every kernel return is same-boot/COMPLETE,
SPM errors/restore failures zero and all ext4 errors zero. No retry occurs.

Raw archive SHA256: first-return.json `42fc47082649e9c0556bbdade09f65921838ef6b0b87ecc52b5924dd4daeb674`;
retained-sysfs.tar `3762065ea539e122ea7db493444e45bd9847f6070c093c38d5511376a6eb9fa7`;
persistent.tar `83aba18df7290b50c83f7c6daf95c134dfc50b32fc8c2f64fbcbc03fec04080d`.

The identical repeat is **COMPLETE as a diagnostic segmented measurement**,
archived in `24-endurance30-repeat-return/`. USB unplugged at 20:37:43 UTC,
reconnected at 21:12:03 UTC, after the collection finished. No SSH traffic
during collection. Same boot `404ef43c-1237-4eed-8c00-56210c9574a8` throughout.

| Segment | RTC alarm | SPM residence | Fresh voltage before → after |
| --- | ---: | ---: | --- |
| 1 | 600 s | 596.103546143 s | 4.046044 → 4.018798 V |
| 2 | 600 s | 595.226043701 s | 4.028906 → 4.014843 V |
| 3 | 600 s | 595.277069092 s | 4.021435 → 4.010888 V |
| 4 | 30 s | 25.228149414 s | 4.017260 → 4.008471 V |

Total **1811.834808350 s suspended / 1847.315205602 s elapsed**: 98.079%
residence, 35.480 s of awake preparation/restore/check gaps. Four expected RTC
wakes, zero unexpected wakes, every alarm disarmed before cleanup. Normal
helper screen restoration occurs between segments. This is neither continuous
suspend nor the new automatic product policy. Strict qualification remains
false solely because the matching diagnostic module taints the kernel (4096).

Whole-collection fresh BAT0 endpoints, both Discharging:
**4.050439 → 4.013964 V (−36.475 mV)**; daemon SOC **86 → 86%**. The unchanged
SOC is not a zero-drain result: installed 04 excludes suspension from its
estimator clock and caps the observation interval (§33). Recent charge
relaxation, nonuniform awake load and the provisional voltage curve also
prevent extrapolating this short measurement to an overnight capacity loss.
The separate daemon voltage samples, 4.050659→3.997045 V, are not substituted
for the endpoint ADC series. No pack-current measurement is available.

Raw archive SHA256: first-return.json `cdcb8fc1ee312872dcfe2a233b4a71790f30f4961c7efc8053ec53b04facd6f9`;
retained-sysfs.tar `917edf0567178f66b1bd8ff0e99bceb7eb64b3a1c43434bbb427dfc094f6a020`;
persistent.tar `652877a651325200badfc1baa3cbc4fbb0509e316699196c34cfb3d4f68af264`.

## 31. 2-hour suspend drain

NOT RUN or armed. The completed diagnostic 30-minute observation permits the
next duration, but the built successor should first receive owner installation
and clean staged/Power/RTC/automatic-policy checks. This measures the actual
built-in context fix and corrected SOC clock instead of extending old 04's
tainted, screen-restoring segmented harness. No two-hour result is inferred.

## 32. Overnight result when available

No new full-suspend overnight result. Owner's 88%→30% runtime result fails the
product target. <=1% cannot be assessed through SOC rescaling or stale values.

## 33. SOC / charging issue

No 88% UI cap found. Installed voltage-based curve reaches 100% at 4.175 V;
charging estimate subtracts a provisional 75 mV and moves at <=1 point/min.
For example 4.175 V while charging maps near 95% before time filtering, so a
brief/partial charge can lag further. This is a possible mechanism, not proof
of the missing starting-voltage/termination event. CV hold/termination uses
existing 4.175/4.200 V entry/guard and six stable ten-second samples; unchanged.
SDP 450 mA and DCP 650 mA are programmed ceilings, not measured pack current.
Need a complete charge/termination record to explain that particular 88%.

A separate **post-resume UI freshness defect is confirmed** by SSH in
`21-endurance30-armed/deployment.jsonl`: at monotonic 6160.474 s, Reborn still
publishes the battery sample from 451.902 s while the daemon is fresh at
6160.333 s. `background.quiesce()` invalidates an outstanding request, whose
worker deliberately sends no result; prepare/restore consume generation changes
inside control callbacks, leaving the main loop's old Boolean pending flag set
forever. New source tracks the pending request's generation and clears it when
invalidated. A real quiesce/resume-between-ticks test reproduces and covers this.
No SOC scaling, clamping, delayed updates or historical sample substitution is
introduced. This defect is proven for the diagnostic resumes; attribution to
the earlier 88% charging observation is not established.

The estimator also receives CLOCK_MONOTONIC, which excludes time asleep, then
caps any observation interval at 60 seconds. This explains why the diagnostic
sleep endpoint SOC can stay fixed despite a fresh lower voltage. New source
uses CLOCK_BOOTTIME for SOC only and accounts for the actual observation gap
in the unchanged filter and one-point-per-minute rate. Curve, charging offset,
rest-confidence requirements and all electrical/protection limits are unchanged;
the shutdown grace and scheduling clocks are unchanged. Regression tests hold
monotonic time fixed while physical time advances, verify loss becomes visible,
and verify elapsed time alone and voltage rebound never invent capacity. This
corrects reporting, not electrical consumption; it cannot earn a drain pass.

## 34. Battery health evidence

NOT ENOUGH EVIDENCE for degradation. Software did not attain deep sleep and
even C3 was blocked during the long boot. Do not blame hardware before software
sleep, peripheral state and voltage endurance are qualified.

## 35. Files changed

The coherent Linux change covers CPU PM/CIRQ ownership, filesystem-freeze
selection, USB clock ownership and event-driven detached monitoring, persistent
boot/power evidence, product suspend ownership and battery-maintenance returns,
resident diagnostic collectors, targeted regressions, release identity and this
report/roadmap. Reborn adds the automatic policy, database preparation barrier,
abandoned-helper recovery and observation-generation fix. Commit inventories
provide the exact file list; private physical evidence remains under ignored out/.

## 36. Tests

Earlier targeted USB/C3/reconnect/charger suite: 42 PASS, 1 pre-build DT SKIP
(superseded by the complete artifact checks below). 23 boot evidence/power
journal/boot-order tests PASS (existing
boot-order ResourceWarnings recorded). Production ARM `drivers/y2/usb.o`
compile PASS. Matching 04 diagnostic module ARM compile PASS; loaded only for
the separately labelled follow-up diagnostic, not the five clean stage passes.
The CPU PM ownership fixture also checks the actual GIC-mask ordering; the
existing suspend abort/restore fixture follows deferred syscore restoration.
Current paired source: Reborn fmt/strict workspace Clippy and **332 workspace
tests PASS**; explicit DB barrier, pending observation-generation recovery and
live helper lock ownership are included. ARM release build with the matching
04 SDK passes; the final source revision is rebuilt in the candidate. Platform
sleep/update/maintenance/workload targeted suite: **46 PASS**; latest narrower
34-test sleep/context suite also passes. SPM ARM compile passes. The broader current source power/CPU/USB/battery suite passes 155 cases with
one pre-artifact DT skip; the added bounded wake-count test also passes. These
targeted checks are supplemented by the completed frozen-source build below.
The added suspend-time SOC correction passes 53 battery/power/sleep/journal
regressions. Frozen Reborn source is reconfirmed at all 332 workspace tests.

The complete frozen-source build now passes kernel/config/DT/layout/BOOTIMG,
exact module ABI and the ARM application build. Production profile: **542 unique
cases covered**, 532 passed in the locked container plus ten dependency-specific
cases that all pass on the packaging host; zero remaining skips/failures.
The initial isolated profile stopped on an inaccessible shared-source symlink;
a private copy of the same pinned source resolves that environment problem,
and the complete profile passes. ARM ABI and shell syntax checks pass in QEMU.
ARM ELF closure: **384 files / 1,411 dependencies**, no build RPATHs. Seven exact
loadable kernel modules are owned by BOOTIMG's rescue archive, not Y2ROOT.
Reborn embedded source and installed product/power Python bytes match the
committed inputs. Rootfs/manifest/privacy/preserving-update validation passes.

## 37. Commits

Frozen source pair:

- Linux `0c9b78c7903182861b84e7d90a536bd30fca295a` — current build source,
  including suspend-aware SOC elapsed time; parent
  `cec9cae1b0caf2280b49cd07a655b28c0f5e1897` contains suspend context,
  USB idle, owned product policy and evidence.
- Reborn `5a9f7586dd8d80ab5afc16c6a9a7e853e7469aeb` — automatic requests,
  DB barrier, helper recovery and fresh post-resume observations.

Existing Luca author/committer identity is preserved; no identity configuration
was changed. Isolated detached worktrees are under
`/home/luca/Dokumente/Code/worktrees/y2-deepsleep-final/`.

## 38. Candidate / hashes

One full successor is built: **DEEPSLEEP-FINAL-01/root v1.31**, release
`1.0.0-platform-v1-deepsleep-final-candidate.1`, kernel
`6.18.0-y2linux-platform-v1-deepsleep-final-01`, compiled source pair in §37.
Canonical owner package:
`/home/luca/Dokumente/Code/Y2Linux/out/y2linux-platform-v1-deepsleep-final-candidate/`.

- BOOTIMG (7,254,016 bytes): `8a354eb0b9a9e65b3213ee83b1db53c9bd1174a52a9ea27233749c7d22c0cc16`
- Y2ROOT (536,870,912 bytes): `f84d1bc4a819f819f2f9b6f3593be00ba491b0ae17c5b6220f0024aea5b681e0`

Only BOOTIMG/ANDROID are selected by the preserving scatter; Y2DATA and all
other partitions remain unselected. The package includes manifest, complete
SHA256 inventory, validation receipts/report and OWNER-HANDOFF.md. Matching
kernel symbols remain in the adjacent `…-candidate-symbols/` folder.
No flash has occurred; built-in and product physical qualification remain open.
The handoff's old firmware-provisioning directory was absent; all seven existing
04 target firmware files were instead verified against the pinned inventory and
04 package receipt before staging. No new firmware/calibration input is used.
Installed candidate 04 is the exact packaged fallback:

- BOOTIMG: `be0f4379531be4b8f94fd927adda18106fbad1a567665cb63d5807908095aea4`
- Y2ROOT: `4fc765b931f85e0fee96c0b80c92592eca3a4f3f2a4e379d18abd71bc3978e64`

These fallback hashes are prior sealed image identities, not partition readback
claims. Owner action: verify SHA256SUMS, use the preserving scatter with Download
Only for BOOTIMG and ANDROID/Y2ROOT, then boot with USB connected for identity
collection. The owner explicitly reserved flashing; the agent does not flash.
The investigation remains **MORE_WORK_REQUIRED** until the clean built-in,
automatic sleep, longer endurance and unresolved hardware gates are settled.
