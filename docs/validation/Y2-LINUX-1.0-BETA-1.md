# Y2Linux 1.0 Beta 1 (Baseline 50)

Status: **@STATUS@** (2026-10-16). The first public beta of Y2Linux and Y2Reborn: release `1.0.0-beta.1`,
Reborn `1.0.0-beta.1`, kernel `6.18.56-y2linux-1.0.0-beta.1`, update sequence 5000, Linux `@LINUX@`,
Reborn `@REBORN@`, git tag `baseline-50` in both repositories. Built with `--public`. Container suite **@SUITE@**,
all seal checks PASS (public distribution gate, no radio firmware). Milestone audit: BETA-1 in
[roadmap-gap-audit](../planning/roadmap-gap-audit.md).

| Image | SHA-256 |
| --- | --- |
| BOOTIMG | `@BOOTIMG@` |
| Y2ROOT | `@Y2ROOT@` |
| RECOVERY | `@RECOVERY@` |
| Y2DATA (no SSH key) | `@Y2DATA@` |

## Release contents

- `Y2Linux-1.0.0-beta.1-first-install.zip`: BOOTIMG, RECOVERY (Y2 recovery image), Y2ROOT, Y2DATA, the scatter
  files for SP Flash Tool (one pass writes all four) and checksums. No MediaTek firmware, no SSH key.
- The signed over-the-air update (`manifest.json`, `manifest.sig`, three payloads; key `platform-v1-release-20261015`).
- Corresponding sources: Buildroot legal-info (package sources, patches, licences) and the Linux 6.18.56 archive;
  Y2Linux and Y2Reborn at `baseline-50`.

## Since 49

| Change | Detail |
| --- | --- |
| Firmware watcher | Re-checks every maintenance pass and restarts the radios as stop + start with enough time (owner Firmware-drive test of 49, archive 154). |
| Software Update | A cancel or an older failure no longer hides a newer release (Reborn `476e281`). Versions read "1.0.0 Beta 1". |
| Identity | Y2Linux and Reborn `1.0.0-beta.1`. |

What the path to the beta brought (35–49): over-the-air updates through a Y2 recovery image with backup, readback and
rollback; software restart fixed; the download screen; space for every update; firmware-free public images with the
owner's own radio firmware; public codec set SBC, AAC (fdk-aac-free), LDAC. Reports
[35](Y2-PLATFORM-V1-POWER-FINAL-35.md)–[49](Y2-PLATFORM-V1-POWER-FINAL-49.md).

## Known gaps (also in the release notes)

Battery in sleep ≈8.3 mA vs stock ≈1.3 mA; rare slow display start after a restart (picture starts since 47); USB after
deep-sleep wake not confirmed over many wakes; Bluetooth reconnect after a wake, AAC (fdk-aac-free) with AirPods not yet
confirmed; full install from stock run on one player only.

## Device results

Pending: the owner installs Beta 1 over Wi-Fi from the release.
