# Next-session handoff — current deep-sleep continuation, 2026-10-07

**This section supersedes the 2026-10-06 installed-image and next-action claims
below. Preserve this handoff and the evidence. Cleanup is outside the current
owner request; do not delete the active build, fallback, symbols or raw archives.**

- Actual installed firmware is **POWER-FINAL-04**, verified over SSH, not 02.
  Linux `5aeba051c428451483402e5874dcf8222afca259`, Reborn
  `8cd365da5f3454c8e3189df1434b966edbd06575`, root v1.30. Current diagnostic boot
  `404ef43c-1237-4eed-8c00-56210c9574a8`, taint 4096 from matching PM probes.
- Both primary repositories use `codex/platform-v1-deep-sleep-final`.
  Compiled successor source: Linux **`0c9b78c7903182861b84e7d90a536bd30fca295a`**,
  Reborn **`5a9f7586dd8d80ab5afc16c6a9a7e853e7469aeb`**. Later Linux commits may
  document results without changing compiled identity. Luca identity preserved.
- New owner package: `out/y2linux-platform-v1-deepsleep-final-candidate/`,
  **DEEPSLEEP-FINAL-01**, root v1.31. Read its `OWNER-HANDOFF.md`, manifest and
  SHA256SUMS. BOOTIMG `8a354eb0b9a9e65b3213ee83b1db53c9bd1174a52a9ea27233749c7d22c0cc16`;
  Y2ROOT `f84d1bc4a819f819f2f9b6f3593be00ba491b0ae17c5b6220f0024aea5b681e0`.
  Only BOOTIMG/ANDROID selected; Y2DATA preserved. Exact 04 fallback included.
  No flash performed. Adjacent `…-candidate-symbols/` retains matching symbols.
- Build vehicle: `/home/luca/Dokumente/Code/worktrees/y2-deepsleep-final/`
  with detached paired worktrees; Linux `out/deepsleep-final-build` contains the
  complete build. Seven existing firmware inputs were verified/recovered from
  the retained 04 target into `out/deep-sleep-final/owner-firmware/`; the old
  provisioning path below no longer exists. Do not invent calibration inputs.
- Software checks pass: 542 unique production cases (532 container + ten host
  dependency cases, zero remaining failures/skips), Reborn fmt/strict Clippy/
  332 workspace tests/fresh ARM, kernel/config/DT/module ABI/QEMU/package.
- Physical work and all 38 requested sections are in
  [the current report](../validation/Y2-PLATFORM-V1-DEEP-SLEEP-FINAL.md).
  Private archives: `out/deep-sleep-final/evidence/20261007/00-initial/` through
  `24-endurance30-repeat-return/`. Latest collection is complete and archived.
  Same-boot diagnostic returns: 14 (12 RTC, one Power, one USB). The 30-minute
  repeat accumulated 1811.835 s, four expected RTC wakes, no unexpected wakes,
  4.050439→4.013964 V; old SOC 86→86 is unsuitable for a drain pass. No 2-hour
  or full-suspend overnight measurement has been run or armed.
- Root cause of post-thaw hang: duplicate CPU/cluster PM saves overwrite core
  GIC interrupt enables after CIRQ masking; final core restore disables storage/
  timer IRQs. A matching diagnostic suppression establishes same-boot returns.
  Built successor gives core PM sole ownership and orders CIRQ replay after it.
  It also fixes cold-battery USB clock ownership, adds automatic owned sleep,
  fixes stale Reborn observations and uses BOOTTIME for unchanged SOC filtering.
- Open defects/gates: one intermittent DPM_PREPARED wait before CPU PM remains
  unlocalized; separate user-poweroff panic remains unfixed; built-in clean
  repetition, automatic sleep/inhibitors, cold-battery C3 and true endurance
  remain. Infrastructure/DDRPHY retention is not deepest power collapse; no
  measured mA/capacity or battery-degradation conclusion. No <=1% target pass.
- Next: owner verifies/install successor via preserving Download Only, then
  leave USB connected for identity/taint-zero archive. Do not autonomously flash.
  Stage PM and use one bounded real Power/RTC trial before repetition/long tests.
  Use BOOTTIME for gesture scheduling, generous RTC fallback and actual IRQ
  attribution. Prevent automatic policy racing the staged collector using an
  actually held activity lock; do not use a stale inhibitor file. Never load 04
  modules on the successor; current endurance script requires taint4096 and
  must not be reused unchanged. Archive pstore/PM/power before every reboot.

The standing [boundary audit](roadmap-gap-audit.md#successor-sealing-and-owner-installation-boundary)
and roadmap were refreshed. Issues #16/#27/#28/#29/#31/#32/#33/#34 remain open,
#30 closed historically; no remote mutation, push or release promotion.

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
