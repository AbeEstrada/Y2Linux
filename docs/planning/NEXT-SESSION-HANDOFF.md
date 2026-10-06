# Next-session handoff — 2026-10-06 (delete this file when it has been consumed)

Two jobs, in this order. **Do not start the cleanup before Job 0 is complete.**

- **Job 0 — safety (10 minutes, mandatory first):** make sure no source history lives only inside `out/`.
- **Job 1 — hardware:** owner flashes POWER-FINAL-03, validate it, locate the suspend stall.
- **Job 2 — cleanup:** `out/` keeps only 03, documentation is consolidated, both repos end clean.

Job 1 and Job 2 are independent. If the owner has not flashed yet, start Job 2 (after Job 0).

## Paste-ready prompt

```
Read /home/luca/Dokumente/Code/Y2Linux/docs/planning/NEXT-SESSION-HANDOFF.md completely
(on branch codex/platform-v1-power-final-03 until it is merged), then do Job 0, then Job 2
(cleanup) and, once I confirm POWER-FINAL-03 is installed, Job 1 (hardware validation).
Do not flash. Do not push. Preserve Git identity (Luca) via environment variables and add no
model attribution. Never delete anything listed under "Must not be lost".
```

## Is 03 the newest image with every fix I proposed?

**Yes, it is the newest image and contains every fix that was implemented.** It was built from
clean commits, packaged, validated and sealed. It has **not been flashed**; the device runs
POWER-FINAL-02. It is not "everything proposed": the table is exact.

| Item | In 03? | Evidence |
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
| Source, Linux | branch `codex/platform-v1-power-final-03`, compiled `ffddeb8`, head `1ca3673` plus later docs/harness commit. **Saved into the main repo** at `/home/luca/Dokumente/Code/Y2Linux`; the working clone is `out/power-final-documentation/Y2Linux` |
| Source, Reborn | branch `codex/platform-v1-power-final-03`, compiled `b2c460e`, saved into `/home/luca/Dokumente/Code/Y2Reborn` |
| Sealed 03 package (flash this) | `out/y2linux-platform-v1-power-final-candidate-03/` BOOTIMG `8872666c3f1e3fdcbded7b0bea5986c5653344623ce787ad741da6a415f691f6`, Y2ROOT `0ae0bd785ea0ca5009f5ec5487d055c6dc60223c049c4487ee3df2e1e18bed28`; `fallback/` is the exact 02 pair |
| 03 kernel symbols | `out/y2linux-platform-v1-power-final-candidate-03-symbols/` (`vmlinux`, `System.map`, `.config`): **needed to turn stall `wchan` numbers into function names** |
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
2. **Main working tree is dirty and belongs to an earlier session.** `main` has 7 modified docs
   (`CURRENT_PLATFORM_STATE.md`, `DOCUMENTATION_CATALOG.md`, `knowledge/candidate-index.md`,
   `planning/platform-v1-roadmap.md`, `planning/roadmap-gap-audit.md`,
   `release/Y2-COMMUNITY-BETA-FEATURE-AUDIT.md`, `…FEATURES.json`) and untracked
   `docs/release/Y2-PLATFORM-V1-{INTEGRATION-PLAN,INTEGRATION-STATUS,MASTER,PHYSICAL-QUALIFICATION}.md`,
   `docs/validation/Y2-PLATFORM-V1-INTEGRATION.md`, `tools/development/observe-platform-v1.py`.
   Save them first: `git diff > /safe/main-dirty.patch` and copy the untracked files. Then decide
   (owner) whether they are kept (merge into the consolidated docs) or dropped.
3. `main` is an ancestor of 03 in both repos, so the merge is a fast-forward:
   `git merge --ff-only codex/platform-v1-power-final-03` (Linux: 37 commits; Reborn currently on branch
   `cpu-idle-completion`, 19 commits). Do it only after step 2, on a clean tree.
4. Verified at handoff: no detached worktree holds a commit that is on no branch. The only dirty one is
   the owner's `/home/luca/Dokumente/Code/worktrees/platform-v1-usb-final/Y2Linux` (4 owner files). **Do not remove it
   without the owner's explicit yes.**

### Must not be lost

- `codex/platform-v1-power-final-03` in both repos, then `main` after the fast-forward.
- 03 package, 03 symbols directory, `out/platform-v1-power-final/private/` (ask owner: keep or archive).
- `out/cpu-idle-completion-02-owner-firmware/`: **move it out of `out/`** (suggest
  `/home/luca/Dokumente/Code/Y2Linux-private/owner-firmware`), then update the path wherever documentation or a runbook
  names it. It is required by `tools/production/build.py --owner-firmware`.
- Stock firmware lives outside the repo (`/home/luca/Dokumente/Code/Y2Player/…`); do not touch it.

## Job 2 — cleanup

State measured at handoff: `out/` is **325 GB in 303 entries**. Linux has 49 registered worktrees: the main tree, 19 under
`out/…-worktrees`, 16 under `/home/luca/Dokumente/Code/worktrees` (85 GB) and 13 under `/tmp/y2linux-*` (probably stale; `git worktree prune`
clears the missing ones). 35 local Linux branches. **Y2Reborn has its own 36 worktrees and 23 branches** (same procedure, same
locations). `Y2Reborn/target` is 4.1 GB; `Y2Linux/.cache` is 4.1 GB (**keep**, builds need it); `docs/` is 882 files / 16 MB.

### A. `out/` keeps only 03

Keep exactly: the 03 package, the 03 symbols directory, `platform-v1-power-final/private/` (owner decision).
Everything else goes, in this order:

1. `git worktree list` — for each worktree under `out/`: `git worktree remove --force <path>`, then `git worktree prune`.
   Never `rm -rf` a registered worktree first; that leaves dangling registrations.
2. Delete old builds and packages: all `*-build`, `*-package*`, `y2linux-*` directories except the 03 pair above
   (includes POWER01, 02, USB02 and baseline packages; 03's `fallback/` already carries the 02 pair).
   **Consequence to state to the owner:** rolling back further than 02 will need a rebuild.
3. Delete `out/power-final-documentation` last, only after Job 0 steps 1 and 3 are verified. Its `out/power-final-03-build`
   can be deleted; a rebuild reproduces behaviour, not identical bytes, so the sealed package is the artifact.
4. Delete the remaining historical evidence trees and tmp directories (`*-validation`, `*-physical`, `*-overlay`, logs).
5. Result check: `du -sh out` is a few GB; `git status` in `Y2Linux` and `Y2Reborn` is clean (`out/` and `.cache/` are ignored).

### B. External worktrees and branches

- `/home/luca/Dokumente/Code/worktrees/*` (16 worktrees, 85 GB): same removal procedure per worktree. Skip `platform-v1-usb-final` until
  the owner decides about its 4 dirty files.
- After the fast-forward: `git branch --merged main` lists branches safe to delete. For any branch **not** merged, create
  `git tag archive/<branch> <branch>` first, then delete the branch. Tags keep the history without worktrees.
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
7. Verify: full host test run in the container (`tools/build/run.py … tools/production/tests.sh`, expect 511 cases, 10 skips, 0 failures),
   `git grep` for dead `docs/` paths, then one commit per step so each deletion is reviewable.
8. Same pass for `Y2Reborn/docs` and its `readme.md`.

Decisions needed from the owner (ask once, early): the dirty `main` docs, the USB owner worktree, keeping/archiving the private
evidence, and whether to keep POWER01/02 packages anywhere outside `out/`.

## Job 1 — hardware validation of 03 (after the owner flashes)

Take `/tmp/y2-platform-v1-device.lock` first (`flock -n … sleep N &`; release by killing that PID, not `pkill -f`). The classifier asks for explicit
user consent before launching scripts that write on the device: say what will run, then run it.

1. **Identity:** `/etc/y2linux/versions.json` = release `…candidate.3`, build `…POWER-FINAL-03`, kernel `…power-final-03`, Linux
   `ffddeb8…`, Reborn `b2c460e…`; boot id, taint 0. Remove the live symlink `/usr/bin/y2-platform` only if you want to prove the Reborn fix:
   after the flash `ls /usr/bin/y2-platform` must fail and Power must still work.
2. **Smoke gate, DAC, supervisor:** repeat `power-session/dac-readback.sh` and `proc-rates.sh` (they passed on 02).
3. **Suspend (the main goal):** run `power-session/suspend-session.py` (README). After the recovery boot read:
   `cat /sys/firmware/y2_pm/state /sys/firmware/y2_pm/devices`; look for `thaw_stall`, `S:<comm>`, `D:<comm>`, `thaw_blocked`, `I:…mmc` entries.
   Each `S:`/`D:` entry's number is a kernel address: resolve it with
   `awk` on `out/y2linux-platform-v1-power-final-candidate-03-symbols/System.map` (nearest lower symbol). Then
   `mount -t pstore pstore /sys/fs/pstore; ls /sys/fs/pstore` — a `console-ramoops*` file means DRAM survived and gives the full dmesg of the
   stalled boot (enable `/sys/power/pm_print_times` and `pm_debug_messages` first). `oops_pc`/`oops_lr`/`panic` entries mean a crash,
   not a hang. Hypothesis to confirm or kill: storage I/O blocked after reset-return (`filesystems_thaw` waiting on `s_umount`
   while a task is stuck in `mmc_wait_for_req`), eMMC controller state not restored. **Fix the cause, do not skip thaw.** Backstop maximum is 30 s.
4. **Wi-Fi idle policy:** battery, dark, Wi-Fi on: after about five minutes C3 entries must appear (`cpuidle/state2/usage`), Reborn event log
   `idle_power_down`; screen wake must restore Wi-Fi without touching `/data/network/enabled`.
5. **Remaining matrix:** Bluetooth connected idle vs C3, missing Bluetooth peer (owner switches headphones off), Power then RTC wake cycles
   (5, then 10) once a same-boot resume exists, PC and wall charging and source transitions (ask the owner to connect the wall charger),
   5/30/120-minute idle, then an overnight procedure. Report programmed ceilings, never measured mA.
6. If kernel or root changes are needed: accumulate fixes and build **one** `POWER-FINAL-04` (see
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
