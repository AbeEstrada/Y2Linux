# Y2 Platform 1.0 full system suspend / resume

Status: **MORE_WORK_REQUIRED — implementation in progress; physical full resume not yet qualified.**

Work is isolated on `codex/platform-v1-suspend` in both repositories. Linux base
`b5aea93`, Reborn base `b71b468`. No main-worktree edit, unrelated merge, push or
flash. C1 WFI, C2 SLIDLE and C3 DORMANT entry/restore architecture are preserved.
All device access uses the non-blocking `/tmp/y2-platform-v1-device.lock`.

## Starting hardware evidence and original failure

The 2026-10-04 locked reads identify installed **Y2LINUX-BASELINE-02**: Linux
`8584ccd85f052f351fe51650b2348c83ca894ed4`, Reborn
`b71b468860233faa0a42b8448ec5777fa952b8e3`, kernel
`6.18.0-y2linux-baseline-02`, root `2025.02.18-platform-v1.21`, boot
`27e6d684-3794-4490-95db-a489027cd4f4`, taint 0. Battery reports Charging;
current and previous SRAM suspend journals are invalid/empty, backstop inactive.
These reads do not qualify this image's deep system suspend or cold-boot C3.
Private receipt: `out/platform-v1-suspend/inspect-01/inspect.txt`.

[UART01 physical evidence](Y2-CPU-C3-UART-PHYSICAL.md) independently proves repeated
runtime C3 reset-and-return, not freezer/device/system suspend.
The retained [Fix02 failure](Y2-CPU-FINAL-FIX02-PHYSICAL-QUALIFICATION.md#full-rtc-suspend--fail-exact-boundary)
entered full suspend, woke on RTC/SPM EINT (`0x20`), recorded reset dispatch
`0x59325253`, restored CPU/syscore/secondaries and device callbacks, then stalled
between `DEVICES_RESUMING` and kernel `EXIT`. Its RGU recovery was a **new boot,
not successful resume**. That original stalled instruction remains unestablished.
Current source already brackets device completion, console, thaw, PM_POST_SUSPEND
and kernel exit; historical failure locations are not assumed current.

## Implemented corrections

1. Full system suspend now validates Linux's populated CPU0 context stash in its
   finisher, before leaving coherency. It checks BIU readback, normal PCM pointer,
   length, UART request release, sleep timer/watchdog/power controls, local timer
   restore and CIRQ restore. Restore failures return an error, increment
   `suspend_restore_failures`, retain fault notes and quarantine the shared SPM
   owner. A real CPU reset return remains counted even if later restoration fails.
   Both entry refusal and successful wake unwind CPU/cluster/CIRQ ownership.
2. Linux can log a device resume callback error and still return zero from
   `pm_suspend`. The existing journal previously retained such failures only in
   its small callback ring. It now preserves the first noirq/early/device resume
   error in its retained receipt, preventing a successful kernel exit from hiding
   a storage, USB, radio, graphics or audio restoration failure. Prepare refusal
   classification remains unchanged; no second tracing architecture is added.
3. Successful `pm_test` was indistinguishable from deep resume in the product
   receipt. Receipts now capture the selected test mode. Deep restoration needs
   same boot, valid error-free kernel EXIT, the reset-vector stamp, full suspend
   PCM length 596 and a nonzero wake source. Staged success is recorded without
   advertising deep sleep or marking Reborn ready as a deep-resume result.
4. Reborn exposes `SleepRequested`, `SleepPreparing`, `SleepRefused`, `Sleeping`,
   `Waking`, `Restored`, `RestoreFailed` through its typed platform boundary.
   The helper obtains explicit `sleep_prepare` acknowledgement: checkpoint queue
   and position, refuse playback/pending work, release ALSA and DRM scanout, blank
   display. Preparation blocks new input/transport/control mutations until unwind.
   `sleep_restore` restores scanout/backlight, renders a frame and clears old press
   ages, queued wake edges and wheel cadence. It runs on failed attempts too;
   status-socket liveness alone no longer proves application restoration.
5. A short Power gesture requests sleep when playback is paused/stopped; during
   playback it blanks the display. An off-screen press wakes the display. A long
   hold opens the existing shutdown confirmation even with the screen off; its
   release cannot request sleep. Normal copy contains no SPM/CIRQ/stage names.
6. A one-shot resident qualification observer uses the existing SRAM receipt and
   callback ring. Host entry is never retried after a lost acknowledgement. It
   separates staged tests from actual entry/resume counter deltas, verifies boot,
   taint, positive suspend residence, child IRQ attribution, alarm clearing and
   ext4 error counts. No reset or flash command is present.

These are source/fault-injection results, not claims that they caused the
historical post-device-resume stall. The new source is **not installed**.

## Wake sources and charging policy

Power is the MT6323 key child IRQ (hardware child 5); RTC is child 20. Both feed
PMIC EINT and **SPM `WAKE_SRC_EINT`**, not a dedicated Power/RTC SPM bit. The
existing DT wake flags, child IRQ wake ownership, MFD late wake-mask ordering and
CIRQ/GIC replay remain. Attribution uses same-boot serviced child IRQ deltas;
the shared EINT bit alone is insufficient. RTC alarms are programmed/read back
through the existing RTC API; the observer clears its own fallback alarm after
wake or entry refusal. Awake-alarm delivery remains separate from suspend wake.

Active charging intentionally refuses device preparation with `-EBUSY`. The
source documents the stock USB wake-lock rule and the need to service charging
safety/watchdogs awake. No charger guard, PMIC protection or charging policy is
bypassed. Battery operation and an independent observer are required for the
later staged/full physical tests.

Exact MT6582 reference: [vendor SPM sleep source](https://android.googlesource.com/kernel/mediatek/+/d53dd75c3ff77cac3f5be58fddfe660e94f94d64/arch/arm/mach-mt6582/mt_spm_sleep.c),
retained under `out/cpu-c3-uart-research/` in the original repository. It uses
SHUTDOWN_MODE for full suspend, DORMANT_MODE for runtime idle, and supports
retained infrastructure/DDRPHY. No later-SoC register assumptions or arbitrary
L2-retention changes are imported into full shutdown.

## Trace ownership

| Boundary | Existing evidence owner |
| --- | --- |
| Request / radio preparation / sync / return | y2-suspend, durable suspend-last.json |
| Freezer / device / late / noirq / CPU offline | patch 0060 stage marks; patch 0059 callback ring |
| PMIC wake masks / RTC armed | MT6323 MFD late callback snapshot |
| SPM / wake reason / context | spm.c, retained SRAM, full-entry/resume counters |
| Resume vector / cpu_resume | stackless resume-vector.S stamp then cpu_resume_arm |
| Syscore / noirq / early / device resume | kernel stage marks and callback phase ring |
| Console / PM notifier / thaw / exit | patch 0060 existing completion marks |
| Radio / Reborn / display/input restoration | helper receipt and explicit Reborn acknowledgement |

## Physical results

Pending acquisition of the shared device lock for staged qualification. Other
sessions retain ownership during their hardware tests; the owner requested
continued source work until they finish. Do not unplug USB until Wi-Fi observer
readiness is verified. Planned order remains staged PM, one short RTC wake, one
Power wake, subsystem checks, five mixed cycles, ten mixed cycles, longer residence.
No full-suspend attempt or watchdog recovery has been performed in this pass yet.

| Coverage | Current full-suspend result |
| --- | --- |
| Power wake / clean input / backlight | NOT_RUN |
| RTC awake alarm / RTC deep wake / clear | NOT_RUN / NOT_RUN / NOT_RUN |
| Same-boot complete system resume | NOT_PROVEN |
| eMMC / SD / filesystem | Source regressions pass; physical full restore NOT_RUN |
| USB | Source regressions pass; physical full restore NOT_RUN |
| Wi-Fi / CONSYS | Source regressions pass; physical full restore NOT_RUN |
| Bluetooth / BTIF | Source regressions pass; physical full restore NOT_RUN |
| GPU / Lima / DRM / display | Source regressions pass; physical full restore NOT_RUN |
| AFE / CS43131 / ALSA | Source regressions pass; physical full restore NOT_RUN |
| Reborn | Native tests pass; new acknowledgement path physical NOT_RUN |
| Wheel / input / RTC timekeeping | Source regressions pass; physical full restore NOT_RUN |
| Five / ten mixed cycles / longer residence | NOT_RUN / NOT_RUN / NOT_RUN |

No electrical standby measurement is available. Sleep-duration/CPU/IRQ/battery
voltage/SOC observations are proxies only; no standby-current number is claimed.

## Validation and limitations

Fresh production-config ARM kernel Image, zImage and modules build in the pinned
host environment. Final kernel hashes and logs are under
`out/platform-v1-suspend/`; build artifacts under `out/platform-v1-suspend-build/`.
The 132-test targeted source run passes: 129 passed, three emitted-DTB checks
skipped. Coverage includes suspend policy and failures, CPU/idle/timers/CIRQ,
storage/MMC context, USB, connectivity/radio, GPU and audio. The later 23-test
policy run passes, including two added charging/preparation-refusal checks.
Reborn fmt and strict all-target Clippy pass; all 243 workspace tests pass with
locked dependencies and isolated temporary paths. The ARM release build passes
against the exact Baseline02 SDK; Reborn SHA256 is
`673f8c18d293101102e9768076e5429968f71ecee17121eb38aa0d3172418a09`.
A native headless process passes explicit prepare/checkpoint, prepared mutation
refusal, restore/control admission and a second prepare/restore in the same
process. This is an application IPC test, not physical GPU/audio/input proof.

Wake-input reset is scheduled before fallible display restoration, so even a
failed display restore discards the prior gesture before accepting input again.

The ordinary product request still preserves its existing physical-qualification
refusal. It must not enable unqualified full suspend simply because runtime C3
works or these source tests pass. Installed Baseline02 cannot execute the new
Reborn prepare/restore protocol without a coherent userspace update; new kernel
checks likewise require owner installation, which this pass does not perform.
The historical stalled instruction and complete physical restoration remain
open until installed-image evidence establishes their current state.

Implementation commits:

- Linux `69fa2c7`: checked full-suspend restoration, retained device resume errors,
  explicit Reborn acknowledgement, one-shot observer and regression tests.
- Linux `c73cd83`: charging and preparation failure policy.
- Linux `50cc218`: temporary Wi-Fi observer port and verified host-key support.
- Reborn `4544b1a`: typed preparation/restoration and Power/input semantics.
- Reborn `f69c3c4`: discard wake input before fallible display restoration.

The physical receipt remains pending. No push or flash.
