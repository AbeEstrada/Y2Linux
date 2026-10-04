# Y2 + Reborn Platform 1.0 master report

Review cutoff: 2026-10-04T14:24:19.143470+00:00. **INTEGRATION_IN_PROGRESS**.

The master found eleven independent paired subsystem sessions and is doing
integration review only. No subsystem tree, ref or index was modified. Initial observation performed no build/hardware test/merge. The refreshed
activation audit now admits master-owned isolated integration trees; no main merge,
flash or push occurred. See the
[live status](Y2-PLATFORM-V1-INTEGRATION-STATUS.md) for every branch/HEAD/path,
dirty state, changed files, contract, tests, evidence, dependencies and candidate;
the [plan](Y2-PLATFORM-V1-INTEGRATION-PLAN.md) records C01–C30 and merge order.

## Overall Platform 1.0 state

The protected source foundation is Linux `b5aea937a3b8e3e8ec398f8cb2e04656b8a53f8c` and
Reborn `b71b468860233faa0a42b8448ec5777fa952b8e3`. Reborn main at `7f9df397` lacks the
scanout-release commit; preserve it. All eleven session histories retain the
foundations. Independent drafts have not become one selected implementation.

Owner receipts identify **installed Baseline02** (compiled Linux `8584ccd8`,
Reborn `b71b4688`, root v1.21). Radio/storage/DB/graphics measurements belong to
boot `27e6d684-3794-4490-95db-a489027cd4f4`, taint 0. The later single RTC full
sleep trial recovered through a watchdog reboot to
`88b85fa3-2282-4d93-b0b8-818a105ddd0a`, also taint 0. Retained SRAM stops at
DEVICES_RESUMING, wake 0x20, full PCM 596 and reset stamp 0x59325253, with no
complete/exit mark: **FAIL, not a same-boot resume**. Post-reboot aligned direct
reads of both 64-KiB scratch fixtures match and root/data/SD ext4 counters are
zero; this is reboot recovery, not suspend restoration. Raw owner receipts are
immutably archived in the 13:11 inventory snapshot’s suspend-baseline02-rtc-failure
folder. New suspend source was not installed; its acceptance remains open.
Master has not contacted the device. Baseline02 automatic C3 qualification
remains an independent gate; prior bounded CPU/storage evidence is retained.

The [UART01 physical receipt](../validation/Y2-CPU-C3-UART-PHYSICAL.md) protects
bounded C1, C2 84.3473%, C3 65.2450%, 21 guarded trials and 3,647 successful
entries/resumes, same boot and zero checked restore faults. It does not qualify
full-system suspend, electrical battery savings or future integrated images.

Protected-path review at the cutoff finds only suspend modifying Linux `spm.c`:
its new context checks target full-system entry, plus checked BIU/normal-PCM/
timer/CIRQ restoration and shared quarantine on failure. The DORMANT finisher
branch retains the existing timer/stash/flush/WFI/abort contract; other inventoried
idle/UART/timer/boot-policy paths are untouched by the eleven owners. USB's
Buildroot defconfig addition is MTP, with existing dependencies retained.
This is source preservation evidence, not an integrated physical pass; shared
SPM/config/package effects still require fresh C1/C2/C3 regression.

## Active and finished sessions

Bluetooth has a clean paired software handoff at Linux `5846a7a0a133` /
Reborn `de092094c27a`. Its owner verdict is MORE_WORK_REQUIRED for actual changed
binary/peer/audio qualification; do not call it Platform 1.0 finished. Master
source disposition is ACCEPT_WITH_INTEGRATION_ADJUSTMENT for safe diagnostic
composition, subject to final complete-diff/source review before cherry-pick.
No code has been integrated.

High-resolution audio has a paired software handoff at Linux `71631818` (implementation `d9595d6f`) /
Reborn `cd5d2430`; its MORE_HARDWARE_EVIDENCE_REQUIRED verdict keeps wider native
modes disabled. Documentation-only 71631818 corrects its research diagram to include the live
post-conversion f64 VolumeRamp; unity-volume fixtures do not prove every gain/DSP
state. This is a documentation correction, without reopened implementation scope. Input has refreshed paired software and userspace candidate
`95ed509` / `e51a335`, with 257 workspace tests and malformed-key cancellation.
Owner requested session closure after a zero-event observation; its final closing
report is now committed at Linux `8b58030`. Counted acceptance remains MORE_WORK_REQUIRED, and no changed
binary was executed. The master removed its reserved physical slot.

Wi-Fi has a clean paired source handoff at Linux `78c35124` / Reborn `2cdb9cce`;
its after-policy hardware and wider acceptance remain PARTIAL.
Graphics has clean paired final handoffs `383234de` / `a2df691e`. Reviewed durable
receipts prove bounded Baseline02 awake/off/wake behavior and temporary native ARM
JPEG benefit, with the static redraw defect and broader acceptance left PARTIAL.
Reborn performance has an admission-only Linux commit and Reborn implementation
`b8c05db` plus wired pacing `069415a`. Its exact final-binary matched device and supplemental controls pass
is reviewed; clean closing Reborn7ed4a406/Linux949b78ce completes the handoff. USB has a clean paired software handoff and a sealed
subsystem candidate; closing `1115933` also freezes later qualification metrics:
owner `08019df` and fresh source-bound ARM/package receipts
supersede the earlier openat2 header build failure (C23). Physical desktop gates
remain open; this is not the master RC.
Suspend has clean paired final source/evidence handoff `2d2b543` / `c57a55f`,
including codec source `a69bd50`. Installed Baseline02 full RTC FAIL is retained;
new kernel/handshake is software validated and PHYSICAL_NOT_RUN. FFmpeg has a clean paired software handoff with 252 host and
32 media/30 library ARM QEMU tests; physical scan/playback is NOT_RUN.
Storage has a final clean paired handoff at Linux `3a6b5f3` (implementation
`2a603c1`) and Reborn `f726ae40` playback guard following `ee1c25a`. Its completed 1k
stock DATA/SD corpus receipts are also preserved by FFmpeg c9ef7902/e709ecc.
Library DB has clean paired final handoffs `cdbdfe8` / `c7a8786` and saved bounded
native 1k/10k/50k measurements; no whole-app/endurance acceptance follows.
All eleven clean paired source/software handoffs are now available. Performance
closing reports and supplementation are complete; highres documentation correction
is complete without reopened implementation. Check the status cutoff before using these
lifecycle labels; commits alone never finish a session.

## Product area coverage

| Area | Current authority / integration condition |
| --- | --- |
| CPU, C1/C2/C3, timers/hotplug | Protected foundation and exact UART01 receipt; audit shared SPM/config/scanout changes; qualify the integrated image |
| Full suspend/resume | Suspend owner; same-boot complete restore remains open; ordinary unqualified product requests stay refused |
| Battery/charging/thermal | Existing policy, no independent new owner discovered; preserve charging refusal and verify cross-subsystem/endurance conditions |
| Storage/filesystems | Storage owner; stable live identity and persistent catalog upgrade need C07/C19 |
| USB/install observer | USB owner; MTP + ECM/configfs changes, desktop acceptance and recovery/observer availability pending |
| Wi-Fi/Bluetooth/codecs | Separate policy owners; shared daemon wait, diagnostics and coexistence; changed Bluetooth binary/real peer still unqualified |
| Wired/high-resolution audio | Audio precision owner; S16 44.1/48 fallback preserved; wider MT6582 path requires exact hardware evidence |
| FFmpeg/metadata/playback formats | Media owner; one paired native ABI and bounded decoder; combine with precision/graphics/DB |
| Library/database | DB owner; catalog completeness, bounded scanner and durability; preserve IDs and avoid duplicate old-card catalogs |
| GPU/display | Graphics owner; current DRM/Lima/runtime-PM retained, artwork overlap selected once |
| Input/wheel | Input owner; timing/rebind/overflow fixes; reconcile Power and performance, counted acceptance pending |
| Reborn performance/application | Performance instrumentation owner; compose one event loop/catalog/scanner; reject its stale Bluetooth polling hunk |
| Boot/shutdown/update/recovery | Existing foundation, no separate live owner discovered; verify shared gadget/sleep/app effects and preserving package/fallback |
| Diagnostics/release composition | Master composition concern; fixed safe schema, one candidate identity, source/notices/privacy and feature inventory gates |

## Accepted, rejected and unchanged work

Accepted into integration: **none**. Final selections require finished owners and
semantic reconciliation. Bluetooth's software work is provisionally suitable;
its physical gates remain open. Wi-Fi's reviewed source is provisionally suitable
after shared wait/diagnostic composition; no after-performance claim. Audio's source additions are provisionally
suitable with diagnostic/media composition; no native wider mode is accepted.
No branch was rejected wholesale or deleted. Reject performance's weaker
Bluetooth polling hunk in favor of the completed Bluetooth owner worker.

Duplicated implementations detected: FFmpeg and DB incremental scan/reuse;
FFmpeg and graphics reduced JPEG decode. Keep one DB-owned scanner and one
selected bounded media artwork path. Input/performance also duplicate timestamp names (`kernel_mono_us` versus
`evdev_us`); choose the input-owned monotonic/provenance contract. Independent
report/roadmap insertions are
documentation duplication, not eleven new feature authorities.

Preserve good unchanged behavior: GPU/Lima/DRM runtime-PM and scanout architecture;
Bluetooth controller/CONSYS ownership and conservative reconnect budget;
Wi-Fi fullmac/supplicant/DHCP ownership and disabled broken checksum offload;
native S16/44.1/48 fallback; battery/charging/thermal policy; immutable fallback,
Y2DATA/protected partitions and recovery. Highres owner has not established an
exact wider MT6582 fetch/interconnect contract, so native highres remains an open
requirement rather than a guessed enablement or an invented silicon ceiling.
These are current preservation decisions, not final no-change acceptances of
all active sessions.

## Outstanding conflicts and interfaces

Confirmed text conflicts: shared Linux readiness wait (USB/Wi-Fi), Reborn library
scanner (FFmpeg/DB), native JPEG artwork (FFmpeg/graphics), physical Power/input
router (input/suspend/performance). Temporary-copy checks leave live worktrees untouched.

Further semantic risks: one Reborn app/catalog/scanner/event loop; storage
`diskseq`/mount lifetime and MTP eject; union of safe diagnostic fields; paired
C/Rust media ABI; full-suspend shared SPM normal firmware/restore/broken-state;
Buildroot dependency/config/source version and kernel patch digest composition;
USB auto-refresh must not launch a scan after suspend preparation acknowledgement.
Performance's new asynchronous watchdog observations can also launch scans when
results reach the UI; compose their cancellation/freshness with prepare/restore
and storage lifecycle (C25), without adding a second hardware authority.
Collection-art composition must retain FFmpeg sidecar freshness and performance's
successful-insert-only cache eviction, with one bounded worker/cache (C27).
The pure combined diagnostic probe confirms lost/redacted new public telemetry; Wi-Fi 7056977 partly resolves its observation fields/enums, while USB/sleep/bonded composition remains open;
storage’s UUID+CID upgrade intentionally retains legacy rows offline and requires
one rescan/new queue selection. Reviewed UI catalog filters online tracks, so
those legacy rows are already excluded from normal browsing. Preserve that safe
policy and no old-Track rebind; verify saved-queue refusal, count/memory and total
resident-catalog capacity when old plus new rows coexist (C19). Storage and DB duplicate its parsing helper. FFmpeg's additive
metadata-revision migration/reuse must enter the DB-owned scanner (C24).
Storage `f726ae40` supersedes the confirmed `ee1c25a` path-only decoder gap
and the first dirty nested-symlink defect. Reviewed source walks root/parents/
regular file with no-follow and device/mount checks, holds file and parent FDs
through decoder close, and pins queued tracks and sidecars. All 33 valid audio
fixtures retain metadata/first PCM/position, with identical JPEG/PNG/WebP pixels
through suffix-free FDs and special-file refusal. The bounded artwork signature
fallback adds a fourth owner to native media composition; preserve FFmpeg limits
and graphics behavior. Combined-media/source/suspend regression remains open,
and new source is PHYSICAL_NOT_RUN (C26). FFmpeg owner review adds semantic
metadata equality (timing counters separate) and case-insensitive/corrupt-fallback
sidecar selection through the pinned parent to the combined regression list.
USB's earlier installed-UART01 assumption is corrected by 6fcd1b2; retain the dated
receipt as historical evidence and current Baseline02 identity separately.
Performance changes native shaders/batching with exactly49,152 bytes of staging.
Its final source-bound comparison contains ten benchmark screen readbacks:600 of
6,912,000 channels differ (0.0087%), maximum5/255, small antialias/interpolation
differences. Live covers are excluded from those pixels. Preserve that honest
near-equivalence and require integrated render/capture regression. Graphics closing receipt corrects stale SDK 9.0.1 wording to verified
9.0.2 and binds the tested membrane hash; its device runtime version was not
independently captured (C22). Canonical contract choices are documented,
**not implemented/reconciled yet**.
Keep existing `negotiated_codec` authoritative; intent names remain distinct.
Proposed Power contract follows the suspend owner's reported explicit requirement:
long hold opens the existing shutdown confirmation, short paused Power requests
qualified sleep/wake and playing Power blanks. Input owns raw normalization and
typed cancellation; its older QuickSettings-on-Power expectation must be reconciled
once. This contract selection is documented for integration, not yet shipped.

## Hardware and release blockers

- Final integrated-image boot policy and protected C1/C2/C3 regression.
- Genuine same-boot full RTC/Power suspend/wake and all subsystem restoration:
  single Baseline02 RTC trial failed; retained codec resume entry has no leave.
- USB desktop MTP/copy/disconnect/eject behavior with one filesystem owner;
  generated openat2/syscall headers must remain valid in the integration build.
- Final Wi-Fi readiness/transfer and changed Bluetooth worker/runtime/peer/codec
  evidence. Owner reports no headset currently available; coexistence/audio stays
  NOT_TESTED until one is supplied for the actual campaign.
- Native highres exact-SoC fetch/interconnect and independent bit/clock proof;
  admitted native output remains S16 stereo 44.1/48 kHz.
- Current-image storage/filesystem modes/hotplug, new renderer batching equivalence/performance, display/brightness/boot/shutdown,
  counted wheel/buttons, library/durability and measured performance.
- Charging/battery/thermal/electrical and representative actual workload endurance;
  short samples and passive collectors do not prove these.
- Corresponding source/notices/collector gaps, owner firmware redistribution,
  private calibration exclusion, optional codec distribution review, exact fallback
  and private-state-free package composition. New MTP dependencies need inventory.

These preserve the existing [233-feature release inventory](Y2-COMMUNITY-BETA-FEATURE-AUDIT.md)
and its implementation/software/physical/hardware/distribution distinctions.
No required feature is silently dropped. No new legal clearance is claimed.
Read-only GitHub refresh on 2026-10-04 confirms #16/#27/#28/#29/#31/#32/#33/#34
OPEN and historical #30 CLOSED since 2026-09-15. That planning closure does not
qualify physical full resume; the new failed RTC receipt keeps this release gate
open. No external issue state or comment was changed by master.

## Current integration order and candidate

0 foundations; 1 shared kernel review; 2 storage; 3 USB; 4 Wi-Fi/service loop;
5 Bluetooth; 6 precision/media; 7 DB scanner reconciliation; 8 graphics/performance;
9 input; 10 paired Reborn/full sleep; 11 release composition and broad validation.
Targeted tests follow each coherent step. The order can split coherent commits
when final dependencies require it; no blind branch history merge.

Integration branches `codex/platform-v1-integration`: **NOT_CREATED** while
selected owners are active. Integration commits: **none**. Fresh integrated
global software results: **NOT_RUN**. The retained Baseline02 software receipt is
391 production cases (386 pass/5 dependency skips), 125 focused source tests,
27 native filesystem/GIO, 3 ALSA, 238 Reborn, ARM/QEMU/ELF/package checks; those
counts are historical, not this master pass or an integrated RC result.

Platform v1 integration candidate:
`out/y2linux-platform-v1-integration-candidate/` — **NOT_BUILT**.
BOOTIMG SHA256: **not available**. Y2ROOT SHA256: **not available**.

Existing Baseline02: `out/y2linux-baseline-02-candidate/`, compiled Linux
`8584ccd85f052f351fe51650b2348c83ca894ed4` / Reborn
`b71b468860233faa0a42b8448ec5777fa952b8e3`; manifest-recorded hashes:
BOOTIMG `5d8a2999368a04b23b898d2106b465eb6b028c2314da1a39c66c6b26dc8c41a3`;
Y2ROOT `3148bea2b6d78be34afcbb9cd933502f14416e81c8053324ff6c9ea151ee3892`.
They are **not** the integration-candidate hashes and were not rehashed in this
read-only audit. Prior candidates remain retained and indexed by status report. Fresh storage mode/read/reinsert evidence is preserved as bounded Baseline02 observation; it does not automatically admit faster modes or qualify the integrated RC.
Input also produced an uninstalled ARM-userspace candidate, with no BOOTIMG or
Y2ROOT. Its source/binary hashes are indexed separately; it is not a final release.
USB's sealed `out/y2linux-platform-v1-usb-candidate/` is also a subsystem candidate,
compiled `08019df` / `51d477b`; its exact hashes are indexed by status. Neither is
renamed or promoted into the master candidate.

## Device coordination record

Master made no device connection or lock acquisition. Read-only host process,
lock and thread-ID metadata identified graphics PID `2284716` as the persistent
reservation holder. Its age alone did not establish abandonment. At owner
requests, master asked for normal safe batch completion/release; no process was
signalled and no lock file was removed or changed. Graphics reports release;
performance reports admission at 12:02:52 UTC and restoration/release around
12:08 UTC. Those messages coordinate access, not physical qualification evidence.

Storage reports that input PID `3196160` acquired next, while its nonblocking
attempt remained unsuccessful. Master requested an explicit storage gap after
input's safe release and notified performance/DB to avoid queued blocking-waiter
starvation. No slot is assumed granted and no test is marked run until owner
receipts show actual lock admission, source/binary identity and restoration.
Input subsequently reports safe release after a zero-event observer window;
that is not counted-input acceptance. A previously queued DB waiter then reports
normal admission before storage. Master asked DB to finish safely/release and
input/performance/suspend waiters to defer for storage's next agreed gap. No
active benchmark is interrupted and no reported availability is treated as a
guaranteed kernel-lock grant.
Suspend reports a pre-existing explicit owner reservation and withdrew its waiting
claim only for storage's final cleanup. The requested sequence became DB safe
release, storage, reserved continuous suspend, input, performance. Input later
reported an owner request to close and removed its slot; the current requested
sequence is DB → storage → suspend → performance. All admissions remain actual
nonblocking flock checks; messages do not acquire a lease.
DB subsequently reports both 50k stages completed and normal release/owned cleanup;
master relayed availability to storage. Physical benchmark numbers await the final
saved report, source/binary identities and restoration receipt before admission.
Storage subsequently reports both 1k mixed-corpus stages passed, owned scratch/
harness cleanup, unchanged mounted modes/services/settings and same boot/taint0,
then actual normal release. Master relayed that release to the reserved suspend
owner and asked performance to remain deferred. Durable corpus receipts reviewed via FFmpeg’s source-bound compact evidence show
all 1,000 stock files indexed/reused on DATA and SD with zero failures/controller
fault deltas. Source/binary identity remains Baseline02, not the new playback guard.
Suspend then reported actual nonblocking admission at 12:48 UTC and is establishing
the independent observer before any requested cable unplug. Master remains offline.
Performance initially had no queued waiter and remained deferred until release.
The ensuing one-shot full RTC trial failed through watchdog recovery/new boot;
owner then completed integrity/cleanup and actual normal release, without a
second deep trial. Master relayed that release to performance, which must acquire
nonblocking and repeat its preserved baseline on the new boot before its candidate.
Master’s retained-ring review identifies unmatched CS43131 1-0030 resume entry
7407; the owner corrected its initial all-callbacks-returned inference and is
reviewing that exact driver offline. A final root cause/fix is not established. Suspend plans narrow codec PM
substep notes and failed-suspend rollback repair in patch0030 (C28), with no
AFE/highres/DSP redesign or new hardware trial. Final a69bd50/2d2b543 codec diff and
executed fault tests are reviewed; normal ARM build passes. Semantic integration
and future exact-image physical proof remain required. Performance subsequently reports actual
nonblocking admission at 13:19 UTC on the new boot, with independent identity/
policy/integrity readmission and preserved baseline followed by b8c05db candidate.
The matched b8 run passed per owner report. Its subsequent untimed audio syscall
trace motivates a write-size probe and possible bounded ALSA pacing change (C29);
no old binary result qualifies a later change. Current extra audio files are measurement helpers;
no playback pacing implementation hunk is present at the 13:32 source snapshot.
A later reviewed dirty hunk now defers a wired-only bounded wait after a partial
write to the next call, preserving accepted-frame progress and clearing wait state
after recovery/discard. Pacing is now committed069415a with audio-owner PASS_SOURCE_REVIEW bound to
that exact commit. Primary Git verifies the reviewed native.rs blob0580a345 is
identical to the committed file (SHA25678a1f816); patch and file hashes are recorded
separately after correcting a draft label. Ten executed fault/native tests support
the source contract, and final exact069415a ARM binarySHA7871ec67 has a matched Baseline02 device pass.
Whole-app playing CPU87.95→11.21% and audio-thread82.63→5.11% of one core,
with zero measured xruns/playback/FFmpeg errors. Controls and active shutdown
317.28ms pass; stock/data/policy/integrity restored on boot88b85fa3/taint0 with
normal lock release. Full243 workspace tests and lint/ARM build pass per owner. Master requested exact evidence and
audio-owner contract review without changing formats/buffers/gain or taking the device.
Primary summary/raw receipt/restoration archived in13:58 snapshot. The two-sample
Play/Pause KMS regression21.75→42.47ms is retained; the separate16resume/16pause phase-varied replay improves KMS p95
43.98→22.55/64.70→38.50ms. All32samples per side, trace drops0, xruns0,
playback/FFmpeg errors0; existing bounded logger drops15/13 are separate.
Supplemental JSON is archived in14:10 snapshot and primary figures preserved.
No app source changed. Normal lease release/restoration completed; paired closing
7ed4a406/949b78ce is clean and reviewed; master stays offline.

## Next owner action and readiness

**No owner flash/install action now.** All eleven source-frozen handoffs are
reviewed. The immediate master action is the refreshed boundary audit and paired
isolated integration branches, followed by owned semantic composition and
targeted validation after each step. A real headset is needed for later Bluetooth
qualification. One final integrated physical campaign will reuse unaffected
receipts and focus on cross-subsystem regressions, with minimal owner interaction.

Readiness: **INTEGRATION_IN_PROGRESS**. The final 16-item completion report,
one candidate and its exact owner installation step become available only after
required integration/software gates; PLATFORM_V1_READY additionally requires
required physical/endurance and distribution gates.
