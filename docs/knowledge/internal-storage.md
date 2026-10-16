# Internal storage and removable media (POWER-FINAL-08)

<!-- knowledge-base-scope: current-production-policy -->
2026-10-10 (provisioning run on the owner's player that day). **Since Beta 7.9 (2026-10-17) every player sets
Internal Storage up by itself at start** (STORAGE-SETUP, [plan](../planning/INTERNAL-STORAGE-SETUP-PLAN.md)); the
command below stays for developers.

## Layout

| Partition | Filesystem | Use |
| --- | --- | --- |
| p5 `Y2ROOT` (820 MiB) | ext4, UUID `...0101` | system, read by the initramfs |
| p7 `Y2DATA` (800 MiB) | ext4, UUID `...0102` | `/data`: settings, Wi-Fi/Bluetooth state, SSH, logs, Reborn database |
| p8 `Y2MEDIA` (5.46 GiB) | ext4, UUID `...0103` | `/media/internal`: music and whatever the owner copies over MTP |
| SD card | any card the owner formats with `y2-media format` (ext4 by default); vfat/exfat/ext4 cards also mount | `/media/sd` |

p8 used to be the stock firmware's runtime FAT storage. The eMMC write guard now includes its exact span
(stock logical sector 3742720 to the end of the exposed disk, directly after Y2DATA). Boot areas, CACHE,
protected/NVRAM partitions and the hidden tail remain unwritable.

## What the owner sees

* MTP **Internal Storage** is `/media/internal/music` (fixed slot, storage id `0xffff0001`); **SD Card** is `/media/sd`.
  The old `/data/music` folder is no longer exported.
* Reborn follows the platform's record: Y2Media when `/run/y2/internal-media.json` says Ready for this boot and this
  mount, `/data/music` before that (an unprovisioned device keeps working).
* Factory reset does not erase Y2Media music; delete files over MTP.

## Automatic setup (Beta 7.9)

`S02y2-media` runs `y2-platform internal-media setup --automatic` before USB and Reborn. It acts only on the stock
FAT at the exact p8 geometry, after the read-only check (issue #44 rules), from a read-only mount at
`/run/y2/old-storage`:

* nothing but leftovers (empty folders, thumbnail caches, computer clutter) → format at once;
* user files ≤ 400 MB with ≥ 150 MB left on Y2DATA → copied to `/data/system/internal-media-kept` with SHA-256,
  format, moved to `music/Old Player Files` with SHA-256 (then `/data/music` as before);
* more, or unreadable → `Waiting`: nothing changes, the old storage stays mounted read-only and is exported over MTP
  as *Old Storage*; Reborn asks once, Settings → Storage → *Set Up Internal Storage* runs
  `internal-media setup --confirm-shown` (the serial this boot reported) and erases it, then the player restarts.

`/data/system/internal-media-setup.json` (phase `staging` → `formatting` → `migrating`) makes every step resumable;
only that record allows formatting a p8 that an interrupted format left unreadable. Skipped (`Pending`) while an
update waits for its health check, below 3.70 V on battery, or with an unknown battery. The filesystem is created with
every setting named (`internal_media.MKFS`), identical to the first Y2MEDIA. This boot's result:
`/run/y2/internal-media-setup.json` and `storage.internal_setup` in `y2-platform status`. Start screen phases
`media_setup*`.

## Commands (root, over USB SSH)

    y2-platform internal-media status
    y2-platform internal-media mount | unmount
    y2-platform internal-media provision --confirm-serial 3F93-07E6 [--no-migrate]
    y2-media status                      # shows partition_bytes and capacity_state (Undersized) for the card
    y2-media format --confirm-cid <CID>  # repartition the whole card, ext4 label Y2SD; names the card
    y2-media grow                        # e2fsck + resize2fs for an undersized ext4 card

`provision` replaces only the stock FAT filesystem whose serial you pass, refuses a mounted or any other filesystem,
creates ext4 `Y2MEDIA`, mounts it, copies `/data/music` across with SHA-256 verification and removes an original only
after every file verified. Re-running it resumes a partial migration and never overwrites a differing file.
Nothing formats or deletes automatically. The file-level backup of the stock partition taken before this change is
`out/deep-sleep-final/evidence/20261010/93-stock-fat-partition-backup/`.

## Known limits

* Format and grow are explicit owner operations; a card with a foreign or undersized filesystem is only reported.
* An ext4 card is not readable by a PC when pulled out; MTP is the transfer path. exFAT remains mountable.
* No endurance measurement of ext4 on this eMMC; no physical power-loss test of Y2Media yet.
