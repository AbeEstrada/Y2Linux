# Y2 Platform 1.0 input validation

2026-10-04. **IN_PROGRESS; physical acceptance pending.** Work is isolated to
`codex/platform-v1-input` in both repositories at
`/home/luca/Dokumente/Code/worktrees/platform-v1-input/{Y2Linux,Y2Reborn}`.
No flash, push, unrelated merge, identity change or main-worktree write.

## Identity and evidence boundary

Linux base `b5aea93`; input tools/admission `99087bac96728d1b61ee92828d8d56608f5cc27d`.
Reborn base `b71b468`; fixed candidate
`a701e0b866293c7e2bdfab95545081a8e363c074`.
Kernel/DT/CPU/I2C drivers and production packaging are unchanged.
Candidate: `out/platform-v1-input-candidate/`, build
`Y2-INPUT-V1-CANDIDATE-01`. It contains ARM userspace binaries and a manifest,
**not BOOTIMG/Y2ROOT images**. It has not been installed or physically qualified.

The nonblocking `/tmp/y2-platform-v1-device.lock` has been occupied by other
sessions. No live-device command, mount, service stop or hardware mutation has
occurred in this pass. Current counted physical tests and input-to-frame latency
must not be inferred from software tests or historical logs. The owner has
agreed to perform counted tests when a capture window becomes available.

Retained hardware authority: UART01 Linux `e9e8d63`, Reborn `b71b468`, kernel
`6.18.0-y2linux-cpu-c3-uart-01`, boot
`fd955840-35d9-47db-83e0-ff47d6bb2d2b`, taint 0. Bounded C1/C2/C3 gates pass;
3,647 actual C3 entries/returns/UART ACKs with zero restore failures. Baseline02
new-image/cold-boot qualification remains PHYSICAL_NOT_RUN. See
[CPU receipt](Y2-CPU-C3-UART-PHYSICAL.md) and
[admission audit](../planning/roadmap-gap-audit.md#platform-10-input-pass-admission--2026-10-04).

## 1. Complete architecture and authority

APT32F -> data-ready EINT55 falling edge -> threaded IRQ -> I2C0 at 0x51,
100 kHz, register-zero write/repeated-start nine-byte read -> AA/55 class-3
frame validation -> KEY_UP/PAGEUP or KEY_DOWN/PAGEDOWN down/SYN/up/SYN -> evdev
CLOCK_MONOTONIC -> main-thread InputManager poll -> NormalizedInput ->
ActionRouter -> typed Action -> Ui/AppModel update -> Effect -> runtime dirty
frame -> normalize/draw -> EGL/GBM/DRM page flip -> render return. Contrary to
the proposed generic pipeline, the current application has **no separate
input-reader thread or semantic input channel**.

| Behavior | Single authority |
| --- | --- |
| Frame validation, one I2C transaction per IRQ | APT32F kernel driver |
| Physical navigation debounce | gpio-keys-polled; 20 ms polling, default 5 ms debounce rounded to the poll interval |
| Volume hardware debounce / changed-state reporting | MT6582 keypad hardware / driver |
| Power interrupt and system wake capability | MT6323 PMIC keys; DT wakeup-source |
| Repeated down / orphan release safety | InputManager pressed-state machine; no extra time-window button filter |
| Wheel duplicate suppression and cadence | WheelCadence in InputManager; unchanged 8 ms filter |
| Hold / repeat timing | InputManager only; 650 / 400 / 90 ms |
| Short/long exclusivity, screen-off and Power gesture ownership | ActionRouter |
| Fine navigation versus long-list acceleration | Ui context policy, never duplicate detection |
| SYN_DROPPED/device loss/reopen | InputManager cancellation/drop/rescan state |
| Successful full-system resume and its ScreenWake | Platform/suspend owner; no suspend subsystem changes here |

Screens do not parse evdev types, device names or key codes. The separate
semantic screen-off guard in UI also protects control-socket/global actions;
it is not another bounce filter. Full source contract:
[Reborn ownership](../../../Y2Reborn/docs/architecture/platform-v1-input.md).

## 2–4. Actual retained wheel pattern, bounce and accuracy

[Machine-readable retained analysis](evidence/platform-v1-input-retained.json)
records exact input-log hashes, counts and nearest-rank quantiles. These are
real older hardware captures, **not current counted acceptance**.

| Capture | CW / CCW press/release pairs | Active same-direction gap min / median / p95 / max | Synthetic down-to-up median / max | Same-direction gaps <8 ms |
| --- | --- | --- | --- | --- |
| DEV02, 2026-09-10 | 30 / 22 | 61.712 / 82.350 / 123.511 / 154.569 ms | 14 / 34 us | 0 |
| GPU01, 2026-09-18 | 83 / 83 | 30.957 / 41.349 / 82.729 / 165.575 ms | 9 / 32 us | 0 |

“Active” excludes pauses >=220 ms; the full distributions retain those pauses.
The old DEV02 receipt also records 52 wheel IRQs and 52 I2C completions for 52
wheel pulses. A synthetic release a few microseconds after a press is the
kernel's intentional pulse, not a second detent or button bounce. The physical
hand-to-frame count and any firmware-level duplicate/re-read distribution are
unknown: no owner-counted detents exist in these receipts. Therefore neither
zero physical duplicates nor zero missed detents is claimed. The 8 ms window
rejects none of the retained valid event spacings; no evidence justifies tuning
it. A current 100 CW / 100 CCW counted test remains required.

## 5–7. Fast wheel, acceleration and reversal

Preserved cadence EWMA `(3*previous + gap)/4`; first three detents remain single.
Two steps become eligible at detent four with <=110 ms cadence; three at six
with <=70 ms; four at ten with <=45 ms. Duplicate packets do not grow the
streak. No tier above four is added. Pause **>=220 ms**, backwards timestamp,
direction reversal, device loss, overflow and screen transitions reset cadence.
The exact 220 ms boundary was corrected from `>` to `>=` to match Product v2.
No trusted timestamp means precise single steps; receipt-time batching cannot
be used as evidence of duplicate detents or intentional acceleration.

Only catalog lists with >=40 rows honor suggestions. Home, Settings, short
lists, Queue, dialogs, Quick Settings and editing remain one item per accepted
detent. Now Playing wheel volume stays a fixed +/-2 regardless of acceleration.
Reversal tests reset immediately in either direction; fast/medium human feel
remains unmeasured on the candidate.

## 8–9. Queue and latency

There is no semantic channel backlog. The old reader consumed just one
1,024-byte read per device/loop; the fixed reader drains up to 16 reads to
EAGAIN, preserving timestamp order across devices. A synthetic real-reader
100-detent burst (400 records, 9,600 bytes on host) produces exactly 100 single
steps in one poll, with nothing left for the next poll. This is deterministic
software evidence, not a physically counted spin. A producer exceeding the
budget defers held-key aging until queued releases are consumed. Select, Back
and transport records are never coalesced. Coalescing wheel suggestions would
lose detent cardinality in precise contexts and is rejected without a measured
backlog that requires it.

Main-loop sleeps remain 15 ms lit / 50 ms dark; dirty frames remain rate-limited
by 34 ms plus rendering/page-flip work. These are source scheduling settings,
not measured latency percentiles. Wheel, Select, Back, volume and Play/Pause
physical-to-kernel, kernel-to-action/state and state-to-frame median/p95/worst
are currently **NOT_MEASURED**. The old input monitor quantized its timestamp
to whole seconds, so it cannot establish those latencies.

The new bounded monitor records absolute monotonic microseconds at raw receipt,
normalization, action/state and next successful render return. The steady-state
renderer return follows DRM page-flip completion; initial modeset and actual
photon time remain separate. The external capture measures kernel timestamp to
observer receipt only; this must not be mislabeled Reborn/UI latency. No I2C
latency or raw APT32F frame timestamp is invented.

## 10–13. Buttons, long press, Power/wake and screen-off

| Button | Intentional short action | Hold |
| --- | --- | --- |
| Select | Select on release | Context options at 650 ms; release consumed |
| Back | Parent/back on release | Home; release consumed |
| Play/Pause | Toggle on release | Now Playing while lit; no invisible screen while dark |
| Previous / Next | Track action on release, lit or dark | Seek -/+30 s; then repeat at 90 ms, also while dark |
| Volume +/- | Atomic audio target +/-2 on down | Repeat starts 400 ms, cadence 90 ms; bounded 0..100 |
| Power | Lit -> ScreenSleep; dark -> ScreenWake on confirmed release | Lit -> Quick Settings exclusively; dark gesture belongs to wake |

Repeated down while already pressed is ignored. Kernel autorepeat never adds
to Reborn's own timing. Late repeat ticks emit at most one event, never a
catch-up burst after release. A true long press arriving in one queued batch
emits LongPress before Release; a physically short press arriving late stays
short. The initial long seek no longer also emits a same-tick repeat.

A Power press begun dark cannot sleep an externally awakened display or open
Quick Settings after wake. A lit gesture interrupted by an external screen
transition cannot toggle the new state. Select/Back begun dark stay suppressed
on release after wake; wheel motion never changes invisible UI. Cadence resets
on display transitions, including suggestions already decoded in that batch.
Transport/volume remain global during paused or active screen-off playback.

Full suspend was not implemented, invoked or qualified. The suspend session
can consume existing typed NormalizedInput and ScreenSleep/ScreenWake/PowerMenu
Actions. `InputManager::reset()` discards old evdev queues, cancels held state,
clears drop/cadence state and reopens; route returned Cancels and reset the
router at the platform boundary. Platform must emit ScreenWake from a confirmed
successful wake; an orphan Power release cancels rather than sleeping again.

Volume no longer fsyncs the session on every press/repeat. Audio's existing
atomic target/ramp is unchanged and UI volume marks persistence dirty. The
existing 15-second checkpoint and shutdown save remain; an abrupt crash can
lose the last uncheckpointed volume adjustment. Actual listening response,
rapid physical presses and >=20 presses of each button remain pending.

## 14–15. Idle, wakeups and C1/C2/C3

APT32F has no timer/poll loop, one threaded read per data-ready IRQ, no handler
retry, no idle logging, rate-limited transfer failures, and IRQ drain before
I2C suspend. Keypad is IRQ-driven changed-state input with inherited scan policy;
Power is PMIC IRQ/wakeup. Neither wheel nor keypad is a full-suspend wake source.
Navigation gpio-keys-polled **does create a 20 ms kernel poll** while opened;
Reborn also retains 15/50 ms main-loop wakeups. Device rescans add at most one
per second, even when initially absent; they no longer retry sysfs every loop
when missing. No CPU governor, core-parking, C1/C2/C3 or radio policy was changed.

Current untouched-input IRQ deltas, timer wakeups, context switches and CPU
usage are **NOT_MEASURED due to the busy device**. Retained whole-system UART01
C1/C2/C3 working evidence includes the prior input implementation; it supports
compatibility in that bounded scope, not new-image qualification or electrical
battery savings. The existing 50 Hz navigation poll is an explicit remaining
idle limitation. Converting it to interrupts requires validated GPIO/EINT mux,
IRQ/debounce and wake ownership beyond this handoff provider. No guessed pin
remux, firmware sleep command, increased poll interval or weakened idle guard.

## 16–18. Bugs, fixes and rejected optimizations

Four added deterministic tests **failed before fixes**: queued real hold became
short, kernel repeat doubled the local volume authority, dark held transport
became a short track skip, and a dark-started Power gesture slept an externally
woken display. They pass after fixes. Additional source/test findings fixed:

- Rebind identity used changing inputN; failed initial opens/absent devices were
  never revisited. Stable parent identity plus one-second discovery retries.
- One-read queue handling could leave queued releases behind timer aging. Bounded
  draining and deferral on budget exhaustion; timestamp order across devices.
- Long seek and repeat could start together in one tick. Repeat restarts its
  interval after the long action; no same-tick duplicate seek.
- Exact 220 ms pause did not reset as specified. Correct inclusive boundary.
- Lost-device/drop/suspend reset state needed explicit, reusable cancellation
  and queue reopening; tested reset/drop behavior and unknown release safety.
- Wheel cadence could survive invisible interaction or an already-decoded wake
  batch. App reset plus router batch policy preserves the first visible steps.
- Volume performed synchronous durable checkpoint work per physical step.
  Bounded existing persistence cadence replaces those writes.
- Input monitor timestamps were whole-second values and lacked raw/state/frame
  correlation. Explicit bounded microsecond diagnostics replace that record.

Rejected: changing 8 ms without bounce evidence; new gesture engine; larger
acceleration tiers; broad channel/thread rewrite; lossy wheel coalescing;
button time filters in multiple layers; slowing navigation polling for an idle
metric; speculative GPIO/EINT migration; undocumented APT32F commands; kernel
logging/verbose release telemetry; full-suspend implementation; flash/push.

## 19–22. Files, tests, commits and candidate

Linux changes: this report, roadmap-gap-audit.md, platform-v1-roadmap.md,
`docs/validation/evidence/platform-v1-input-retained.json`,
`tools/development/input-capture.c`, `tools/development/analyze-input.py`,
`tests/test_input_capture.py`. Reborn changes:
`crates/reborn-platform/src/input.rs`, `app/reborn/src/main.rs`,
`crates/reborn-ui/src/tests.rs`, `docs/architecture/platform-v1-input.md`.

Validation: fmt PASS; clippy workspace/all-targets/locked/-D warnings PASS;
workspace tests **256 passed**, including **36 input tests** and **40 UI tests**;
ARM release workspace build PASS using retained Baseline02 Buildroot SDK,
Cortex-A7/NEON/hard-float. Linux input tests **5 passed** (actual APT32F handler
and GPIO callbacks plus analyzer fault cases). Observer compiles with host
Clang and ARM GCC under -Wall -Wextra -Werror. ARM ELF/dependencies inspected.
Optional host QEMU smoke was unavailable (qemu-arm absent; container daemon
unavailable); it is not substituted for physical acceptance.

New tests cover detents, duplicates, valid rapid events, reversal/onset/reset,
queued short/long exclusivity, all six short/long button contracts, volume and
seek repeats, cross-device ordering, real-reader burst/partial/EOF/budget,
initial-open/rebind recovery, SYN_DROPPED, full reset, dark navigation/Power,
wake-batch cadence, bounded diagnostics and visible focus at both ends of
10/100/1k/10k libraries. Existing screen/back/dialog/empty/Unicode tests preserved.

Commits: Linux `99087ba` (tools/admission); Reborn `a701e0b` (source/tests/contract).
Candidate manifest retains exact compiled-source and binary SHA256 values:
`out/platform-v1-input-candidate/manifest.json`. Reborn binary SHA256
`d0330570db870826dee319b0b7627507e7c12b1eb079330f4fd4e847bae5a5f8`;
12,562,796 bytes. Raw software logs and receipt: `out/input-validation/`.
No rootfs/kernel build is necessary for the unchanged kernel; integration with
other Platform 1.0 subsystem work remains a separate owner boundary.

## 23–24. Remaining physical owner test and verdict

Await a free nonblocking shared-device lock. Verify actual installed identity
and controller inventory first. Upload only the bounded observer to private
`/run` storage, retain records locally and remove it afterwards; never grab
input devices, flash, probe undocumented I2C or disturb another session.

Count 100 isolated clockwise and 100 counter-clockwise detents (pause after
each); compare raw presses, accepted detents and visible UI steps separately.
Then medium/fast sustained rotations, stop/resume, rapid reversals; 20 short
presses of every button, long holds and simultaneous controls; screen-off active
and paused playback, wake and volume listening; Home/Library/Artists/Albums/
Tracks/Now Playing/Queue/Settings/dialogs/Quick Settings; realistic large lists.
Record owner feel separately from machine counters. Observe idle IRQ/CPU/timer
activity without changing other sessions' CPU/radio policy. Candidate-specific
raw/action/state/page-flip diagnostics require executing that ARM binary; older
installed code can establish raw events but not its improved state/frame trace.
Device rebind/full resume are separate guarded destructive-to-service tests;
software cancellation tests do not replace their physical acceptance.

**Provisional verdict: MORE_WORK_REQUIRED.** Coherent implementation and software
validation are complete; current counted detent/button, actual latency, idle
and owner feel evidence remain open. No input or full-system milestone is closed.
