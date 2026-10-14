# Y2Linux

Linux 6.18 and a Buildroot userspace for the **Innioasis Y2** music player
(MediaTek MT6582), together with the native music player
[Y2Reborn](https://github.com/SchulzCode/Y2Reborn). It replaces the stock
Android system on the internal eMMC and leaves the bootloaders, calibration and
factory partitions untouched.

> **Status: Baseline 46 (2026-10-16), developer preview.** It runs every day on
> the maintainer's Y2. The first install is built from source and flashed with
> SP Flash Tool; after that, the player installs new releases over Wi-Fi from
> this repository's [GitHub releases](https://github.com/SchulzCode/Y2Linux/releases).
> Only one hardware revision has been tested (see
> [Supported hardware](#supported-hardware)). Read [Known issues](#known-issues)
> before you flash.

| | Baseline 46 |
| --- | --- |
| Git tag (both repositories) | `baseline-46` (previous: `baseline-34`); GitHub release `baseline-46` carries the signed over-the-air update |
| Kernel | `6.18.56-y2linux-platform-v1-power-final-46` (Linux 6.18 long-term line) |
| Root filesystem / release | `2026.08-platform-v1.76` (Buildroot 2026.08) / `1.0.0-platform-v1-power-final-candidate.46` |
| Player | Y2Reborn 0.3.0 (Rust 1.99) with Cover Flow, Genres and 15 themes |
| Main components | GCC 15.3 / glibc 2.44, Mesa 26.2.4, FFmpeg 9.0.2, BlueZ 5.87, OpenSSL 4.0.3, Python 3.15.0 — every component on its newest release |
| Maintainer's images built from | Y2Linux `d03ab29`, Y2Reborn `850687d` (later commits: docs only) |

## Getting started

1. **[Build from source](docs/BUILDING.md)**: host setup, the stock firmware
   files you extract from Innioasis's own firmware package, the build and the
   first-install package.
2. **[Install on the Y2](docs/INSTALL.md)**: back up, flash with SP Flash
   Tool, first boot, SSH over USB, updating and going back to stock.

## What works

Observed on the maintainer's device on the candidates up to 45 (46 is the first release on the
update channel):

- **Over-the-air updates:** Settings → About & Updates checks once a day on Wi-Fi (or on demand),
  downloads a signed release and, with **Restart and Install**, restarts into a Y2 recovery image
  that backs up, installs and verifies kernel, rescue and system, then restarts into the new
  version (about a minute; the old version is restored on any failure). It makes room on its own
  by removing old logs; music and settings are never touched. Needs the Y2 recovery image flashed
  once ([recovery install](docs/architecture/ota-recovery-install.md)).
- Software restart works (since 43).

- Boots from internal eMMC: stock preloader and LK, then Linux 6.18 and Buildroot. No SD card needed.
- Display with GPU (DRM + Lima), buttons, click wheel and the Reborn player UI.
- **Themes:** Settings → Display → Theme switches between Reborn's own look and 15 shipped
  themes that restyle every screen (Classic, Nano Glass, Walkman, Terminal, Winamp, Paper,
  Big Type, Cassette, Neon Night, Zune, five Mini colours). More can be added by copying a
  theme folder into `Themes` on the player over MTP. Authoring guide:
  [Reborn skins](https://github.com/SchulzCode/Y2Reborn/blob/main/docs/skins.md).
- Albums in **Cover Flow** (perspective covers with reflections, the cover flies into the
  album page; the grid stays available in Settings → Display), and **Genres** in the main list
  (genre → All Songs and its albums).
- Album art from the album folder first (cover.jpg, folder.jpg, … and Windows Media Player
  names), the embedded picture when the folder has none.
- Wired headphone audio (CS43131 DAC), S16 stereo at 44.1/48 kHz; higher-rate files are converted.
- Bluetooth audio; the codec is chosen automatically (SBC, or AAC/aptX/LDAC when the
  headphones support them and BlueALSA offers them).
- Wi-Fi (2.4 GHz).
- USB: MTP (internal storage and SD card), and SSH/SFTP over USB Ethernet for developers.
- microSD card for music (`/media/sd`). Optionally, the stock FAT partition can be turned into
  a 5.4 GiB ext4 music partition (`y2-platform internal-media provision`).
- Charging over USB (conservative 650 mA default ceiling) with the stock top-off: the battery
  is charged until really full, shows 100 % then counts down 99, 98, …, and keeps its
  percentage across a restart. An offline charging screen when the player is off.
- Deep sleep when the screen times out: the SoC suspends and wakes every 30 min for
  housekeeping, with the stock suspend settings (CPU at 0.85 V, USB PHY off, wheel controller
  asleep). Sleep and USB state are written to `/data` so they survive a restart.
- The display hardware is powered off with the screen, stock hardware clock gating is on,
  and unused PLLs and clocks are switched off for sleep. The battery percentage uses the stock
  fuel-gauge curve. A PC port charges at the stock 450 mA even when the PC is off or asleep.
- In sleep the power-management chip is set to the stock suspend values (audio and unused
  clocks off, references off) and restored on wake.
- Waking with Power lights the screen in about half a second; Wi-Fi and Bluetooth come back
  in the background.
- A dark screen after the shutdown animation (no white or colour noise). The start-up colour
  flash fix (the backlight is off while the display is handed over) is in, but not yet confirmed.

## Known issues

- **Rarely a dark screen at start.** Twice the display controller answered every register read one
  register late, so the first picture never started (a cold start with USB plugged in on 42, and the
  installer screen once). Since 44 the driver detects this and restarts the display; the retry
  has not been needed on the device yet. Hold Power for 10 s and start again if it happens.
- **USB after a wake from deep sleep.** On 13–15 the device re-enumerated and received,
  but its transmit never completed, so USB networking and MTP stayed silent until a
  restart. Since 16 every wake has worked (one after a 16 h night), and 17's diagnostics
  caught and repaired a lost USB interrupt setting after a sleep; not yet confirmed over many wakes.
- **Battery life is not stock-like yet.** 26 drew about 8.3 mA asleep over a 10 h night
  (16: about 8.6 mA); stock is about 1.3 mA (≈0.1 points/h). 27 adds the stock panel
  power-down, VGP2-off and VSYS sleep mode, 32 deep idle during screen-off playback; neither
  has had its overnight or playback measurement yet. The SoC's
  infrastructure power domain still never switches off in sleep (the SoC side now matches stock;
  17–20 gate the remaining modem, PMIC, PMIC-wrapper and UART1 clocks like stock; their overnight
  drain has not been measured yet). The percentage is estimated from voltage; there is
  no current sensor.
- Cover Flow should now run at the panel's rate (25 removed a 34-ms frame gate); the new
  frame rate has not been measured on the device yet.
- Bluetooth: saved headphones are not always reconnected after a start or wake (the platform
  reconnect can end `Inhibited`; connect them once from Settings → Bluetooth). AAC with
  AirPods has not been confirmed on the device yet.
- Playing to a saved but disconnected Bluetooth output fails instead of connecting it.
- Over-the-air updates need the Y2 recovery image in RECOVERY (flashed once with SP Flash Tool).
  A kernel that hangs before its rescue system runs can only be fixed with SP Flash Tool.

The full list, with evidence and next steps, is in the
[current platform state](docs/CURRENT_PLATFORM_STATE.md) and the
reports for [46](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-46.md) (update space, restart by default, first release),
[44](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-44.md)/[45](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-45.md) (display read lag, installer screen),
[43](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-43.md) (software restart fixed),
[35](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-35.md)–[38](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-38.md) (over-the-air updates),
[34](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-34.md) (shipped themes, battery display),
[33](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-33.md) (themes),
[32](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-32.md) (deep idle during playback),
[31](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-31.md) (artwork and formats),
[30](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-30.md) (storage and decode speed),
[28](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-28.md)/[29](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-29.md) (stock battery percentage and top-off),
[27](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-27.md) (stock panel, VGP2 and VSYS sleep),
[26](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-26.md) (Bluetooth codecs),
[25](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-25.md) (Cover Flow frame gate),
[24](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-24.md) (frame pacing),
[23](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-23.md) (Cover Flow and Genres),
[21](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-21.md)/[22](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-22.md) (display power transitions),
[19](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-19.md)/[20](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-20.md) (PMIC_WRAP and UART1 clocks),
[18](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-18.md) (stock PMIC sleep settings),
[17](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-17.md) (modem gate, faster wake),
[16](docs/validation/Y2-PLATFORM-V1-POWER-FINAL-16.md) (stock sleep parity),
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
