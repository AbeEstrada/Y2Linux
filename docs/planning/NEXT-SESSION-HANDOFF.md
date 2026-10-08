# Next-session handoff — deep-sleep continuation, 2026-10-08 local

> **LATEST (end of 2026-10-08): POWER-FINAL-05 is INSTALLED** (owner flashed; archives 82–84 verified). Folder `out/y2linux-platform-v1-power-final-candidate-05/`
> (own `OWNER-HANDOFF.md`, `SHA256SUMS`), symbols `…-candidate-05-symbols/`, worktrees `/home/luca/Dokumente/Code/worktrees/y2-power-final-05/`, receipts
> `out/deep-sleep-final/build05-receipts/`. Linux `837b6146ee4d0f551b69cfaddd686a69ce56a060` (branch `codex/platform-v1-power-final-05`, based on 04), Reborn
> `97ff8c3` unchanged, kernel `6.18.0-y2linux-platform-v1-power-final-05`, root v1.35, release `1.0.0-platform-v1-power-final-candidate.5`. BOOTIMG (7256064 B)
> `0137a855db96d8f94005333941495c4fdaa2f81c9eb653458b77e9c0fd044117`, Y2ROOT `9175185fd577b759302337cc8d17f678fde3dc621525b90d45cf6cb370e99a4d`; `fallback/` = sealed 04.
> **Change vs 04 (only):** vendor `PMIC_INIT_SETTING_V1` `LP_SEL` (bit 0) on VA 0x404, VIO28 0x500, VUSB 0x502, VM 0x552, VIO18 0x556, applied ~10 s after boot (E2 only, readback
> verified), PMIC write whitelist extended by exactly those bits, runtime revert `/sys/firmware/y2_pmic/lp_sel` (root; `echo 0` clears, `echo 1` sets). The bits live in the PMIC and
> survive reboot: `echo 0` before flashing 04 back. A beyond-vendor storage-rail switch (VMC/VMCH/VEMC3V3) was NOT included (blocked by the safety classifier). No power benefit is
> claimed: there is no on-device current sensor, capacity is unknown, SOC is voltage-derived.
> **Evidence on 05:** first check clean (boot `3cae62f2`, taint 0, `lp_sel applied=1`, golden differences 25→20 awake). Suspend probe run (archives 85–87): 1573.4 s suspended, 2 maintenance
> wakes, SPM 3/3, aborts 0, golden differences at suspend entry 22→17, SD rails off across suspend, connectivity rails off, VEMC3V3/VUSB/VGP2 on. Full analysis, rail map (measured PMIC state),
> vendor-source comparison and candidate ranking live in `docs/validation/Y2-PLATFORM-V1-SUSPEND-POWER-OPTIMIZATION.md` **on branch `codex/platform-v1-power-final-05`** (worktree
> `/home/luca/Dokumente/Code/worktrees/platform-v1-power-final-05/Y2Linux`), with data `docs/validation/data/y2-suspend-power-optimization-20261008.json`, `y2-pmic-suspend-golden-vs-awake-20261008.json`,
> `y2-suspend-probe-analysis-20261008.json`, and tools `tools/development/power-session/{suspend-probe,arm-suspend-probe}.py`, `tools/development/analyze-suspend-probe.py`.
> **Key findings:** (1) the maintenance wake is the SPM PCM timer, 600 s (vendor `SPM_WAKE_PERIOD`), 603 s cycle with ~3 s awake; (2) Y2Linux runs the vendor deep-idle PCM with INFRA/DDRPHY
> retained, whereas the vendor's real suspend uses the 597-word `pcm_suspend` with INFRA/DDRPHY and 26 MHz off (highest-risk/highest-payoff lever, separate image); (3) the vendor suspend golden
> PMIC table differs in 17 entries at suspend entry (VEMC3V3 on, VPROC/VSYS sleep-voltage enables, LP_SEL on VMC/VMCH/VEMC3V3, clock/OSC control); (4) radios and SD card are already off in suspend.
> **Next (agreed with owner):** overnight unplugged drain test on 05 (paused, screen dark; started from 88%/4.095 V, post-charge, probe stopped), archive with `capture-return.py` under the host lease
> before anything else; then Power-button and RTC wake and early-boot on 05; overnight A/B with `lp_sel` cleared; optional USB-meter top-up measurement (KWS-2303C class; verify mAh counter,
> D+/D- pass-through); then decide on `pcm_suspend` (06). Notes: never read `/sys/power/wakeup_count` or `/proc/kmsg` over SSH; the PWRAP write allowlist in `kernel/platform/policy.h` is a
> guarded safety control (widen only with explicit owner approval).
>
> **UPDATE (POWER-FINAL-05 built, awaiting owner flash):** `out/y2linux-platform-v1-power-final-candidate-05/` (Linux `837b614` on branch `codex/platform-v1-power-final-05`,
> worktrees `y2-power-final-05`). 04 + vendor LP_SEL on five LDOs with runtime revert `/sys/firmware/y2_pmic/lp_sel`; BOOTIMG `0137a855…44117`, Y2ROOT `9175185f…99a4d`.
> Full validation PASS; physical NOT_RUN; benefit unmeasured. Installed image is still 04 until the owner flashes. Suspend probe tools:
> `tools/development/power-session/{suspend-probe,arm-suspend-probe}.py` (power branch). Report: `docs/validation/Y2-PLATFORM-V1-SUSPEND-POWER-OPTIMIZATION.md` (power branch).
>
> **CURRENT STATE — read this first (updated end of 2026-10-08).** Blocks below are chronological
> detail; where they conflict with this block, this block wins.
>
> **Installed image: DEEPSLEEP-FINAL-04** (owner flashed; archive68 verified read-only). Diagnostic
> successor to 03: Linux `5e267571d584da7fbe356d3161801ba15f87fa57` (code commit `5e26757`), Reborn
> `97ff8c357bab12319087740d7c97b5051e6588f5` (unchanged), kernel `6.18.0-y2linux-platform-v1-deepsleep-final-04`,
> root v1.34, release `1.0.0-platform-v1-deepsleep-final-candidate.4`. BOOTIMG (7256064 B)
> `4738de48bea8a9970e89cc8d703c824ac3faec103ab2ed6989270816f9ace5f6`, Y2ROOT (536870912 B)
> `b0e667515971da65e1a48afb222248bf68e841bef9d015ad9669944c9bafc041`. Owner folder
> `out/y2linux-platform-v1-deepsleep-final-candidate-04/` (own `OWNER-HANDOFF.md`, `SHA256SUMS`, `fallback/` = sealed 03),
> symbols `…-candidate-04-symbols/`, frozen worktrees `/home/luca/Dokumente/Code/worktrees/y2-deepsleep-final-04/`,
> receipts `out/deep-sleep-final/build04-receipts/`. 03 package, symbols, worktrees and all evidence are untouched.
>
> **What 04 changes vs 03 (diagnostics only, no behavioural fix intended):** `WAIT`/`LOCK` retained-ring phases (9/10) around the
> silent steps of `device_suspend()` plus legacy-bus logging (overlay `0059`), and a built-in device-phase stall sampler in
> `pm-journal.c` (4 s/12 s after a successful `DPM_PREPARED`: ring notes `dpm_stall`/`S:`/`D:`/`dpm_blocked` and stacks to the RAM
> console). `git diff cfb7e09 5e26757 -- . ':!docs'` is the complete non-doc difference. Because the extra records change timing,
> a clean 04 does NOT prove the stall is fixed; it could be hidden. A revert of only the per-device records is the test if 04 stays clean.
>
> **Why 03 failed (analysis, unchanged evidence):** retained ring logs only devices with PM callbacks; every failure ends after a
> returned `11008000.i2c` callback at DPM_PREPARED, so the stall is in an unrecorded wait (`dpm_wait_for_subordinate`,
> `pm_runtime_barrier`, `device_lock`, `dpm_list_mtx`, post-callback bookkeeping or the global `async_synchronize_full()`).
> Host chronology puts the reset ~30 s after the last callback (consistent with the 30 s RGU backstop; reset source unproven). No
> upstream 6.18.y fix matches. Both 03/02 stalls were ~400-460 s after boot; the 04 passes entered at 557 s and later (untested hypothesis).
>
> **Physical results on 04 (all owner-driven, no collector, normal automatic policy, nothing deployed to the device):**
> trial 1 (archives 68-71): 469.27 s real SPM sleep, same boot. One-hour trial (archives 72-73): 3805.25 s suspended in ~3825 s,
> six 600 s maintenance wakes (dark, connectivity suspended) each re-entered, SPM boot totals 9/9 entries/resumes, aborts 0,
> restore failures 0, taint 0, ext4 errors 0, USB wake `0x20` labelled `unknown` by the product. Provisional pre-cable SOC 71%→69%
> (3.966→3.948 V; post-charge relaxation included): NOT a drain result. Data: `docs/validation/data/y2-deepsleep04-trial1-20261008.json`,
> `…trial2-1h-20261008.json`.
>
> **Early-boot test PASSED (archives 74-75, after the owner's reboot):** new boot `aae0ddb3`, taint0; the product requested sleep at BOOTTIME35.6 and entered
> the kernel at **39.4 s** (far earlier than the 03/02 stalls at ~400-460 s), slept **551.80 s** (18081448 ticks), woke on the USB reconnect (`0x20`, label
> `unknown`), PM COMPLETE seq48, Reborn restored, ext4 errors0, 04 guard `pending:false`. A simple "too early after boot" trigger is therefore not supported
> by this sample; one pass cannot exclude it. Data: `docs/validation/data/y2-deepsleep04-early-boot-20261008.json`. Overnight drain test is next.
>
> **Next (agreed with owner):** one owner reboot (early-boot test: unplug ~6 min after boot to probe the 400-460 s stall window),
> then an overnight unplugged drain test (paused, screen dark, no input; owner reports unplug/reconnect times; morning: archive with
> `capture-return.py` under `flock -n /tmp/y2-platform-v1-device.lock` BEFORE anything else, then `image04-readonly-health.py <dir>`).
> On a stall: do not restart, clear the (new, 04-identity) guard or repeat; connect USB; the ring/sampler notes resolve against
> the 04 `System.map`. Still open: stall rate, Power/RTC wake on 04, formal 30-min/2-h gates, overnight drain, warm-start display,
> user poweroff, cold-C3/electrical gaps. Collectors still pin the 03/02 identity and need a reviewed update before use (not needed for
> owner-driven trials). Never read `/proc/kmsg` over SSH (blocks). The 03 guard on `/data` (pending, 03 identity) is inert on 04.
>
> **Product direction discussed (not started):** release builds should drop observer modules/dev collectors/verbose console and the
> heavy stall dump, keep the retained black box + 30 s suspend backstop, and replace the permanent post-failure guard with a bounded
> cooldown policy. Opt-in automatic error reporting is feasible (diagnostic exports exist; send after next boot over HTTPS, scrubbed,
> rate-limited, consent-gated) and is a later task after suspend is settled.

**04 one-hour trial PASSED (archives 72-73):** same boot `836f0b1d`, taint0. Main sleep from BOOTTIME1364.1; six 600 s maintenance wakes
(1965...4980 s), each dark with connectivity runtime-suspended, each re-entered; final USB wake at 5188.7. Product receipt: 7 cycles, 6 maintenance wakes,
**3805.25 s suspended** (99.5% of ~3825 s unplugged); SPM boot totals 9/9 entries/resumes, aborts0, restore failures0; ext4 errors0, pstore empty, Reborn restored.
Provisional pre-cable SOC 71%->69%, 3.966->3.948 V (post-charge relaxation included; no pack current): NOT a drain result. A 1.2 s early entry/return at 1358.0
preceded the main entry (consistent with the unplug event); it also completed. Data: `docs/validation/data/y2-deepsleep04-trial2-1h-20261008.json`.
Still open: stall rate unknown (nine clean entries on 04), early-boot hypothesis, Power/RTC wake, formal 30-min/2-h gates, overnight, display/poweroff gaps.

**04 trial 1 PASSED (2026-10-08, archives 68-71):** normal automatic policy, no collector, owner unplug ~16:15:30 UTC and USB re-plug.
Same boot `836f0b1d`, taint0; journal request BOOTTIME556.0, kernel suspend557.8, resumed1027.8 (USB wake `0x20`, product label `unknown`).
SPM entries/resumes0→1/1, aborts0, restore failures0, residence15376821 ticks=**469.27 s**, PM COMPLETE seq48/error0, Reborn restored,
ext4 errors0, 04 guard `pending:false`. This is one passing cycle; it does not resolve the intermittent pre-SPM stall. New WAIT/LOCK records
are overwritten by the resume tail on a pass and are only informative after a stall. Data: `docs/validation/data/y2-deepsleep04-trial1-20261008.json`.
Observation to test (not a finding): both 03/02 stalls occurred ~400-460 s after boot; this pass entered at 557 s.

**Latest: DEEPSLEEP-FINAL-04 diagnostic successor built and sealed — awaiting owner flash (2026-10-08).**
Owner folder `out/y2linux-platform-v1-deepsleep-final-candidate-04/` (own `OWNER-HANDOFF.md`,
`SHA256SUMS` verified); matching symbols `…-candidate-04-symbols/`; frozen paired worktrees
`/home/luca/Dokumente/Code/worktrees/y2-deepsleep-final-04/`; receipts `out/deep-sleep-final/build04-receipts/`.
Linux `5e267571d584da7fbe356d3161801ba15f87fa57`, Reborn `97ff8c357bab12319087740d7c97b5051e6588f5` (unchanged),
kernel `6.18.0-y2linux-platform-v1-deepsleep-final-04`, root v1.34. BOOTIMG
`4738de48bea8a9970e89cc8d703c824ac3faec103ab2ed6989270816f9ace5f6`, Y2ROOT
`b0e667515971da65e1a48afb222248bf68e841bef9d015ad9669944c9bafc041`. Preserving scatter identical to 03; Y2DATA
unselected; `fallback/` = sealed 03. Validation: container suite, 10 native packaging, 27 native splash, Reborn
fmt/clippy/335 tests, QEMU, ELF closure 384/1411 all PASS; new stall records verified present in the kernel.
**Physical status NOT_RUN.** 03's pending guard does not match 04's identity, so automatic sleep is admitted on 04;
after install verify identity read-only, then one bounded normal-policy trial (to be reviewed with the owner).
On a stall, retained ring ends at the last WAIT/LOCK record and/or `dpm_stall`/`S:`/`D:` notes (resolve wchan against
the 04 System.map); preserve the new guard and archive before any reboot. Collectors still pin 03 and need a
reviewed identity update. Docs here are uncommitted alongside the owner's earlier doc edits; code is committed as 5e26757.

**Previous: 2026-10-08 late local analysis — device-phase stall diagnostic prepared
(source only; nothing built, flashed, deployed or run on hardware).** Reconciling
archives 65/66 with the exact03 suspend/device PM code gives these findings:

- **Chronology.** Archive65's host capture (03:12:20 CEST, BOOTTIME 182 s) puts
  boot `0132fb21` start near 03:09:18 CEST, so the kernel suspend request
  (BOOTTIME 398.4 s) fell near 03:15:57. Archive66's first SSH (07:44:11 UTC,
  BOOTTIME 23261.9 s) puts boot `81dce40c` start near 03:16:29 CEST. The unplanned
  reset therefore came roughly **half a minute** after the last callback, not
  hours later. That is consistent with the 30 s RGU backstop the product helper
  arms before every entry (`product_sleep.py`), within host-timestamp error of
  several seconds. It does not prove the reset source (RGU status is raw0 even
  for known backstop resets). The ring header `backstop_s=0` only reflects
  that the helper's HELPER_REQUEST mark resets the ring before the backstop is
  written; it is not evidence that no backstop was armed.
- **What the ring can and cannot say.** `y2_pm_device()` is called only from
  `dpm_run_callback()`, so it records devices that *have* a PM callback. Every
  logged entry has its leave. The stall is therefore in a step the ring cannot
  see: `dpm_wait_for_subordinate()`, `pm_runtime_barrier()`, `device_lock()`, the
  silent post-callback bookkeeping, `dpm_list_mtx`, or the global
  `async_synchronize_full()` at the end of `dpm_suspend()` (Linux 6.18's new
  asynchronous scheme). A bus hang inside a runtime-resume triggered by the
  barrier is also possible and would be silent. Every failure so far (clean02
  archive28b, 404ef43c core, 03 boot 0132fb21) ends at the same
  `11008000.i2c` leave; the registration order after it is not yet known.
- **No known upstream cause.** Stable 6.18.y PM-core fixes after 6.18.0
  (`f384497`, `c9670fd`, `bc6fdd4`) concern the late/early runtime-PM enable
  order, a no_pm completion token and prepare-error cleanup. None describes a
  device-phase wait, so no backport is justified by the evidence.
- **Prepared, unbuilt diagnostic (smallest that separates the hypotheses).**
  Overlay `0059` now also records `WAIT` (before the child/consumer wait and
  runtime barrier) and `LOCK` (around `device_lock`) ring entries per device and
  logs legacy-bus suspend. `pm-journal.c` gains a built-in sampler armed by a
  successful `DPM_PREPARED`: at 4 s and 12 s without `DEVICES_SUSPENDED` it writes
  the suspender's wchan and up to three D-state tasks to the retained ring and
  full stacks (suspender, blocked tasks, busy workqueues) to the RAM console with
  only that console un-suspended. No external module: no taint. A hard bus hang
  that stops the worker is itself distinguishable (ring ends at the last
  `WAIT`/`LOCK` entry with no `dpm_stall` note). Regression:
  `tests/test_dpm_stall_diagnostics.py` (7 cases); fix01-03, platform suspend,
  CPU PM, product auto-sleep and sleep-product suites still pass (102 cases);
  the three changed objects cross-compile warning-free under the production
  config in the locked sandbox (`out/dpm-stall-compile-check/`, new directory).
- **Not claimed.** This is diagnosis tooling, not a fix. pstore/DRAM retention
  across the RGU reset is unproven for the *console* sink (the SRAM ring is the
  authoritative sink). Nothing here changes the pending 03 guard or any evidence.

Next concrete owner decision: approve building a **diagnostic successor
(DEEPSLEEP-FINAL-04 source, not yet built)** and flashing BOOTIMG+Y2ROOT with the
preserving scatter; then one bounded normal-policy trial on that image. Until a
successor is installed, another unplugged wait on 03 cannot diagnose the stall
(the guard refuses entry). The collectors pin the 03 identity and need an
explicit reviewed identity update for the successor; do not weaken their gates.

**Previous: 2026-10-08 evening read-only follow-up (archive67).** The morning
failure below remains the suspend blocker. At 17:00 CEST the installed03 Y2 was
on boot `ad0d5416-1a4a-453c-a008-704b3ae88ceb`, taint0. The intervening
`81dce40c` boot ended with an **orderly user-requested poweroff** at approximately
09:55:39 CEST (journal `shutdown_execute`, pstore `Power down`), followed by the
current boot about16 seconds later. Times are anchored to host capture and
per-boot BOOTTIME; device wall time is unreliable. This is distinct from the earlier unclean
pre-SPM reset. The pending guard still names failed boot `0132fb21` and exact03;
it remains intact. Current boot SPM entries/resumes0/0, with421 journaled
`sleep_recovery_required` refusals before cable return. BOOTTIME and MONOTONIC
advance together; no whole-system sleep occurred during this seven-hour window.

On the current boot, the voltage-derived battery estimate was57%/3.862V at
BOOTTIME5s and32%/3.736V at the last pre-cable journaled refusal
(BOOTTIME25346s, about16:58 CEST). The hourly series falls through52,47,42,38,
36 and32%; it is **not flat** in the archived journal. After reconnection the
live daemon reports Charging31%/3.830V at17:00 CEST. The 63% prior to orderly
poweroff and57% just after boot are different-load provisional estimates, not
six points of measured off-state use. Current, capacity and a calibrated SOC
remain unavailable. Charging/CONSTANT_CURRENT reports fault/sample/stop/last
errors0; 450000uA is the programmed ceiling, not measured current.

Read-only archive `out/deep-sleep-final/evidence/20261008/67-image03-evening-return/`
holds the first-return, retained pstore/PM, persistent logs, health check and
summary and [machine-readable follow-up](../validation/data/y2-deepsleep03-evening-20261008.json).
Exact03 executable/helper hashes still match archive65; Reborn is
responsive and paused, PCM closed, no scan, Wi-Fi/BT off, ext4 errors/warnings0,
USB configured. No test, policy change, guard clear, reboot or deployment was
made. Continue investigating the pre-SPM device-phase failure before another
unplugged endurance claim. Roadmap/audit remain MORE_WORK_REQUIRED.

**Earlier morning03 observation FAILED automatic suspend, then rebooted without
owner intervention.** Read-only SSH archive
`out/deep-sleep-final/evidence/20261008/66-image03-morning-return/` contains the
first-return, retained PM/pstore and persistent logs, subsequent health check,
owner observation, analysis, battery timeline and SHA256 receipts. Read the
[overnight result](../validation/Y2-PLATFORM-V1-DEEP-SLEEP-FINAL.md#32-overnight-result--2026-10-08)
and [machine summary](../validation/data/y2-deepsleep03-overnight-20261008.json).

- Owner: approximately six hours unplugged, around88% at removal and55% in the
  morning; **no manual restart after installation**. Pre-cable journal confirms
  55%, so the displayed endpoint is not merely stale UI. The estimated drop is
  about33 percentage points (about5.5 points/hour using the owner's rough time),
  not a measured charge/current or battery-health result.
- Installed03 identity is unchanged: Linuxcfb7e09/Reborn97ff8c3/rootv1.33;
  Reborn and all three changed helpers match archive65. Boot changed from
  `0132fb21-8462-4f77-9faf-3a7e7f1b8429` to
  **`81dce40c-9bb5-4f14-8465-c7e80ba3c602`**. The boot ledger marks the previous
  shutdown unclean. Old boot requests kernel suspend at BOOTTIME398.407s;
  retained sequence8 ends at **DPM_PREPARED**, callback ring ends after successful
  I2C at398.638s, no SPM entry/return recorded. RGU cause is unreported/raw0;
  pstore has no panic. Do not attribute the exact cause to I2C or watchdog.
- New boot has **SPM entries/resumes0/0** and380 durable
  `sleep_recovery_required` refusals. Its pending guard belongs to03 and the
  failed0132fb21 boot, unlike the old02 guard from installation. **Preserve it.**
  BOOTTIME and MONOTONIC advance together; no six-hour full-sleep claim.
  Runtime CPU0 DORMANT has807610 entries/resumes and zero restore failures;
  this is lower-power runtime idle, not successful system suspend.
- First-entry ADC4.092187V; final dark row56%/3.846972V, then screen-on
  Discharging55%/3.821484V at BOOTTIME23179.994s. Initial SSH already sees
  charging54%; later healthy charging55%. Keep these connected readings separate
  from the pre-cable endpoint. Device wall time uses build_floor and regressed
  across reboot; use per-boot BOOTTIME and recorded host UTC.
- Morning health: taint0, Reborn first frame/status healthy, playback paused,
  PCM closed, no scan, Wi-Fi/BT off, all three ext4 errors/warnings0, USB configured,
  Charging/CONSTANT_CURRENT with fault/sample/stop/last errors0. No active
  collector/helper, RTC alarm or backstop. Host lease released after reads.

Next blocker is the recurring pre-SPM device-phase failure on exact03. This
inspection did not reboot, clear the guard, deploy, build, flash or launch a
trial. Controlled30-minute/two-hour/endurance acceptance and the independent
display, poweroff, cold-C3/electrical gaps remain open. The
[audit](roadmap-gap-audit.md#clean-corrective-image-physical-admission) and roadmap
are refreshed without milestone promotion. Preserve all evidence and matching
images/symbols. Pre-observation statements below that03 suspend was NOT_RUN or
that the night had not started are superseded by this morning result.

## Previous checkpoint — 03 installation sanity pass

**Owner-installed DEEPSLEEP-FINAL-03 passes the requested quick SSH
installation check.** Archive
`out/deep-sleep-final/evidence/20261008/65-image03-first-check/` preserves the
first-return, retained/persistent evidence, exact installed hashes and
`verification.json` (18/18 checks). Boot
`0132fb21-8462-4f77-9faf-3a7e7f1b8429`, taint0, uptime182–278 seconds.
Linuxcfb7e09 / Reborn97ff8c3 / rootv1.33 / kernel03 match the sealed package;
running Reborn and all three changed Python helpers match the build byte-for-byte.
Reborn presents a real first frame and responds to status. USB is configured;
Charging/CONSTANT_CURRENT is observed with fault/sample/stop/last errors0 and
SDP450000uA programmed ceiling. Subsequent HOLD/recharge samples are retained;
no actual battery-current or full-charge measurement is claimed. All three
ext4 error counters are0, playback paused, PCM closed, no scan, Wi-Fi/BT off.

Normal automatic sleep is built in. The synthetic USB budget supply has no
wakeup source; physical cable and battery wake remain enabled. Operation locks
are free, only Idle workload is leased, and old02's pending guard does not match
03's identity. No test/helper, RTC alarm or recovery backstop is armed. No device
policy, service, firmware or guard was changed by this check. The host lease is
released at the end of the check.

**03 full suspend/endurance remain NOT_RUN:** entries/resumes0 while USB is
attached; admission correctly refuses active charging. A successful boot is not
a suspend/resume qualification. The owner still intends an exploratory unplugged
night. Leave playback paused and screen off; record actual unplug/entry time from
owner/journal. No overnight start is yet recorded and no collector is armed.
On morning reconnect, archive first before reboot or changes; compare boot ID,
actual accumulated sleep, maintenance/other wakes and fresh voltage/SOC.
Connected88% is provisional and is not an unplugged test endpoint. The missing
controlled30-minute/two-hour gates and independent reliability defects remain.
Cleanup is outside this task; preserve all evidence, sealed images and symbols.

## Successor03 baseline — installed, quick check passed

Owner folder:
`/home/luca/Dokumente/Code/Y2Linux/out/y2linux-platform-v1-deepsleep-final-candidate-03/`.
Use its `OWNER-HANDOFF.md`, `SHA256SUMS`, `manifest.json` and preserving scatter.
The unsuffixed `…-candidate/` and explicit `…-candidate-02/` still contain02;
they were not overwritten. Matching03 symbols/build remain separately retained.

- Linux source **`cfb7e098eae60918f47d7b330445bf66e9d61817`**.
- Reborn source **`97ff8c357bab12319087740d7c97b5051e6588f5`**.
- Kernel `6.18.0-y2linux-platform-v1-deepsleep-final-03`, rootv1.33,
  release `1.0.0-platform-v1-deepsleep-final-candidate.3`.
- BOOTIMG **`00c4399af0985e88e3345b7782bc29f02a73fd57ab39bb64db06e8b1f717fb90`**.
- Y2ROOT **`569f92e0bdc43be5ef908884e7f171698dfc76025b1ebfb80cc90b4cede5d617`**.
- **578 platform cases PASS** (541 locked-container, ten native dependency,
  27 native splash), zero uncovered skips/failures. Reborn fmt/strict Clippy/
  **335 tests**, fresh ARM, kernel/config/DT/module ABI/QEMU checks PASS.
  ARM closure384 files/1411 dependencies, no build RPATHs. Preserving package
  and ext4 checks pass; full receipts are in `out/deep-sleep-final/build03-receipts/`.

The source-bound BOOTIMG/Y2ROOT pair includes all committed production corrections
described below, includingd43b592 and Linux/Reborn display readiness/retry
changes. The source patch is not a
claim that the independent warm-start display root cause is fixed. No failed
or untracked display reset diagnostic goes into production. The first test-run
dependency failure is preserved: native splash needs desktop libdrm/Pillow;
cfb7e09 routes it to the required packaging-host pass. No test was dropped.

Owner uses **Download Only**, reloads03's `MT6582_preserve_data_scatter.txt`, and
selects **BOOTIMG + ANDROID/Y2ROOT only**. Y2DATA and every other partition remain
unselected. Boot USB-connected and verify exact image, charging, display, logs
and boot ID before unplugging. The owner alone flashes; no agent flash.

**Overnight intent:** the owner wants the player unplugged for the rest of the
night, with morning inspection. Save its actual start/stop times and fresh
unplugged battery endpoint. Preserve retained/persistent evidence first on
morning reconnect, before reboot or changes. Calculate real accumulated suspend,
maintenance/other wakes, awake gaps, same-boot continuity, voltage and fresh SOC.
An exploratory night does not retrospectively pass the interrupted30-minute or
missing two-hour gates. Entry and endurance on03 are **PHYSICAL_NOT_RUN** despite
the successful installation sanity check. No overnight collector/alarm is armed.
Archive65 verifies that the old02-specific pending guard has a different identity
and does not quarantine03. Historical02 overlay ledgers on Y2DATA remain evidence,
not a claim that overlays were applied to03.

The existing clean/product collectors pin02 source identities and will refuse03.
After fresh SSH verification, update their explicit accepted pair for a reviewed
03 trial; do not bypass boot/taint/source checks or reuse04/02 diagnostic modules.
`capture-return.py` is read-only and can archive the new boot before that work.

## Stopped for the day — archives62/63, interrupted endurance

- Base image02, boot **`f567b2c3-97eb-42e2-8c24-ffca801be25c`**, taint **0**,
  only normal DRM module. SSH `root@10.42.0.1`, pinned key
  `/home/luca/.ssh/y2linux_ed25519`. Acquire the shared host device lease again
  before resuming physical work; the previous session's lease was released.
- Collector **`/data/logs/deepsleep-product-f567b2c3-4893`**, former PID8254,
  has exited. Archive61 retains its arming; archive
  **`out/deep-sleep-final/evidence/20261007/62-product-30min-interrupted-return/`**
  contains the complete first-return, retained SRAM/pstore and persistent archive.
  `analysis.json` and `power-events.json` record the review.
- Owner requested an early stop and was told to reconnect. The former 01:00 UTC
  reconnect deadline is cancelled. This is **OWNER_INTERRUPTED, not a thirty-minute
  pass**: two actual SPM intervals of **600.004089355 + 343.159606934 seconds**,
  total **943.163696289 seconds** (15 minutes 43 seconds).
- The first interval ended on the 600-second SPM maintenance timer. Screen stayed
  off (`bl_power=4`), connectivity remained runtime suspended, and the normal
  product helper re-entered suspend. The second ended with USB insertion: PMIC
  wake `0x20`, cable presence/CHRDET activity, unchanged Power12 and RTC8 counts.
  The product receipt labels that terminal wake `unknown`; do not call it RTC.
- Same boot, taint0, SPM8→10 entries and resumes, no abort/restore failure,
  COMPLETE667/error0, Reborn restored, three ext4 error counters0. The observer
  correctly stops with `USB returned`, restores quarantine and clears its alarm.
  The local wake-count race below **did not occur in this physical trial**.
  USB contaminates the endpoint, and immediate receipt SOC is stale; no drain
  percentage or thirty-minute acceptance can be derived from this interrupted run.
- **`63-session-stop/parked.json`** verifies both operation locks are available,
  no collector/helper remains, RTC alarm empty, backstop idle, pm_test `none`,
  and the persistent product guard has `pending:true`. All 12 stop checks pass.
  Reborn answers status and playback is paused. USB is configured; the final
  `charger-stop.json` shows Charging, no faults, SDP450000uA programmed ceiling
  (not measured current). No new deployment, reboot, flash or test at closure.

If the owner has not installed03, verify02 identity, overlays and runtime wake
setting before any mutation. Prefer the newly requested coherent03 installation
over another live overlay. Its short normal-policy and full thirty-minute checks
must precede acceptance of two hours/overnight. Sealed02 remains unchanged.
The original independent reliability gaps remain open.

## Latest physical result — normal automatic sleep PASS

Archive **59-product-usb-wake-return/**, root3787, proves the narrow USB wake
correction: named maintenance7356 refusal, releaseBOOTTIME3895.063, automatic
kernel entry3916.070, one **203.051330566-second** SPM return. RTC7→8, Power12→12,
COMPLETE573, boot unchanged, taint0, Reborn restored, ext4 errors0. SPM totals8/8
with zero restore failures; total includes the earlier falsely reported53 return.
No hidden retry/direct collector suspend call. USB reconnect transfers302MB and
Charging works; all six physical wake owners remain enabled. This is qualified
live-overlay/runtime-policy behavior, **not unchanged sealed02 acceptance**.

Immediate ADC4.086035→4.092187V includes recovery. Immediate resume SOC90 is
still a pre-wake daemon sample; after-snapshot8.63s later has a fresh0.397s-old
sample90%, ADC4.060327V with application awake. No short-test drain/target claim.
Archive59 hashes: firstff64b9b0573ba305e252e4ecbdcb785f91b0d69b4a2019643a2536a4e1f4924b,
retained5138336dda0076704d8f9db7bddcac4a5d7fa5f6ae2ae4c7448c655651ecb843,
persistentada2ffd65ec837c9a7987ed5e2ee1fe1a10e8d41dd435c72be7b9b5ae842d736.
The roadmap/gap audit retains the short-policy and thirty-minute gates; owner
stopping for the day suspends further physical work until the next session.

## Current live corrections — keep separate from sealed02

1. Linux **`0ba99f5ffbdc6af2dac6320d0b3256121642fb0c`** fixes buffered
   PM-command replay. `/usr/lib/y2-platform/y2_platform/product_sleep.py` SHA
   **`72651d6f6366b7d58a8e80cac9e5681acb00ab4e7eb0315016ac4cc1789d72da`**.
   Archive54 and `/data/logs/deepsleep-live-overlay-f567b2c3-2987/` retain original
   bytes and deployment receipt; `/data/system/platform/deepsleep-live-overlay.json`
   records it. Kernel/Reborn/image metadata unchanged. Real Python-I/O regressions
   pass on host and installed Python3.12.14; old code fails all3 error cases.
2. Archive57 changes only `/sys/class/power_supply/y2-usb-input/power/wakeup`
   from enabled to **disabled**. This is the software gadget current-budget
   publisher. All six other PMIC/charger/Power/RTC/battery wake settings remain
   enabled. No current/voltage/protection/notification change. Persistent ledger
   `/data/system/platform/deepsleep-runtime-policy.json`; device evidence
   `/data/logs/deepsleep-usb-budget-wake-f567b2c3-3773/`. Runtime only; kernel source
   commit **`9066f73`** sets `power_supply_config.no_wakeup_source=true`, ARM USB
   compile PASS; archive59 physically confirms the causal correction. Do not claim that sealed02 contains it.

Archive53 FAILED product completion: named maintenance refusal and later auto
request worked; buffered Python close replayed an EBUSY suspend, then reported
that stale error after198.585602 seconds of same-boot RTC sleep. SPM7/7,
RADIOS_RESTORING470, taint0; actual application restoration occurred but no
successful product receipt. The local and installed-Python fixtures reproduce
exactly two stores and the stale exception. Commit0ba99f5 fixes that bug.

Archive56 then exposes the underlying refusal without replay: three normal
requests abort in device suspend with EBUSY, no new SPM entry (still7/7), same
boot/taint0, final RADIOS_RESTORING524/DEVICES_RESUMING error−16. Only synthetic
`y2-usb-input` suspend-check wake count increases2→8. `pm_wakeup_irq` is absent.
MUSB PM calls set_power→power_supply_changed→pm_stay_awake on this synthetic
supply. The explicit owner helper did not arm wakeup_count, so its passes did
not cover this path. Archive57's narrow runtime change tests that cause.
The old collector cleanup raced a final automatic refusal's guard clear; host
retook both operation locks and restored quarantine before the new trial.

3. **`39290266a020782b7cb543048aefb33c3da68570`** receipt/journal changes are
   now **DEPLOYED**, archive60, backup
   `/data/logs/deepsleep-endurance-journal-f567b2c3-4870/`.36 affected tests pass.
   `suspend_record.py` SHA97c8a6804c4dcacfddd0dbba4cca75780a0b8061c86123fa32fba7f56a47aa73;
   `power_journal.py` SHA57add62a7b97c9ef3055abfc94e2a24d8e8bdd2075f03b6bff9800a8c6d3e1b9.
   Keeps first entry ADC/timestamp across maintenance returns and completed
   endpoints at the existing event cadence. Both locks held, backups/ledger
   durable, no service restart, kernel/Reborn/firmware metadata unchanged.
   Existing power-daemon periodic rows still use its old imported logger;
   new product helpers use the updated event logger. No new polling timer.

The optional collector120-minute/8-hour modes require reviewed shorter success.
Only30 minutes is admitted now. It captures a separate fresh battery-after
sample; kernel-return receipt SOC may precede the battery daemon's next tick.
The new03 image contains these corrections; owner installation is now pending.

## Local-only maintenance correction prepared during trial61

**`d43b5923803d006122402aba65ee275d7f19ca13`** is committed and included in03,
**NOT DEPLOYED to the still-installed02**.
Production currently reuses the wake-event count read before the2-second battery
maintenance pause. A normal BAT0 notification in that interval invalidates it
and unnecessarily restores the screen/radios instead of re-entering sleep.
A real product-flow fixture with kernel wake-count comparison reproduces
`wake_event_in_progress` on old code. Set the count toNone after maintenance so
the next loop takes a fresh bounded read; preserve prior Power/RTC IRQ comparison
and the atomic count-store guard. All27 affected tests pass, including Power/RTC
during the gap and another event after the fresh read. Source SHA
`d83f140fb9b3670ae778864c39f61cfb64f5a1aa2279022eefec8e1f8c149dba`.
Receipt `out/deep-sleep-final/maintenance-count-source-validation.json`.

Trial61 remained on SHA72651d6f… and archive62 proves its first maintenance
re-entry succeeded. It ended on the owner's USB reconnection, not this race.
The old-source negative fixture still establishes the latent bug. Before any
longer trial, record the backed-up overlay when deployed and qualify the
corrected source; nothing was deployed after the owner's stop request.
Do not weaken the collector's shorter/same-source evidence checks. No new
candidate, raw hardware write or charging-policy change was made.

Read-only vendor comparison is saved at `out/deep-sleep-final/vendor-suspend-source/`.
It confirms stock INFRA/DDRPHY collapse requires its additional UART restore
path, whereas installed mode retains it. Existing stock poweroff extracts also
show write-interface unlock, BBPU4309 and GPIO37 handling; installed callback
uses4300. This is a sequence mismatch, not proof that changing one literal fixes
poweroff. No pin/register experiment or source implementation was performed.

## Confirmed clean progress

Archive **50-clean-cycles-return/** passes all five new real cycles on the same
untainted boot: three short RTC, Power89.802795s, RTC305.200562s. Combined with47,
**6/6 clean returns: Power2/2, RTC4/4**, SPM6 entries/6 resumes, aborts and restore
failures0, COMPLETE408. All RTC alarms auto-disarmed, no unexpected wake.
Five-minute ADC4.057031→4.052416V (−4.615mV), provisionalSOC89→89; no claim of
zero current or overnight target pass. Archive51 also proves live application
sleep preparation refuses `playback_active` while playback continues, then PCM
closes after pause. Volume and position restored.

Archive **47-clean-power-return/**: installed02 passes all five PM stages,
then a genuine same-boot Power return. SPM entries/resumes1/1, aborts/restore
failures0, 1243558 ticks = **37.950378418 seconds**, Power IRQ6→8 and RTC0→0,
COMPLETE seq163, taint0. RTC fallback was still pending and explicitly cleared.
Owner saw the normal player. Strict clean verdict passes.

Archive **48-clean-resume-health/**: five-second playback advances to4969 ms,
PCM hw_ptr216584, then PCM closes on pause. Volume/position restored. Both
internal and SD storage pass262144-byte write/fsync/readback/hash, ext4 errors0.
Wi-Fi is Online/COMPLETED by this check; the immediately returning health sample
in47 caught it reconnecting. Do not mislabel that earlier sample all-servicesOK.

Archive42 previously proved the same built-in02 context path through all five
stages plus RTC wake (24.529053 s) with a read-only stack observer/taint4096.
This is diagnostic evidence, separate from clean47.

## Installed image and sealed package

**DEEPSLEEP-FINAL-02**, release1.0.0-platform-v1-deepsleep-final-candidate.2,
root2025.02.18-platform-v1.32, kernel6.18.0-y2linux-platform-v1-deepsleep-final-02.
Linux **`5a32683f1ae9493c6a37bd18af3d131afb04d450`**;
Reborn **`5a9f7586dd8d80ab5afc16c6a9a7e853e7469aeb`**. Owner installed it.
It corrects01's missing inherited USB CCF clock claim. USB and charging work;
450000uA SDP ceiling is programmed policy, not measured battery current.
Archive26 recovers01's saved diagnostic export and exact stage2/-EIO failure.

Sealed immutable owner folder `out/y2linux-platform-v1-deepsleep-final-candidate-02/`,
identical canonical `…-candidate/`. Matching `…-candidate-symbols/` retained.

- BOOTIMG `38d2da2d9f4627d32e93dd87a91dd544e44526bbb6441619c5e4cf95d26fad75`
- Y2ROOT `da874614b165287a8e22799dce65c75641bd423e0ccd5d18aee99a6ebeb536bc`
- 543 unique production checks plus kernel/config/DT/module ABI/QEMU/ARM/ELF/
  preserving package checks pass. Failed01 is retained separately;04 fallback
  and source-matched symbols/build remain. Do not overwrite sealed packages.

No agent flash. Any successor is BOOTIMG/Y2ROOT only; owner installs preserving
Y2DATA. The new03 package above supersedes02 for the requested next baseline;
02 remains the preserved prior package/fallback.

## Unresolved failures — do not erase after a pass

1. **Intermittent device-phase wait:** clean02 archive28b resets during devices,
   last retained DPM_PREPARED seq21, ring ends with successful I2C after codec/MMC.
   No outstanding callback/wait is identified. Passing observer captures show
   a transient UART/SRCU wait but do not establish the root cause. Clean47 now
   passes the same staged sequence; repeated reliability remains open.
2. **Warm-start display:** service reboots after diagnostic boots reproduce
   vblank1/no progress and taint512 at~1.026s before modules (archives32/44).
   Owner hardware restart restores clean startup (38/45b). Active read-only
   archive36 shows OVL FSM0x100 (`h_wait_w_rst`), unchanged35 samples. Source
   display-readiness/retry fixes below do not fix that driver cause.
3. **Failed display recovery diagnostic:** archive38 recovers successful KMS
   disable after31.015s and inactive snapshot, then no return from module call.
   First completed hardware operation is unknown. **Do not repeat
   `y2-display-recover.ko`**. No backstop was armed in that trial; that omission
   must not recur. `kernel/platform/ovl-reset.h` is not production-integrated.
4. Original user-poweroff BBPU/panic defect remains separate and unresolved.
5. Clean short RTC/Power and five-minute residence now pass narrowly. Product
   auto-sleep/inhibitors now pass narrowly with the recorded overlays; cold-battery
   C3,30/120-minute and overnight drain remain incomplete. SPM shuts CPUs down
   with infrastructure/DDRPHY retained; deepest electrical minimum is unknown.
   No measured current, battery-degradation finding or <=1% target pass exists.

## Source branches and undeployed work

Both primary repositories: `codex/platform-v1-deep-sleep-final`.
Frozen paired worktrees: `/home/luca/Dokumente/Code/worktrees/y2-deepsleep-final/`.
Do not edit frozen production sources or upstream source cache.

Reborn **`97ff8c357bab12319087740d7c97b5051e6588f5`** is committed but **not
deployed**: require first page-flip event before presentation, preserve failed
buffers safely, one automatic context recreation per incident, wake retry.
335 workspace tests/fmt/strictClippy/ARM PASS, actual native regression fails
on old source. Linux splash retry-handshake fix has27 native tests/ARM PASS,
committed as **`f4d2774`** but not deployed. Receipt `out/deep-sleep-final/display-recovery-source-validation.json`.
No installed source metadata may be changed to imply these fixes are running.

Linux commits `9066f73`, `c73c581` and `d43b592` record the USB wake correction,
reviewed collectors and maintenance fix. The working tree also holds preserved
untracked diagnostic sources; do not include the failed reset diagnostic in
production. Existing Luca identity stays unchanged.
No push, release promotion, remote issue closure or external messages.

## Original overnight evidence and root correction

The initial image was POWER-FINAL-04, Linux5aeba051/Reborn8cd365d/rootv1.30,
verified against newest04 handoff and manifests. Retained long boot74a4645d
shows~6.72h screen-off, paused/radiosoff, **no product auto-suspend policy**.
Cold-battery C3 was enabled but blocked by USB PERI bit10; observed C3 zero.
Later voltage3.900146→3.403564V proves real depletion. Exact88% starting voltage
and charge termination did not survive rotation; no88% UI cap exists. Owner
later charged briefly and turned off; separate shutdown/panic logs are not
proof of an overnight suspend attempt.

Original full-suspend post-thaw hang was localized to nested CPU/cluster PM
saving masked GIC enables over core's original save. Removing that duplicate
owner and replaying CIRQ after core restore is built into01/02. Matching04
context-suppression diagnostic proved14 same-boot returns. Its30-minute repeat
accumulated1811.835s, four expected RTC wakes,4.050439→4.013964V; old SOC86→86
was invalid as drain evidence.02 fixes elapsed-time filtering usingBOOTTIME
without changing the curve, limits or reported values to hide loss.

The full38-section [validation report](../validation/Y2-PLATFORM-V1-DEEP-SLEEP-FINAL.md)
and [standing audit](roadmap-gap-audit.md#clean-corrective-image-physical-admission)
contain detailed receipts/limitations. Raw archives/hashes stay under ignored
`out/deep-sleep-final/evidence/20261007/`. All previous failed trials remain
failures; #16/#27/#28/#29/#31/#32/#33/#34 remain open, historical#30 unchanged.

## Historical 2026-10-06 handoff (superseded where noted above)

Three jobs. **Do not start the cleanup before Job 0 is complete.**

- **Job 0 — safety:** **DONE on 2026-10-06** (see below). Re-verify the three checks, then move on.
- **Job 1 — hardware:** owner flashes **POWER-FINAL-04**, validate it, locate the suspend stall.
- **Job 2 — cleanup:** `out/` keeps only **04**, documentation is consolidated, both repos end clean.
- **Job 3 — integrate the 11 parallel handoffs:** **DONE** (section below); the cleanup may now delete those merged branches.

Job 1 and Job 2 are independent. If the owner has not flashed yet, start Job 2.

## State of `main` right now (updated)

**The working baseline is POWER-FINAL-04.** `main` in **both** repos contains it: Linux `main` (compiled commit `5aeba05`, later commits are docs only) and
Reborn `main` `8cd365d`. 04 = 03 + the 11 parallel branches merged with 03 winning every collision; the image is behaviourally identical to 03 (the merge
added tools, tests and docs only), so **03 was never flashed and can be discarded**. (Reborn's checked-out branch
was switched from `cpu-idle-completion` to `main`; `cpu-idle-completion` is an ancestor and still exists). The earlier session's
uncommitted `main` docs are preserved on branch `wip/main-dirty-docs-2026-10-06` (commit `0f02caf`) **and** as
`/home/luca/Dokumente/Code/Y2Linux-backups/main-dirty-2026-10-06/` (patch + untracked copies). Decide whether to merge those
docs into the consolidated documentation (they describe the Baseline02 integration plan) or drop them.

## Paste-ready prompt

```
Read /home/luca/Dokumente/Code/Y2Linux/docs/planning/NEXT-SESSION-HANDOFF.md completely
(it is on `main`), then re-verify Job 0, then do Job 2 (cleanup) and, once I confirm
POWER-FINAL-04 is installed, Job 1 (hardware validation). We work with 04, not 03.
Do not flash. Do not push. Preserve Git identity (Luca) via environment variables and add no
model attribution. Never delete anything listed under "Must not be lost".
```

## Is 04 the newest image with every fix I proposed?

**Yes, 04 is the newest image and contains every fix that was implemented, plus the integrated parallel branches.** It was built from clean `main`
commits, packaged, validated (515 production cases, 10 skips, 0 failures) and sealed. It has **not been flashed**; the device runs POWER-FINAL-02.
The table below was written for 03; every row applies unchanged to 04. It is not "everything proposed": the table is exact.

| Item | In 04 (and 03)? | Evidence |
| --- | --- | --- |
| DAC idle bias off (rails drop when paused) | yes (from 02) | hardware PASS |
| Blocking connectivity supervisor + zombie reap fix | yes (from 02) | hardware PASS |
| Reborn calls `/usr/sbin/y2-platform` (Power "not available") | yes | hardware, via live symlink |
| Screen-off fallback when sleep refused (qualification, charger) | yes | hardware (qualification case), unit tests |
| Wi-Fi blocked at runtime after 5 dark idle minutes on battery | yes | decision function unit-tested; **never run on hardware** |
| Missing-AP scan backoff (`autoscan exponential:2:120`) | yes | runtime command measured live; supervisor code unit-tested |
| Post-thaw stall sampler, oops/panic notes, ramoops | yes | compiles, DT/config validated; **never run on hardware** |
| Journal breadcrumbs + `jiffies` around codec rails | yes (from 02) | ran; showed the stall moved to `filesystems_thaw` |
| Slow the 20 ms polled navigation GPIO while dark | **no** | idea only; top steady wake source (27 ctx/s). Dark transport buttons need it; needs a decision |
| Bluetooth connected idle vs C3 (BTIF/APDMA also blocks C2/C3?) | **no** | unmeasured; test with headphones connected, dark, battery |
| Clear stale `restore_failed` sleep receipt from an earlier boot | **no** | persists until the next request; cosmetic but wrong |
| FAST_PSP as Wi-Fi default | **no, rejected** | blocks C3 either way; CAM stays default |
| Automatic paused-inactive full suspend | **no** | gated until a same-boot resume exists |

Not yet done on hardware: Power wake, repeated suspend cycles, wall charging, missing Bluetooth
peer, 2-hour idle, overnight. **Full suspend still fails** (see below). Verdict: `MORE_WORK_REQUIRED`.

## Where everything is

| What | Where |
| --- | --- |
| Source, Linux | `main` in `/home/luca/Dokumente/Code/Y2Linux`, **compiled `5aeba051c428451483402e5874dcf8222afca259`** (later commits on `main` are docs only). The build clone `out/power-final-documentation/Y2Linux` is only a build vehicle |
| Source, Reborn | `main` in `/home/luca/Dokumente/Code/Y2Reborn`, **compiled `8cd365da5f3454c8e3189df1434b966edbd06575`** |
| **Sealed 04 package (flash this)** | `out/y2linux-platform-v1-power-final-candidate-04/` release `…candidate.4`, build `Y2LINUX-PLATFORM-V1-POWER-FINAL-04`, kernel `6.18.0-y2linux-platform-v1-power-final-04`, root `2025.02.18-platform-v1.30`; BOOTIMG `be0f4379531be4b8f94fd927adda18106fbad1a567665cb63d5807908095aea4`, Y2ROOT `4fc765b931f85e0fee96c0b80c92592eca3a4f3f2a4e379d18abd71bc3978e64`; `fallback/` is the exact **02** pair (the image installed today). Superseded and discardable: candidate-03 (never flashed) and earlier |
| 04 kernel symbols | `out/y2linux-platform-v1-power-final-candidate-04-symbols/` (`vmlinux`, `System.map`, `.config`): **needed to turn stall `wchan` numbers into function names** |
| Installed on the device today | POWER-FINAL-02 (`79f0925f…b307` / `93c1bf99…f147`), plus a live symlink `/usr/bin/y2-platform` |
| Private raw evidence | `out/platform-v1-power-final/private/` (network/media details, never publish) |
| Owner firmware provisioning (needed for any build) | `out/cpu-idle-completion-02-owner-firmware/` |
| Machine reports | `docs/validation/data/y2-power-final-02-physical.json`, `y2-platform-v1-power-final.json`; report sections 38 and 39 of `docs/validation/Y2-PLATFORM-V1-POWER-BATTERY-FINAL.md` |
| Device harnesses | `tools/development/power-session/` (README inside) |
| Memory notes | `~/.claude/projects/-home-luca-Dokumente-Code-Y2Linux/memory/` (`y2-power-final-findings`, `y2-power-candidate-build-lessons`) |

## Job 0 — make the cleanup safe

The Linux working clone's `origin` is an external worktree and its newest commits lived only in
its own `.git` under `out/`. They were copied into both main repos as `codex/platform-v1-power-final-03`.
Before deleting anything:

1. `git -C /home/luca/Dokumente/Code/Y2Linux log --oneline -3 codex/platform-v1-power-final-03` shows the
   docs/harness commit on top of `1ca3673`; same check in `Y2Reborn` (`b2c460e`). If the newest clone
   commit is missing, `git fetch out/power-final-documentation/Y2Linux codex/platform-v1-power-final:refs/heads/codex/platform-v1-power-final-03` again.
2. (**done**, preserved as described above) **Main working tree was dirty and belonged to an earlier session.** `main` has 7 modified docs
   (`CURRENT_PLATFORM_STATE.md`, `DOCUMENTATION_CATALOG.md`, `knowledge/candidate-index.md`,
   `planning/platform-v1-roadmap.md`, `planning/roadmap-gap-audit.md`,
   `release/Y2-COMMUNITY-BETA-FEATURE-AUDIT.md`, `…FEATURES.json`) and untracked
   `docs/release/Y2-PLATFORM-V1-{INTEGRATION-PLAN,INTEGRATION-STATUS,MASTER,PHYSICAL-QUALIFICATION}.md`,
   `docs/validation/Y2-PLATFORM-V1-INTEGRATION.md`, `tools/development/observe-platform-v1.py`.
   Save them first: `git diff > /safe/main-dirty.patch` and copy the untracked files. Then decide
   (owner) whether they are kept (merge into the consolidated docs) or dropped.
3. (**done**) `main` was an ancestor of 03 in both repos, so the merge was a fast-forward:
   `git merge --ff-only codex/platform-v1-power-final-03` (Linux: 37 commits; Reborn currently on branch
   `cpu-idle-completion`, 19 commits). Do it only after step 2, on a clean tree.
4. Verified at handoff: no detached worktree holds a commit that is on no branch. The only dirty one is
   the owner's `/home/luca/Dokumente/Code/worktrees/platform-v1-usb-final/Y2Linux` (4 owner files). **Do not remove it
   without the owner's explicit yes.**

### Must not be lost

- `codex/platform-v1-power-final-03` in both repos, then `main` after the fast-forward.
- 04 package, 04 symbols directory, `out/platform-v1-power-final/private/` (ask owner: keep or archive).
- `out/cpu-idle-completion-02-owner-firmware/`: **move it out of `out/`** (suggest
  `/home/luca/Dokumente/Code/Y2Linux-private/owner-firmware`), then update the path wherever documentation or a runbook
  names it. It is required by `tools/production/build.py --owner-firmware`.
- Stock firmware lives outside the repo (`/home/luca/Dokumente/Code/Y2Player/…`); do not touch it.

## Job 3 — the 11 parallel handoffs: INTEGRATED on 2026-10-06 (done)

All eleven `codex/platform-v1-<name>` branches plus `codex/highres-audio-completion` are merged into `main` in **both** repos, with
POWER-FINAL-03 as the baseline: on every collision 03's version wins, docs are unioned, nothing from 03 was overwritten.

How it was verified (repeat it if in doubt): for each branch, every code line the branch added relative to its fork point was searched
in the integrated tree (`lost-lines` check). Result: the branches were already integrated into 03's lineage in adapted form by an earlier
integration pass, so almost all of their code is present. What is genuinely new from the merge is small:

| Repo | New in main from the merge |
| --- | --- |
| Linux | AFE register lab (`tools/development/afe-lab`), audio observer, `generate_live` low-bit fixtures in `tools/platform/audio_precision.py`, `tests/test_highres_observations.py` (now in `tests.sh`), planning/validation docs and evidence |
| Reborn | `tools/build/precision-probe.c`, docs |

Proof that 03 is untouched: Linux `git diff ffddeb8 main -- kernel buildroot tools/production tools/connectivity initramfs tools/build tools/validation`
is empty; the only image-reachable file that differs is `tools/platform/audio_precision.py` (additive). Reborn code differs from 03 only by the new
probe file. The sealed 03 images therefore still correspond to `main`.

Final gates on the integrated trees: Linux production profile **515 cases** (511 plus 4 new), 10 skips, 0 failures; Reborn fmt, strict clippy and
all tests pass with the same counts as 03.

Per-branch outcome (Linux code that 03 already had in a newer form was kept; "absent" = branch lines not in the result, all superseded variants):

| Branch | Result |
| --- | --- |
| storage, wifi, bluetooth, highres-audio, suspend, input | code already in 03; docs added. Absent lines: 1-15 per branch (old `wait()` signature, `bt-control.ini` location, patch hunk headers) |
| usb | superseded by USB02: 36 of 2079 lines absent, all config/mechanics 03 changed after hardware validation. Kept 03's `usb.py`, `mtp-safe.*`, patch 0065, config |
| ffmpeg-metadata, library-db, graphics, reborn-performance | Linux side docs only |
| highres-audio-completion | **new tools and fixtures added** |

**Correction to an earlier statement in this file's previous version:** it said all 12 Reborn branches "merge cleanly". That was wrong: the Reborn repo has no
Git identity, so those trial merges aborted and the result was an artefact. The real Reborn merges (with identity from environment variables) had code conflicts
in `main.rs`, `input.rs`, `storage.rs`, `media.c`, the library and others. They were resolved toward 03 after checking that 03 already contains each feature in adapted
form (`TransferRefresh`/USB-triggered refresh, `input_resume`/`resumed()`, `pinned_folder_artwork`, `artwork_lowres`, `metadata_revision`, a superset
`main_loop_interval`). Three merges (ffmpeg-metadata, reborn-performance, input) had auto-merged partial hunks that did not compile against 03 (an `evdev_us` field
without producers, a duplicate `metadata_tests` module); those files were restored to 03 in a visible commit.

Not taken on purpose, because 03 does it differently and was hardware-validated or is the Product UI v2 policy: the usb branch's thread-based service wake,
its gadget `MaxPower`/storage-line mechanics, the input branch's Power key mapping to screen-sleep, reborn-performance's `evdev_us` input timestamps and simple loop
interval. If the owner wants any of them, port that single feature deliberately and re-run the gates. One optional small port: the usb branch's `tools/usb/qualify.py`
takes `/tmp/y2-platform-v1-device.lock` (03's does not).

**Branches are now merged, so cleanup may delete them:** `git branch --merged main` includes all of these in both repos. Keep the archive tags rule for anything still
unmerged. The earlier warning about not deleting these branches no longer applies.

## Job 2 — cleanup

State measured at handoff: `out/` is **325 GB in 303 entries**. Linux has 49 registered worktrees: the main tree, 19 under
`out/…-worktrees`, 16 under `/home/luca/Dokumente/Code/worktrees` (85 GB) and 13 under `/tmp/y2linux-*` (probably stale; `git worktree prune`
clears the missing ones). 35 local Linux branches. **Y2Reborn has its own 36 worktrees and 23 branches** (same procedure, same
locations). `Y2Reborn/target` is 4.1 GB; `Y2Linux/.cache` is 4.1 GB (**keep**, builds need it); `docs/` is 882 files / 16 MB.

### A. `out/` keeps only 04

Keep exactly: the 04 package, the 04 symbols directory, `platform-v1-power-final/private/` (owner decision).
Everything else goes, in this order (the 11 parallel branches live in the repo and in `/home/luca/Dokumente/Code/worktrees/`, not only in `out/`):

1. `git worktree list` — for each worktree under `out/`: `git worktree remove --force <path>`, then `git worktree prune`.
   Never `rm -rf` a registered worktree first; that leaves dangling registrations.
2. Delete old builds and packages: all `*-build`, `*-package*`, `y2linux-*` directories except the 04 pair above
   (includes POWER01, 02, 03, USB02 and baseline packages; 04's `fallback/` already carries the 02 pair, which is what the device runs today).
   **Consequence to state to the owner:** rolling back further than 02 will need a rebuild.
3. Delete `out/power-final-documentation` last, only after Job 0 steps 1 and 3 are verified. Its `out/power-final-04-build` (and the 03 build)
   can be deleted; a rebuild reproduces behaviour, not identical bytes, so the sealed package is the artifact.
4. Delete the remaining historical evidence trees and tmp directories (`*-validation`, `*-physical`, `*-overlay`, logs).
5. Result check: `du -sh out` is a few GB; `git status` in `Y2Linux` and `Y2Reborn` is clean (`out/` and `.cache/` are ignored).

### B. External worktrees and branches

- `/home/luca/Dokumente/Code/worktrees/*` (16 worktrees, 85 GB): same removal procedure per worktree. Skip `platform-v1-usb-final` until
  the owner decides about its 4 dirty files.
- `git branch --merged main` lists branches safe to delete (now including the 11 integrated ones). For any branch **not** merged (for example
  `wip/main-dirty-docs-2026-10-06`), create `git tag archive/<branch> <branch>` first, then delete the branch only if the owner agrees.
- Reborn: delete `target/` (rebuilds in minutes), keep `vendor/`; remove stale `out/` (27 MB).

### C. Documentation consolidation (882 files)

Current layout: `docs/validation` 48 files, `docs/release` 17, `docs/hardware-evidence` 31 dated directories,
`docs/knowledge` 86, `docs/architecture` + `docs/build` 74, plus `docs/planning` where
`roadmap-gap-audit.md` alone is **5382 lines** (every audit appended at the top) and
`CURRENT_PLATFORM_STATE.md` (372), `DOCUMENTATION_CATALOG.md` (396), `KNOWLEDGE_BASE.md`, `README.md`.

Principle: keep one current truth per topic, push history to Git, never delete what code or tests read.

1. **Tag first:** `git tag archive/docs-pre-cleanup-2026-10-06 main` so anything deleted stays recoverable.
2. **Files that tools and tests read — keep or retarget the reader in the same commit:**
   `docs/release/Y2-COMMUNITY-TESTER-GUIDE.md`, `Y2-COMMUNITY-SOURCE-DELIVERY.md`, `Y2-COMMUNITY-BETA-IMPLEMENTATION-PASS.md`
   (`seal_sources.py`); `docs/architecture/production-install.md`, `reborn-ffmpeg9-build.md`, `production-partitions.json`,
   `update-model.md`, `production-recovery.md`, `production-storage-v1.md`, `bluetooth-codecs.md`, `dependencies.json`;
   `docs/knowledge/evidence/gpu-source-contract.json`, `m5-firmware-inventory.json`;
   `docs/hardware-evidence/2026-09-13-storage05-owner/readback-corrected-analysis.json`,
   `docs/hardware-evidence/2026-09-18-gpu01/audio.txt` (`system_update.py`, `tests/test_emmc_layout.py`);
   `docs/validation/Y2-STORAGE-CEILING.md`; `docs/ui/previews/v2/boot-layout.json`; `docs/DOCUMENTATION_CATALOG.md` is read by
   package inventory code (check with `grep -rn DOCUMENTATION_CATALOG tools tests`).
   Run `grep -rhoE "docs/[A-Za-z0-9_./-]+" tools tests | sort -u` again before deleting; this list may be incomplete.
3. **Proposed target structure:** `README.md` (entry), `STATE.md` (single current platform state, replaces
   `CURRENT_PLATFORM_STATE*.md` and the per-candidate index), `architecture/`, `hardware/` (knowledge consolidated per subsystem:
   power/battery/charging, CPU idle and suspend, storage, USB, display/GPU, audio, Wi-Fi/Bluetooth, input), `validation/` (one current
   report per subsystem, the 39-section power report kept whole), `release/` (Community beta set), `planning/` (one roadmap, one
   *current* gap audit).
4. **Consolidate rather than delete where the content is still true:** the 5382-line gap audit becomes a current audit (status table
   per issue #28–#34) plus an archive pointer; per-candidate validation reports (`Y2-CPU-FINAL*`, `FIX01/02/03`, `M5 connectivity01..`,
   storage diag, hardware01/02, USB02, POWER01) fold into the subsystem report's "history" paragraph with commit/hash references.
5. **Delete as stale:** superseded per-candidate reports, dated `hardware-evidence/*` directories nothing references, duplicated
   candidate indexes, `CURRENT_PLATFORM_STATE.entry-2026-09-23.md`, and the old catalog rows. Evidence referenced from a kept document stays.
6. Rewrite `DOCUMENTATION_CATALOG.md` from the final tree (script it: it is generated knowledge, not prose). Update every link.
7. Verify: full host test run in the container (`tools/build/run.py … tools/production/tests.sh`, expect 515 cases, 10 skips, 0 failures),
   `git grep` for dead `docs/` paths, then one commit per step so each deletion is reviewable.
8. Same pass for `Y2Reborn/docs` and its `readme.md`.

Decisions needed from the owner (ask once, early): the dirty `main` docs, the USB owner worktree, keeping/archiving the private
evidence, and whether to keep POWER01/02 packages anywhere outside `out/`.

## Job 1 — hardware validation of 04 (after the owner flashes)

Take `/tmp/y2-platform-v1-device.lock` first (`flock -n … sleep N &`; release by killing that PID, not `pkill -f`). The classifier asks for explicit
user consent before launching scripts that write on the device: say what will run, then run it.

1. **Identity:** `/etc/y2linux/versions.json` = release `…candidate.4`, build `…POWER-FINAL-04`, kernel `…power-final-04`, Linux
   `5aeba051…`, Reborn `8cd365da…`; boot id, taint 0. The live symlink `/usr/bin/y2-platform` disappears with the new root: after the flash
   `ls /usr/bin/y2-platform` must fail while Power still works, which proves the Reborn path fix.
2. **Smoke gate, DAC, supervisor:** repeat `power-session/dac-readback.sh` and `proc-rates.sh` (they passed on 02).
3. **Suspend (the main goal):** run `power-session/suspend-session.py` (README). After the recovery boot read:
   `cat /sys/firmware/y2_pm/state /sys/firmware/y2_pm/devices`; look for `thaw_stall`, `S:<comm>`, `D:<comm>`, `thaw_blocked`, `I:…mmc` entries.
   Each `S:`/`D:` entry's number is a kernel address: resolve it with
   `awk` on `out/y2linux-platform-v1-power-final-candidate-04-symbols/System.map` (use the map that matches the running kernel; 03's map is not interchangeable) (nearest lower symbol). Then
   `mount -t pstore pstore /sys/fs/pstore; ls /sys/fs/pstore` — a `console-ramoops*` file means DRAM survived and gives the full dmesg of the
   stalled boot (enable `/sys/power/pm_print_times` and `pm_debug_messages` first). `oops_pc`/`oops_lr`/`panic` entries mean a crash,
   not a hang. Hypothesis to confirm or kill: storage I/O blocked after reset-return (`filesystems_thaw` waiting on `s_umount`
   while a task is stuck in `mmc_wait_for_req`), eMMC controller state not restored. **Fix the cause, do not skip thaw.** Backstop maximum is 30 s.
4. **Wi-Fi idle policy:** battery, dark, Wi-Fi on: after about five minutes C3 entries must appear (`cpuidle/state2/usage`), Reborn event log
   `idle_power_down`; screen wake must restore Wi-Fi without touching `/data/network/enabled`.
5. **Remaining matrix:** Bluetooth connected idle vs C3, missing Bluetooth peer (owner switches headphones off), Power then RTC wake cycles
   (5, then 10) once a same-boot resume exists, PC and wall charging and source transitions (ask the owner to connect the wall charger),
   5/30/120-minute idle, then an overnight procedure. Report programmed ceilings, never measured mA.
6. If kernel or root changes are needed: accumulate fixes and build **one** `POWER-FINAL-05` (see
   `~/.claude/projects/…/memory/y2-power-candidate-build-lessons.md` for the exact build, package, validate and seal commands and the
   `.cache` pitfalls). Never flash, never push.

## Facts that are easy to get wrong

- Backstop range is 10..30 s. A reset is a failed suspend, never a resume.
- C3 is gated by an active charger, so any window with USB attached shows no C2/C3.
- Associated Wi-Fi blocks C2/C3 (APDMA bit 11, BTIF bit 20); radios-off battery windows give about 74% C3.
- Voltage slopes mix relaxation with load. There is no current sensor.
- The idle-bias fix means the codec is already down at suspend, so the old regcache stall cannot recur; the new stall is later.
- Tests run in the project container (`python3 tools/build/run.py --output <build> -- sh /project/tools/production/tests.sh`); the host lacks
  `qemu-arm` and `pyelftools`, so about 58 host-suite errors are environmental.
- Commit with `GIT_AUTHOR_*`/`GIT_COMMITTER_*` = Luca `116190857+SchulzCode@users.noreply.github.com`; never change git config, never add attribution.
