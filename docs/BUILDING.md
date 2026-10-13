# Building Y2Linux from source

This builds the kernel, the Buildroot root filesystem with the Y2Reborn player,
and a **first-install package** that you flash with SP Flash Tool
([INSTALL.md](INSTALL.md)). These are the same commands that produced
Baseline 18 on the maintainer's machine (an Arch-based Linux, x86_64). They have
not yet been run on a second machine. If a step fails, please open an issue with
the log.

## 1. Host requirements

- Linux x86_64 with about **15 GB free disk** (download cache about 4 GB, build about 5 GB).
- **Python 3.12 or newer**.
- **bubblewrap** (`bwrap`) and unprivileged user namespaces. The kernel build runs in a
  locked, network-isolated Alpine userspace that the tools download and hash-check.
  You don't need Docker.
- The standard **Buildroot host packages**: `gcc`, `g++`, `make`, `binutils`, `patch`,
  `perl`, `rsync`, `cpio`, `unzip`, `bzip2`, `gzip`, `tar`, `file`, `bc`, `wget`,
  `which`, `diffutils`, `findutils`, `gawk`, `git`. The root filesystem is built on the
  host (not inside bubblewrap), so these must be installed.
- **Rust via rustup**, with toolchain **1.99.0** and the ARM target. The Buildroot recipe
  calls `~/.cargo/bin/cargo`. Override that with `REBORN_CARGO=/path/to/cargo` if needed.

  ```sh
  rustup toolchain install 1.99.0 --profile minimal \
      --target armv7-unknown-linux-gnueabihf -c rustfmt -c clippy
  ```

- `e2fsprogs` (`debugfs`, `e2fsck`), `util-linux` (`blkid`) and `simg2img`
  (Arch: `android-tools`; Debian/Ubuntu: `android-sdk-libsparse-utils`) for the
  firmware and packaging steps.
- An **ed25519 SSH key** for root access over USB. The packaging step writes its
  public half into the data partition.

  ```sh
  ssh-keygen -t ed25519 -f ~/.ssh/y2linux_ed25519
  ```

## 2. Get the sources

Y2Linux and Y2Reborn must sit **next to each other** in the same parent folder.
Buildroot builds Reborn from `../Y2Reborn`.

```sh
mkdir y2 && cd y2
git clone https://github.com/SchulzCode/Y2Linux.git
git clone https://github.com/SchulzCode/Y2Reborn.git
git -C Y2Linux checkout baseline-18
git -C Y2Reborn checkout baseline-18
cd Y2Linux
```

Keep both trees clean (no uncommitted changes). The build and packaging tools
refuse dirty trees and record both commit IDs in the image. If you change
anything, commit it first.

## 3. Stock firmware files (from your own Innioasis firmware)

The Wi-Fi/Bluetooth chip needs proprietary MediaTek firmware. It is not in this
repository, and the build never downloads it. You extract it from the Innioasis
firmware package for the Y2, **v3.2.0 FM (2026-08-13)**, the folder you would
load into SP Flash Tool to reflash stock. The tools check every file by SHA-256,
so other firmware versions are rejected.

The same folder is needed again in step 6. It is also your only way back to stock,
so keep a copy.

| File in the stock folder | SHA-256 |
| --- | --- |
| `boot.img` | `5ef1bdf28481ee0bf5f3528c1ddd91cf3f4d2d5f39e4d0ea049a8137a30f6af6` |
| `system.img` | `5a7a92f3a95374f31abe8b3ddbd68c5c2ce5677547db3d1cbc21653d24c76989` |
| `userdata.img` | `552e325ecf2faffeb9351022147bbfda3b7cebe25df491b2d732e85c5c68f27c` |
| `MT6582_Android_scatter.txt` | `e5fe03e9f3219cc9b5ead27892f2ddb722acc16adce3306d27feb87893cd977e` |

Extract the five firmware files and the NVRAM defaults library from `system.img`,
then stage them:

```sh
STOCK=/path/to/y2_v3.2.0_FM-20260813
WORK=$(mktemp -d)
simg2img "$STOCK/system.img" "$WORK/system.raw"
mkdir "$WORK/firmware"
for f in WIFI_RAM_CODE_MT6582 WMT_SOC.cfg mt6572_82_patch_e1_0_hdr.bin \
         mt6572_82_patch_e1_1_hdr.bin modem_1_2g_n.img; do
    debugfs -R "dump /etc/firmware/$f $WORK/firmware/$f" "$WORK/system.raw"
done
debugfs -R "dump /lib/libcustom_nvram.so $WORK/libcustom_nvram.so" "$WORK/system.raw"

python3 tools/connectivity/provision.py \
    --owner-firmware "$WORK/firmware" \
    --stock-custom-nvram "$WORK/libcustom_nvram.so" \
    --output out/owner-firmware
```

`provision.py` prints `Verified owner-local firmware: 7 files`. It derives
`WIFI.defaults` and `BT.defaults` (generic board parameters) from the library.
It never copies a device's own calibration or MAC addresses. Your device keeps
those in its NVRAM partition, which the install never touches.

## 4. Build

```sh
python3 tools/production/build.py --output out/y2-build --owner-firmware out/owner-firmware
```

On the first run this:

1. Downloads and hash-checks the locked inputs (`tools/build/inputs.lock.json`:
   Linux 6.18.56 and the Alpine 3.24 build userspace with LLVM 22; `buildroot/inputs.lock.json`:
   Buildroot 2026.08) into `.cache/`. Buildroot uses the Bootlin GCC 15.3 cross toolchain.
2. Builds the kernel inside bubblewrap with the overlays in `kernel/patches/`.
3. Builds the Buildroot toolchain and root filesystem on the host, including FFmpeg
   9.0.2 and Y2Reborn (offline, from its vendored crates).
4. Builds the initramfs and device tree, and validates the artifacts.

The first build takes a long time because Buildroot compiles its own toolchain.
Later builds reuse `.cache/` and can resume a stage with
`--resume kernel|buildroot|artifacts`. Logs for each stage are in `out/y2-build/*.log`.
The result is `out/y2-build/BOOTIMG.img` (kernel and rescue initramfs) and
`out/y2-build/buildroot/images/` (root filesystem).

## 5. Test (optional, recommended)

```sh
python3 tools/build/run.py --output out/y2-build -- sh /project/tools/production/tests.sh
```

This runs the platform test suite inside the locked environment. Baseline 18
passed 685 cases there. Running the same tests directly on the host gives some
errors that only depend on the host (missing `qemu-arm`, `pyelftools`); use the
container.

Y2Reborn's own tests run on the host (see the Y2Reborn README):

```sh
cd ../Y2Reborn && cargo test --workspace --locked --offline
```

## 6. Make the first-install package

```sh
python3 tools/production/package.py \
    --build out/y2-build \
    --output out/y2-first-install \
    --stock "$STOCK" \
    --public-key ~/.ssh/y2linux_ed25519.pub

python3 tools/production/validate.py out/y2-first-install --build out/y2-build
```

`validate.py` should end with `PASS offline Production Storage v1`. The package contains:

| File | Purpose |
| --- | --- |
| `BOOTIMG.img` | Kernel and rescue initramfs (BOOTIMG partition) |
| `Y2ROOT.img` | Root filesystem (stock ANDROID partition) |
| `Y2DATA.img` | Empty data partition with your SSH public key (stock USRDATA partition) |
| `MT6582_Android_scatter.txt` | First install: BOOTIMG + ANDROID + USRDATA |
| `MT6582_preserve_data_scatter.txt` | Later updates: BOOTIMG + ANDROID only, keeps your data |
| `manifest.json`, `SHA256SUMS`, `metadata/` | Hashes, partition plan, licences and build inputs |
| `install.md`, `recovery.md` | The detailed flashing and recovery runbooks |

The package must be created in `out/` from the exact commit you built, with a
clean tree. `Y2DATA.img` carries your SSH public key, so it is personal: don't share it.

Continue with [INSTALL.md](INSTALL.md).

## Reference

- [Locked build environment](build/environment.md) (what `tools/build/prepare.py` pins and isolates)
- [Source reconstruction](build/platform-v1-reconstruction.md) (inputs, licences, reproducibility limits)
- [Kernel policy](build/kernel-policy.md), [overlay manifest](../kernel/patches/manifest.json)
- Byte-identical rebuilds are **not** claimed: host tools, paths and timestamps can change
  bytes in the Buildroot part. Each package records the exact inputs it used.
