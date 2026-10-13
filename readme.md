# Y2Linux

Linux 6.18 and a Buildroot userspace for the **Innioasis Y2** music player
(MediaTek MT6582), together with the native music player
[Y2Reborn](https://github.com/SchulzCode/Y2Reborn). It replaces the stock
Android system on the internal eMMC and leaves the bootloaders, calibration and
factory partitions untouched.

> **Status: Baseline 16 (2026-10-13), developer preview.** It runs every day on
> the maintainer's Y2. There are no prebuilt images yet: you build from source
> and flash with SP Flash Tool. Only one hardware revision has been tested (see
> [Supported hardware](#supported-hardware)). Read [Known issues](#known-issues)
> before you flash.

| | Baseline 16 |
| --- | --- |
| Git tag (both repositories) | `baseline-16` (previous: `baseline-15`) |
| Kernel | `6.18.56-y2linux-platform-v1-power-final-16` (Linux 6.18 long-term line) |
| Root filesystem / release | `2026.08-platform-v1.46` (Buildroot 2026.08) / `1.0.0-platform-v1-power-final-candidate.16` |
| Player | Y2Reborn 0.3.0 (Rust 1.99) |
| Main components | GCC 15.3 / glibc 2.44, Mesa 26.2.4, FFmpeg 9.0.2, BlueZ 5.87, OpenSSL 4.0.3, Python 3.15.0 — every component on its newest release |
| Maintainer's images built from | Y2Linux `a4e9c3b`, Y2Reborn `217e28d` (later commits: two fixes for the next image, tests and docs) |

## Getting started

1. **[Build from source](docs/BUILDING.md)**: host setup, the stock firmware
   files you extract from Innioasis's own firmware package, the build and the
   first-install package.
2. **[Install on the Y2](docs/INSTALL.md)**: back up, flash with SP Flash
   Tool, first boot, SSH over USB, updating and going back to stock.

## What works

Observed on the maintainer's device on Baseline 16 or the candidates just before it:

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
  housekeeping, with the stock suspend settings (CPU at 0.85 V, USB PHY off, wheel controller
  asleep). Sleep and USB state are written to `/data` so they survive a restart.
- The display hardware is powered off with the screen, stock hardware clock gating is on,
  and unused PLLs and clocks are switched off for sleep. The battery percentage uses the stock
  fuel-gauge curve. A PC port charges at the stock 450 mA even when the PC is off or asleep.

## Known issues

- **Never use a software restart.** A warm reboot (the menu's Restart, update
  reboots, `reboot`) can leave the panel dark (`flip_done timed out`). Turn the
  player off by holding Power, then start it again. Not yet investigated.
- **USB after a wake from deep sleep.** On 13–15 the device re-enumerated and received,
  but its transmit never completed, so USB networking and MTP stayed silent until a
  restart. On 16 both wakes so far worked (one after a 16 h night); not yet confirmed
  over many wakes.
- **Battery life is not stock-like yet.** 16 draws about 8.6 mA asleep (≈0.75 points/h,
  one 16 h night; 15: about 10 mA); stock is about 1.3 mA (≈0.1 points/h). The percentage is estimated from voltage; there is
  no current sensor.
- Bluetooth uses SBC only. AAC/aptX/LDAC sources exist but are not enabled in
  normal builds.
- No public update channel or release signing. You flash or copy updates by hand.

The full list, with evidence and next steps, is in the
[current platform state](docs/CURRENT_PLATFORM_STATE.md) and the
reports for [16](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-16.md) (stock sleep parity),
[15](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-15.md) (newest versions),
[14](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-14.md) (persistent sleep diagnostics) and
[13](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-13.md) (stock suspend power parity).

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
