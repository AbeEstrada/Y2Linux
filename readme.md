# Y2Linux

Linux 6.18 and a Buildroot userspace for the **Innioasis Y2** music player
(MediaTek MT6582), together with the native music player
[Y2Reborn](https://github.com/SchulzCode/Y2Reborn). It replaces the stock
Android system on the internal eMMC and leaves the bootloaders, calibration and
factory partitions untouched.

> **Status: Baseline 13 (2026-10-11), developer preview.** It runs every day on
> the maintainer's Y2. There are no prebuilt images yet: you build from source
> and flash with SP Flash Tool. Only one hardware revision has been tested (see
> [Supported hardware](#supported-hardware)). Read [Known issues](#known-issues)
> before you flash.

| | Baseline 13 |
| --- | --- |
| Git tag (both repositories) | `baseline-13` |
| Kernel | `6.18.0-y2linux-platform-v1-power-final-13` |
| Root filesystem / release | `2025.02.18-platform-v1.43` / `1.0.0-platform-v1-power-final-candidate.13` |
| Player | Y2Reborn 0.3.0 |
| Maintainer's images built from | Y2Linux `47c1cf2`, Y2Reborn `71ddb0d` (later commits: tests, packaging tool and docs only) |

## Getting started

1. **[Build from source](docs/BUILDING.md)**: host setup, the stock firmware
   files you extract from Innioasis's own firmware package, the build and the
   first-install package.
2. **[Install on the Y2](docs/INSTALL.md)**: back up, flash with SP Flash
   Tool, first boot, SSH over USB, updating and going back to stock.

## What works

Observed on the maintainer's device on Baseline 13 or the candidates just before it:

- Boots from internal eMMC: stock preloader and LK, then Linux 6.18 and Buildroot. No SD card needed.
- Display with GPU (DRM + Lima), buttons, click wheel and the Reborn player UI.
- Wired headphone audio (CS43131 DAC), S16 stereo at 44.1/48 kHz; higher-rate files are converted.
- Bluetooth audio (SBC).
- Wi-Fi (2.4 GHz).
- USB: MTP (internal storage and SD card), and SSH/SFTP over USB Ethernet for developers.
- microSD card for music (`/media/sd`). Optionally, the stock FAT partition can be turned into
  a 5.4 GiB ext4 music partition (`y2-platform internal-media provision`).
- Charging over USB (conservative 650 mA default ceiling) with a real "Full" state, and an
  offline charging screen when the player is off.
- Deep sleep when the screen times out: the SoC suspends and wakes every 30 min for
  housekeeping. The first sleep on 13 lasted 3.4 h (7 suspends) and ended with a clean
  Power-button wake.

## Known issues

- **Never use a software restart.** A warm reboot (the menu's Restart, update
  reboots, `reboot`) can leave the panel dark (`flip_done timed out`). Turn the
  player off by holding Power, then start it again. Not yet investigated.
- **USB networking can stop passing traffic after a wake from deep sleep.** The
  device re-enumerates but sends nothing (seen on 12 and on the first 13 wake). Turning
  the player off and on again recovers it. Under investigation.
- **Battery life is not stock-like yet.** Asleep: about 2.2 percentage points/h on
  12. 13 adds the stock sleep settings, but its overnight result is not measured yet.
  Awake with the screen off: about 4.9 points/h, because only the backlight is
  switched off. The percentage is estimated from voltage; there is no current sensor.
- Bluetooth uses SBC only. AAC/aptX/LDAC sources exist but are not enabled in
  normal builds.
- No public update channel or release signing. You flash or copy updates by hand.

The full list, with evidence and next steps, is in the
[current platform state](docs/CURRENT_PLATFORM_STATE.md) and the
[Baseline 13 report](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-13.md).

## Supported hardware

One device has been tested: Innioasis Y2, board `eastaeon82_wet_kk`, MT6582,
7.8 GB eMMC, shipped with Innioasis firmware **v3.2.0 FM (2026-08-13)**. The
build and packaging tools check the stock firmware files by SHA-256. A Y2 with a
different board, eMMC size or partition table is **not supported** until someone
verifies it. Please report your device's details in an issue.

## Repository layout

| Path | Contents |
| --- | --- |
| `kernel/` | Kernel configuration, device tree, platform drivers (`kernel/platform`, `kernel/usb`, `kernel/audio`) and the overlay patches applied to Linux 6.18 (`kernel/patches`) |
| `buildroot/` | Buildroot external tree: defconfig, board overlays, local packages (Reborn, connectivity, MTP, updater) |
| `initramfs/` | Boot-time rescue and handover to the internal root filesystem |
| `tools/build/` | Locked, network-isolated kernel build environment (bubblewrap) |
| `tools/production/` | Production build, packaging and validation, plus on-device helper sources |
| `tools/platform/` | `y2-platform`, the on-device platform service and CLI |
| `tools/connectivity/` | Wi-Fi/Bluetooth services and stock firmware provisioning |
| `tests/` | Host and container test suites (`tools/production/tests.sh`) |
| `docs/` | Documentation; start at [docs/README.md](docs/README.md) |

## Licence

Each source file carries its own SPDX licence identifier; the kernel drivers and
patches are GPL-2.0, and Y2Reborn is MIT. The proprietary MediaTek radio firmware is
**not** in this repository and is never downloaded. You extract it from your own
copy of the Innioasis firmware (see [BUILDING](docs/BUILDING.md)). Images that
contain it are for your own device; do not redistribute them.

This project is not affiliated with Innioasis or MediaTek. Flashing replaces the
stock system; you do it at your own risk.
