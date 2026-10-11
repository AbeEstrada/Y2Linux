# Installing Y2Linux on the Innioasis Y2

You need a first-install package from [BUILDING.md](BUILDING.md), **SP Flash
Tool v5.2032** (Linux or Windows, with its bundled `MTK_AllInOne_DA.bin`) and a
USB cable. Read the whole page once before you start.

## What the install changes

| Partition (stock name) | First install | Later updates |
| --- | --- | --- |
| BOOTIMG | Y2Linux kernel + rescue initramfs | replaced |
| ANDROID (`/system`) | Y2Linux root filesystem | replaced |
| USRDATA (`/data`) | Y2Linux data: settings, library, logs, your SSH key | **kept** |
| FAT (internal music storage) | untouched | untouched |
| Preloader, LK, NVRAM, calibration, PROTECT, SECCFG, RECOVERY, tables | **never written** | never written |

Stock Android and its user data are erased. The internal FAT music storage is
left as it is, but Y2Linux does not use it until you convert it to ext4 (see
[Music](#music)), and converting erases it. Copy off anything you want to keep first.

## Before you flash

1. **Check the package:** `cd out/y2-first-install && sha256sum -c SHA256SUMS`.
2. **Keep the stock firmware folder** (`y2_v3.2.0_FM-20260813`). It is how you go
   back to stock.
3. **Optional backups.** If anything on the stock Android `/data` matters to you, read
   back USRDATA with SP Flash Tool first. The cautious path also reads back the
   partition tables and protected ranges before writing. That procedure, with
   coordinates and a verifier (`tools/production/verify_readback.py`), is in the
   package's `install.md` and `metadata/readback-plan.json`.
4. Charge the battery and take the SD card out for the first boot (not required, but it
   keeps the first boot simple).

## Flash

1. Start SP Flash Tool and choose the **Download** tab. Select **Download Only**.
   Never use *Format All + Download*, *Firmware Upgrade* or *Write Memory*.
2. Load **`MT6582_Android_scatter.txt` from the Y2Linux package** (not the stock one).
3. Check the rows. Exactly these three must be ticked and point at the package files:

   | Row | File |
   | --- | --- |
   | BOOTIMG | `BOOTIMG.img` |
   | ANDROID | `Y2ROOT.img` |
   | USRDATA | `Y2DATA.img` |

   Every other row must be unticked. Stop if the tool asks to format, reports a
   partition-table (PMT) change, or shows different addresses.
4. Click **Download**, then connect the **powered-off** Y2 by USB. Wait for the
   green "Download OK" and unplug.

A green tick only means the transfer finished. The first boot shows whether it worked.

## First boot

Hold Power to start. You should see the Y2Linux startup screen, then the Reborn
player. The first boot creates the SSH host keys and the data folders, so it takes
a little longer than later boots.

If it stops in the **rescue** screen, the screen shows the reason (for example,
the root or data partition was not found). Turn the player off with a long Power
press and check the flashed rows. Nothing is written automatically in rescue.

## Connect over USB (SSH)

With the player running, plug it into your computer. It shows up as a USB Ethernet
adapter (plus MTP). The device is `10.42.0.1`. Give your computer's new interface
`10.42.0.2/24` with no gateway:

```sh
ip -br link                                    # find the new interface (e.g. enp…u2i1 or usb0)
sudo ip address add 10.42.0.2/24 dev <interface>
ssh -i ~/.ssh/y2linux_ed25519 root@10.42.0.1
```

With NetworkManager, create a wired profile for that interface with IPv4 *Manual*,
address `10.42.0.2/24`, no gateway. Login is key-only, with the key you packaged.
Passwords are disabled.

Useful commands on the device:

```sh
y2-status system --json      # identity, health summary
y2-platform status           # platform services
y2-health --full --json      # detailed health
cat /etc/y2linux/versions.json
```

## Music

- **MTP:** the player appears in any MTP client with *SD Card* and, once the internal
  music partition is converted (below), *Internal Storage*. Copy music there. Before
  that conversion, the player reads `/data/music` on the data partition, which you
  can fill over SFTP.
- **SD card:** FAT, exFAT and ext4 cards mount at `/media/sd`. `y2-media status` shows the
  card; `y2-media format --confirm-cid <CID>` reformats it as ext4 (it erases the card).
- **Internal music partition (optional):** the stock FAT music partition can become
  a 5.4 GiB ext4 partition at `/media/internal`, exported over MTP as *Internal Storage*.
  This **erases that FAT partition**. Music already in `/data/music` is moved across
  with checksums.

  ```sh
  y2-platform internal-media status                         # shows the FAT serial
  y2-platform internal-media provision --confirm-serial XXXX-XXXX
  ```

  Then power off and on (not a software restart, see below).

## Updating to a newer build

Build a new first-install package from the newer source, then flash it with
**`MT6582_preserve_data_scatter.txt`**. Only **BOOTIMG** and **ANDROID** are ticked;
**never tick USRDATA**, which would wipe your settings, library and SSH key.
Your data partition is kept and upgraded on boot.

## Known issues to plan around

- **Do not software-restart.** A warm reboot (menu Restart, `reboot`, update reboots)
  can leave the display dark. Power off with a long Power press, then power on.
  If the panel is already dark, hold Power for 10 s and start again.
- **USB networking after deep sleep.** After a wake the USB connection can enumerate
  but pass no traffic. Power off and on to recover.
- More, with evidence: [current platform state](CURRENT_PLATFORM_STATE.md).

## Going back to stock

In SP Flash Tool, Download Only, load the **stock** `MT6582_Android_scatter.txt`,
untick everything, then tick only BOOTIMG → `boot.img`, ANDROID → `system.img`,
USRDATA → `userdata.img`. This restores factory Android (not your old personal
data) and erases Y2Linux and its data. Never tick PRELOADER, UBOOT/LK, MBR/EBR,
NVRAM, PROTECT, SECCFG or RECOVERY.

**This full restore has not yet been tested by the project.** The partitions it
writes are the same ones the install wrote, and the bootloaders are never changed.
The detailed procedure and its caveats are in the package's `recovery.md`
([source](architecture/production-recovery.md)).
