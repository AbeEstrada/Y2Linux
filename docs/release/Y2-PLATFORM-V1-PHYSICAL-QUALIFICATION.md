# One Platform 1.0 physical qualification campaign

2026-10-04. Integrated physical acceptance: **NOT_RUN**. Endurance: **NOT_RUN**.
The master does not flash or test the device. The owner installs one sealed
paired BOOTIMG/Y2ROOT candidate with the preserving scatter only after its broad
software checks pass. Keep the previous matching pair and stock recovery files.
Use Download Only, select BOOTIMG and ANDROID, leave USRDATA and every other
partition unselected. Do not change the partition table, loader or calibration.

The [master](Y2-PLATFORM-V1-MASTER.md), [source inventory](Y2-PLATFORM-V1-INTEGRATION-STATUS.md)
and [release matrix](Y2-COMMUNITY-BETA-FEATURES.json) retain old evidence at its
actual image/binary scope. None supplies integrated physical acceptance.

## Coordinator and evidence gates

`tools/development/qualify-platform-v1-integration.py` prints an offline A–J plan
by default. `--run` requires the owner's existing pinned SSH configuration and
holds `/tmp/y2-platform-v1-device.lock` nonblocking for the entire run. Busy means
NOT_RUN without device access. Child USB/suspend tools inherit the same lease;
closing a child descriptor never releases the coordinator's lease. Temporary
lock fixtures test this without touching the real device lock.

Every observation checks the full manifest Linux/Reborn pair, kernel, root,
same boot and taint zero. Read-only observations may fall back from USB to
independently pinned Wi-Fi. A mutating child is launched once and never replayed.
A child exit zero needs its actual passing receipt; missing/failed receipts,
source mismatch, unexpected reboot or taint stop later trials. Preserve all
failures and hashes. A captured campaign always remains PENDING_EVIDENCE_REVIEW;
no script promotes listening, actual desktop, mechanical or endurance evidence.

After installation and read-only identity review, the owner can use one command
with existing authorized aliases and configuration (replace example paths):

```sh
python3 tools/development/qualify-platform-v1-integration.py \
  --run --package out/y2linux-platform-v1-integration-candidate \
  --ssh-config /owner/existing-y2-ssh-config --host y2 --wifi-host y2-wifi \
  --cpu --usb sftp --volumes internal sd --suspend-stage core \
  --output out/platform-v1-physical/installed-staged
```

The CPU helper performs guarded awake C1/C2/C3/OPP/timer/hotplug qualification
and restores qualified normal-idle C3 only after its checks pass. SFTP validates
Linux-owned transfers; it does not stand in for desktop MTP. After actual desktop
MTP enumeration, run the same coordinator with `--usb mtp --volumes internal`
and `--mtp-uri` set to the real backend's Internal Storage URI (one volume per
matching URI). Use SD only after verifying its actual partition/filesystem size,
card identity and clean mount. Never format or enlarge it for qualification.

A full RTC attempt is explicitly separate from successful staged PM. After
reviewing staged receipts, the owner may run this coordinator with `--cpu`,
independent Wi-Fi and `--suspend-stage none`; it launches one 30-second RTC trial.
Previous Baseline02 full RTC wake **failed**, so do not loop attempts. Require
same-boot COMPLETE/EXIT, full PCM 596/reset 0x59325253, nonzero wake source,
restore counters without new faults, explicit Reborn prepare/restore ACK and
post-return source/radio/audio/USB/UI readiness. A watchdog warm reboot, staged
pm_test, wake-capable declarations or awake RTC delivery are not a resume pass.
Ordinary product deep sleep remains guarded until qualified hardware evidence.

## One A–J acceptance matrix

| Lane | Integrated evidence required | Existing evidence retained / remaining equipment |
| --- | --- | --- |
| A | Exact paired boot, readiness, service order, clean shutdown and preserving update/recovery | Baseline02 installed identity is history; no automatic flash or power cycle |
| B | C1/C2/C3, OPP/timer/hotplug before/after sleep; cold-boot activation and fault guards | Protected UART01: C2 84.3473%, C3 65.2450%, 3647 checked returns, zero restore faults; new image still needs regression |
| C | Staged PM, one backstopped RTC wake and owner Power wake; same-boot full restore | Baseline02 RTC FAIL retained; no precise codec-child cause or Power pass claimed |
| D | DATA/SD fsynced hash, real different-card/eject/reinsert, MTP desktop durable rename/disconnect; no simultaneous filesystem writer | Storage SDR104/private scratch and USB SFTP receipts remain scoped; real desktop MTP and different-card checks pending |
| E | Wi-Fi readiness/power save, real BT peer codec/reconnect/coexistence while transferring/playing | New BT worker unexecuted; headset/AP/codec-capable peer needed; negotiated codec must be observed |
| F | Wired S16/44.1/48 format/seek/pause/stop, no XRUN; actual listening | Q31/decode support is separate; wider native rates require AFE/I2S precision capture and conditional hardware admission |
| G | Declared media formats/artwork/library; scan/USB/sleep races, stale queue/source refusal and fresh covers after replacement | TEMP scanner/revision/CID faults pass in software; physically measured capacity is 50k, not 250k; cached covers have no open FD |
| H | Display/GPU awake/off/wake, counted wheel/buttons, capture/render order and latency | Bounded temporary optimized ARM evidence retained; synthetic events exclude mechanical IRQ/photon latency |
| I | Charging/refusal/offline boot and battery policy across load/sleep, representative endurance/electrical measurements | Current governor/low-battery safeguards retained; no battery-life promotion from CPU residency |
| J | Private-state-safe diagnostics, package notices/source/permissions, preserving update and fallback verification | Owner-local radio firmware permission and codec/source/legal review remain distribution gates |

Automate source/boot/taint/service and counter capture over SSH, reuse unaffected
receipts, and ask for the counted controls, listening, host backend, charger and
headset observations together. Do not repeat eleven unrelated campaigns. Record
hardware identity, condition and distribution independently for every feature.
Stop on first unexplained failure; retain stdout, result JSON, before/after samples
and hashes under the coordinator's private output. Required lanes remain pending
until a reviewer accepts the actual evidence. No main merge or public release
before broad software and required physical/permission gates pass.
