# Candidate and fallback identity index

## POWER-FINAL-17 — sealed 2026-10-13, not flashed

`Y2LINUX-PLATFORM-V1-POWER-FINAL-17`: compiled Linux `045911669740cbf5870795eccafb387b01db24c8` / Reborn
`217e28dfa3a66bbae6ea5983ee3355a132a4d73d` (unchanged); kernel `6.18.56-y2linux-platform-v1-power-final-17`, root
`2026.08-platform-v1.47`, release `1.0.0-platform-v1-power-final-candidate.17`. BOOTIMG
`2ddd8d384cf6d9336d1a3505944f6a787764e982f7327400b5e886a41ea52d9a`, Y2ROOT
`dc1f057a6c1d5768cbe3822893b5f71d3c3615bfbb3848e78491d9f0882a3e76`. Package
`out/y2linux-platform-v1-power-final-candidate-17/` (fallback = 16).

## POWER-FINAL-16 — installed 2026-10-12, Baseline 16 (2026-10-13)

`Y2LINUX-PLATFORM-V1-POWER-FINAL-16`: compiled Linux `a4e9c3b` / Reborn `f68e088d7de9591e13ff1925590ceb419d340625`
(unchanged); kernel `6.18.56-y2linux-platform-v1-power-final-16`, root `2026.08-platform-v1.46`, release
`1.0.0-platform-v1-power-final-candidate.16`. BOOTIMG
`2f1cd1c0091e2015afa2af6ffbd2f191f58090d3cbdc3b52f58a71ef5d6edebf`, Y2ROOT
`bd4a12a07b39f21c9313d82069014891e1e1707ffee9eb532e04cece69a43d9f`. Package
`out/y2linux-platform-v1-power-final-candidate-16/` (fallback = 15). First boot `0b0e8a77`; overnight boot `f871fd6a` (archive 110).

## POWER-FINAL-15 — sealed 2026-10-12, installed the same day (Baseline 15)

`Y2LINUX-PLATFORM-V1-POWER-FINAL-15`: compiled Linux `be1aac2123abbe68778aa52c8ae206c55cdf8a6e` / Reborn
`f68e088d7de9591e13ff1925590ceb419d340625`; kernel `6.18.56-y2linux-platform-v1-power-final-15`, root
`2026.08-platform-v1.45`, release `1.0.0-platform-v1-power-final-candidate.15`. BOOTIMG
`86dc957a6a74da5107d9e889bf48686acb904d3bab6510f6a83e461ed450844d`, Y2ROOT
`0b14b79445f160b4e07430386b5ca1b576bb7b04d793ef8ce3c09a8156d620ae`. Package
`out/y2linux-platform-v1-power-final-candidate-15/` (fallback = sealed 14).

## POWER-FINAL-14 — sealed 2026-10-11, not flashed

`Y2LINUX-PLATFORM-V1-POWER-FINAL-14`: compiled Linux `9d06ac4deb158183f56f845086aaa307ce836177` / Reborn
`63ac4a75286944ac0c57a2f15bb3b841923dd0f3`; kernel `6.18.0-y2linux-platform-v1-power-final-14`, root
`2025.02.18-platform-v1.44`, release `1.0.0-platform-v1-power-final-candidate.14`. BOOTIMG
`273dc927fbdb5778089ad76179ae92f8a32cb7625a83b39cc0850b572d7d3e5a`, Y2ROOT
`78203697a71be7669c9e6f88dedc3a6daa80cd8ff6876d35779e86bb6ba314b9`. Package
`out/y2linux-platform-v1-power-final-candidate-14/` (fallback = sealed 13).

## Baseline 13 / POWER-FINAL-13 — installed, published 2026-10-11

`Y2LINUX-PLATFORM-V1-POWER-FINAL-13`: compiled Linux `47c1cf225dc140d151366f9e6309a3a07556fa67` / Reborn
`71ddb0d523187d61035304d3ea5e42b70d63e357`; kernel `6.18.0-y2linux-platform-v1-power-final-13`, root
`2025.02.18-platform-v1.43`, release `1.0.0-platform-v1-power-final-candidate.13`. BOOTIMG
`f73c24da3abe5978f2c234bd9501a929415fc156fc5ab79ebc7755390dddc178`, Y2ROOT
`e62cb6c7bab621e6f791359e5b56bba3a21f065d2ba864f4917b3ae808c01915`. Maintainer package
`out/y2linux-platform-v1-power-final-candidate-13/` (fallback = sealed 12, BOOTIMG `f33fac4d…`, Y2ROOT `215892b5…`).
Published as tag `baseline-13`. Older "current"/"newest" labels below are historical.

## Newest independent Platform 1.0 baseline — 2026-10-04

`Y2LINUX-PLATFORM-V1-BASELINE-01`: compiled Linux `98daf3f0220f4a1580bb4893094ee9f0e02362a5` / Reborn `9cd12baeeb70b204e08299bd4c91c8c35604c304`;
root `2025.02.18-platform-v1.24`, kernel `6.18.0-y2linux-platform-v1-baseline-01`.
SOFTWARE_VALIDATED / INTEGRATED_PHYSICAL_NOT_RUN; owner-local physical qualification
ready, public distribution not ready. Baseline02 RTC FAIL remains open; UART01
CPU evidence/fallback is historical. Owner main and earlier candidates preserved.
Canonical candidate `/home/luca/Dokumente/Code/Y2Linux/out/y2linux-platform-v1-baseline-candidate`. Details in `docs/release/Y2-PLATFORM-V1-BASELINE.md`.
Older current/next labels below belong to their recorded observation times.

## Current integrated software candidate — 2026-10-04

Linux `4c72466f2f27ddf9f0ca18ba8ddc4d89c52599d2` / Reborn `dd73dcc3243045cd33e319dda2f76918ed37ea31`. One sealed `/home/luca/Dokumente/Code/worktrees/platform-v1-integration/Y2Linux/out/y2linux-platform-v1-integration-candidate`; kernel `6.18.0-y2linux-platform-v1-integration-01`, root `2025.02.18-platform-v1.23`. BOOTIMG `d2dec1a517a596861adb69b4c9aaab51e68d5caf46712a99dbd8607e9d8fbb06`, Y2ROOT `cd3c077fd6c4882c82b7c67c42266f5f0ddc04828ddc2af111434740153bd1dc`. **READY_FOR_PLATFORM_V1_PHYSICAL_QUALIFICATION**; physical/endurance NOT_RUN, owner-local/public distribution blocked. UART01 matching fallback is separate. See [master](../release/Y2-PLATFORM-V1-MASTER.md) and [software receipt](../validation/Y2-PLATFORM-V1-INTEGRATION.md). Older rows below are retained candidate history.

## Current sealed baseline — 2026-10-03

| Field | Sealed Baseline02 |
| --- | --- |
| Build | `Y2LINUX-BASELINE-02` |
| Candidate | `out/y2linux-baseline-02-candidate/` |
| Kernel | `6.18.0-y2linux-baseline-02` |
| Rootfs / release | `2025.02.18-platform-v1.21` / `1.0.0-baseline-candidate.2` |
| Compiled Linux | `8584ccd85f052f351fe51650b2348c83ca894ed4` |
| Compiled Reborn | `b71b468860233faa0a42b8448ec5777fa952b8e3` |
| ABI / feature contract / layout / data | 1 / 2 / 1 / 1 |
| Software / package | PASS |
| New-image hardware / automatic cold boot | PHYSICAL_NOT_RUN |

| Artifact | SHA256 |
| --- | --- |
| Baseline02 BOOTIMG | `5d8a2999368a04b23b898d2106b465eb6b028c2314da1a39c66c6b26dc8c41a3` |
| Baseline02 Y2ROOT | `3148bea2b6d78be34afcbb9cd933502f14416e81c8053324ff6c9ea151ee3892` |
| Baseline02 manifest | `122d6f5d73f3416a2608f770b1d05af5b0ba81db27c315639f56458833cc5654` |
| UART01 fallback BOOTIMG | `a35e7ccb11dfcc642089e422d48a274ab2c700dbba15d00b21cce7b463e4006a` |
| UART01 fallback Y2ROOT | `d3a8282a9f5d1b0046283bce1b595eb5797b62c2bff90a62260e80bbfafb5d98` |

The latest hardware receipt is **UART01**, kernel
`6.18.0-y2linux-cpu-c3-uart-01`, Linux `e9e8d63f9c94232c2b6627881e0967583e202dac`,
Reborn `b71b468860233faa0a42b8448ec5777fa952b8e3`, root
`2025.02.18-platform-v1.20`, boot
`fd955840-35d9-47db-83e0-ff47d6bb2d2b`, taint 0.
C1, C2 and C3 are physically working on that image. Baseline02 retains that
kernel architecture; its new image and automatic cold-boot activation remain
**PHYSICAL_NOT_RUN** until owner installation and the guarded checks.

The exact UART01 pair is included under `fallback/` in the Baseline02 package.
The package selects BOOTIMG and ANDROID/Y2ROOT; it does not replace Y2DATA or
protected partitions. Hashes are copied from retained seal receipts, not a new
build or physical readback. See [Baseline02](../validation/Y2-BASELINE-02.md),
[UART01 hardware](../validation/Y2-CPU-C3-UART-PHYSICAL.md) and
[current state](../CURRENT_PLATFORM_STATE.md). Historical candidate paths below
remain immutable and are not the current installation recommendation.


## Historical snapshots

The following text retains earlier dated decisions and results. Its “current”,
“next” and candidate labels belong to those sessions; the Baseline02 summary
above takes precedence. Historical failures and seal-time NOT_RUN receipts
remain evidence for their exact images.

---

# Candidate and fallback identity index

## Baseline02 sealed precedence — 2026-10-03

| Role | Exact source and artifact | Evidence |
| --- | --- | --- |
| Latest integrated candidate | `out/y2linux-baseline-02-candidate/`, Linux`8584ccd85f052f351fe51650b2348c83ca894ed4`, Reborn`b71b468860233faa0a42b8448ec5777fa952b8e3`, kernel6.18.0-y2linux-baseline-02/rootv1.21 | Fresh software/package checks PASS; automatic qualified C3 boot policy; new-image physical/cold boot NOT_RUN |
| Installed and exact paired rollback | UART01, Linuxe9e8d63/Rebornb71b4688, kernel6.18.0-y2linux-cpu-c3-uart-01/rootv1.20 | C1/C2/C3 physically WORKING;3647 C3 checked returns, zero restore/UART faults; same boot |

BOOTIMG SHA256 `5d8a2999368a04b23b898d2106b465eb6b028c2314da1a39c66c6b26dc8c41a3`; Y2ROOT SHA256 `3148bea2b6d78be34afcbb9cd933502f14416e81c8053324ff6c9ea151ee3892`.
[Sealed receipt and owner action](../validation/Y2-BASELINE-02.md).
Only BOOTIMG/ANDROID payloads; preserve Y2DATA. Old precedence/preparation and
candidate roles below are historical. No flash or push.

## Baseline02 preparation precedence — 2026-10-03

Newest requested package: `out/y2linux-baseline-02-candidate/`, build
Y2LINUX-BASELINE-02, kernel6.18.0-y2linux-baseline-02/rootv1.21. Fresh integrated
build/seal pending; owner-selected automatic guarded CPU0 C3 boot policy.
New-image physical qualification remains NOT_RUN. Installed and exact rollback
pair is UART01, Linuxe9e8d63/Rebornb71b4688, with physically working C1/C2/C3.
See [baseline record](../validation/Y2-BASELINE-02.md) and
[hardware qualification](../validation/Y2-CPU-C3-UART-PHYSICAL.md).
Older precedence and candidate roles below are historical, superseded here.

## Current audit precedence — 2026-10-02

The [master audit baseline](../release/Y2-COMMUNITY-BETA-FEATURE-AUDIT.md#2-exact-source--runtime-baseline) supersedes the older role labels below. At17:49:54 CEST: Linux `dcbd7d1` identifies candidate4 (build activity, no sealed/physical receipt reviewed); candidate3 `c5f0eec` is sealed and reported flashed/characterized in a concurrent draft; candidate2 is the prior installed pair; Fix02 remains the latest broad physical qualification. Reborn `b92d312` is unchanged. Exact hashes, source history and draft disagreements are in the audit; original historical receipts remain intact.

Updated 2026-10-01. This is an index to retained manifests and physical reports,
not a new package validation or a live-device read. The exact owner-flashed
Fix02 pair was observed on 2026-09-29. Later documentation HEADs are not the
commits compiled into it.

| Role | Source/runtime identity | Evidence and limitation |
| --- | --- | --- |
| Latest storage ceiling candidate 2 (unflashed) | Linux `4db6d6dee8e8b21d85f4f7dfa8e6b7aac82d5e56`; Reborn `b92d312cc2dc4b74f57a1a9a7b1407e34707137a` | kernel `6.18.0-y2linux-storage-ceiling-02`, root `2025.02.18-platform-v1.12`, release `1.0.0-storage-ceiling-candidate.2`; adds the SD rail PWRAP fields; BOOTIMG `5c17f744…`, Y2ROOT `dc611011…`; software-validated; [receipt](../validation/Y2-STORAGE-CEILING.md#first-device-check-and-candidate-2) |
| Storage ceiling candidate 1 (booted; eMMC HS200 OK, SD rails refused) | Linux `540ae029b13940d4b2dfe21902bed71b89cb117a`; Reborn `b92d312cc2dc4b74f57a1a9a7b1407e34707137a` | kernel `6.18.0-y2linux-storage-ceiling`, root `2025.02.18-platform-v1.11`, release `1.0.0-storage-ceiling-candidate.1`; eMMC HS200 / SD SDR104 ceilings with fallback ladders; BOOTIMG `4332d4f2…`, Y2ROOT `72eab34a…`; software-validated, physical NOT_RUN; [receipt](../validation/Y2-STORAGE-CEILING.md) |
| Product UI v2 candidate (unflashed) | Linux `5cfe04cb2fe9e1177df99f3113b7a17ee7d442f5`; Reborn `bd8436dd2afcdbe4a45b9140aa98e4d20307482b` | kernel `6.18.0-y2linux-cpu-final-fix03` (unchanged), root `2025.02.18-platform-v1.10`, release `1.0.0-reborn-product-ui-v2-candidate.1`; BOOTIMG `8a974cb5…`, Y2ROOT `a5c2914e…`; software-validated, physical NOT_RUN; [receipt](../validation/Y2-REBORN-PRODUCT-UI-V2.md) |
| Fix03 candidate (unflashed) | Linux `76a5d41df683a1680b1127393deb0101aafe7697`; Reborn `77cf83e09a18f82a867040e72d35b6e70b26fa85` | kernel `6.18.0-y2linux-cpu-final-fix03`, root `2025.02.18-platform-v1.9`, release `1.0.0-cpu-final-fix03-candidate.1`; BOOTIMG `c55b2640…`, Y2ROOT `04cafd4b…`; software-validated, physical NOT_RUN |
| Installed Fix02 pair | Linux `1a1a6693dcd82f62daecd4c1491ef512823a86c5`; Reborn `77cf83e09a18f82a867040e72d35b6e70b26fa85` | kernel `6.18.0-y2linux-cpu-final-fix02`, root `2025.02.18-platform-v1.8`; BOOTIMG `a621e270…`, Y2ROOT `5010d839…`; physical acceptance FAIL (awake CPU qualified) |
| Fix01 candidate | Linux `0de6e951b438bf0f2d701e23e476d2b2405ba3c6`; Reborn `36db1869c6bab1ad2d00b7d8e7807ea6ef5b3803` | kernel `6.18.0-y2linux-cpu-final-fix01`, root `2025.02.18-platform-v1.7`, release `1.0.0-cpu-final-fix01-candidate.1`; physical acceptance FAIL |
| Prior CPU Final tested pair | Linux `ff586dfff2b5e7abd28af339c055375307308f1f`; Reborn `afcf9ffa1bc45073e97520d592c0284ce73fefcf` | kernel `6.18.0-y2linux-cpu-final`, root `2025.02.18-platform-v1.6`; older physical before-state |
| Retained known-good fallback | Hardware02 kernel `6.18.0-y2linux-hardware-02`, root `2025.02.18-platform-v1.4` | preserve exact BOOTIMG/Y2ROOT pair and Y2DATA; narrower earlier hardware evidence, not a Fix01 rollback test |
| Hardware Final software candidate | Linux `067003f8988042a832181e935128ea93e26070a7`; Reborn `5b5d23b89952d88faf3155cf680ccce918f1b099` | earlier software ledger; no Fix01 physical acceptance transfer |
| Platform v1 software candidate | Linux `d04b95aaff713edf943042d97a4c6134ca19fc24`; Reborn `6c8aa128550ec80addd08ef3145e9d5a846ddf2e` | earlier build/completion receipt; no Fix01 physical acceptance transfer |

Latest local package (Fix03, unflashed): `out/y2linux-cpu-final-fix03-candidate/`.
Its manifest selects only **BOOTIMG** and **ANDROID/Y2ROOT** in the preserve-data
scatter. It has no Y2DATA replacement and no protected/preloader/LK/NVRAM/
calibration payload. Exact manifest image hashes:

| File | SHA-256 |
| --- | --- |
| `BOOTIMG.img` | `c55b26407e46a436f2bfffe216feecfd18ced6b7bd404ed8ab6eaa013ba9cce6` |
| `Y2ROOT.img` | `04cafd4bddab65a01e0a35c056ee9a22a6b00ffa059cd863a95095af635d7257` |
| `fallback/BOOTIMG.img` | `b2a2c3bcb7cc7783828882e447e8b867453cb5b65846ce63577076b1ca4afeea` |
| `fallback/Y2ROOT.img` | `63dbd0a198cd86e847c10ed163fd14b2cbe269595fa1988c99ac8393160bb547` |

Hashes here are copied from the sealed candidate manifest, not a fresh build or
flash assertion. The [Fix03 software receipt](../validation/Y2-CPU-FINAL-FIX03.md)
records package integrity; the [Fix02 physical report](../validation/Y2-CPU-FINAL-FIX02-PHYSICAL-QUALIFICATION.md)
is the latest hardware outcome and before-state. Fix01 (BOOTIMG `82b38fd3…`)
and Fix02 (BOOTIMG `a621e270…`) receipts keep their own hashes. Never substitute a newer source HEAD or a different
image for an exact measured pair without another qualification.
