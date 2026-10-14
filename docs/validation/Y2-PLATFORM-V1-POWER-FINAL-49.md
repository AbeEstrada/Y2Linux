# POWER-FINAL-49 — firmware-free public images, one-time flash package, public codec set

Status: **PUBLISHED** as GitHub release `baseline-49` (2026-10-16): the update files, a first-install package for SP
Flash Tool and the GPL source collection. Linux `b4610ea`, Reborn `ceb6313`, kernel
`6.18.56-y2linux-platform-v1-power-final-49`, release `…candidate.49`, update sequence 4900. Container suite **727 OK**,
all seal checks PASS (public distribution gate included). Packages `out/y2linux-platform-v1-power-final-candidate-49/`
(update; `-ota-release/` signed with `platform-v1-release-20261015`) and `out/y2linux-49-first-install/` (public flash
package), receipts `out/deep-sleep-final/build49-receipts/`. Owner-private variant with aptX:
`…-candidate-49-private/` (`-ota/`), receipts `build49p-receipts/`, not published.

| Image | SHA-256 |
| --- | --- |
| BOOTIMG | `c7ece1080fe5dd76f01b02d671dfbe860e5339901b9526f291b44e9f2a27f1a5` |
| Y2ROOT (public) | `f1a073c8014163db53781cb3a339bd92acf09d5d17b90c15610cc074760c0d97` |
| Y2ROOT (private, aptX) | `93405c27600a51a26430822fb1ea52b2c7e03f6f7c5febc3a42026e8bfa48c23` |
| RECOVERY | `7097cce59b90c55196fa581db03dd2d1538a37e48fcf3bc92a69c1b8e3478418` |
| Y2DATA (public, no SSH key) | `1b741e60dd08d4596bcb89294404ed6c7b8341734aabac0b95a95a01f9c8a262` |

## Why

The owner asked for release 49 to carry all images (the one-time flash setup for other developers) and an explanation
of the recovery. Preparing it showed that the system image of releases 46–48 (`rootfs.ext4.gz`) contained MediaTek's
radio firmware, which may not be redistributed (owner: permission from Innioasis, not from MediaTek). Those assets were
removed (notes added; never in Git). The public-distribution gate also blocked AAC, aptX, aptX HD and LDAC.

| Change | Detail |
| --- | --- |
| No firmware in any image | `/lib/firmware/mediatek/mt6582` → `/data/firmware/mt6582`. Seal check refuses firmware files; the final images were searched for the firmware's bytes: none. |
| Existing players | The 49+ recovery copies the reviewed files from the old root to Y2DATA (hash-checked) before it writes the new root. |
| New players | `y2_platform.radiofw` reads the owner's stock `system.img` (Android sparse ext4) itself, checks the five files (+ reader library) by SHA-256, derives the two defaults, installs them, deletes the copy and starts the radios. While missing, MTP shows a **Firmware** drive (one empty Y2DATA folder; responder allowlist extended); Reborn explains on Wi-Fi/Bluetooth. `y2-platform firmware status|scan|install`. |
| Codecs | Owner decision 2026-10-16: public SBC, AAC from **fdk-aac-free** 2.0.3 (AAC-LC only, as Fedora ships), LDAC; aptX/aptX HD only private (`build.py --public`). |
| Public package | `package.py --public`: no SSH key (developers personalize Y2DATA with `first_owner.py`), no local paths, one scatter writing BOOTIMG, RECOVERY, ANDROID, USRDATA. |
| GPL sources | Buildroot legal-info (package sources, patches, licences; Reborn = its tagged repository) and the pinned Linux archive are release assets. |
| Build hygiene | Every build installs into an empty target (a reused workspace had kept aptX and the full FDK in an image); two licence-file hashes of bumped packages recorded. |
| Contributions | Y2Linux #38 (cs43130 on-demand load measurement, two driver fixes), Y2Reborn #6 (artwork worker), #7 (A–Z sort), #8 (genre grid title). |
| Docs | [INSTALL](../INSTALL.md) (eight-step release install), [Recovery and updates](../RECOVERY-AND-UPDATES.md), [BUILDING](../BUILDING.md). |

## Device results

- Before publishing, the owner chose to install the public 49 over Wi-Fi from the release (the private variant was
  staged over USB and cancelled). Pending: firmware kept across the update, Wi-Fi/Bluetooth working, recovery screen.
