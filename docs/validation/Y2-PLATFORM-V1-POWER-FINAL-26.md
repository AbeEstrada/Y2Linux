# POWER-FINAL-26 — Bluetooth codec auto-selection

Status: **SEALED, AWAITING THE OWNER FLASH** (2026-10-13). Package `out/y2linux-platform-v1-power-final-candidate-26/`
(fallback = 25), receipts `out/deep-sleep-final/build26-receipts/`. BOOTIMG
`f4ca442b185a6a8561ef12901d68c9662c630a5be65f554776fbe885fe1d585a`, Y2ROOT
`66efd3ed0d4f727edeffa9dd6571f3d9c3e4ebe02647d8074b04c7cf09c2405f`. Identity: build `Y2LINUX-PLATFORM-V1-POWER-FINAL-26`,
kernel `6.18.56-y2linux-platform-v1-power-final-26`, root `2026.08-platform-v1.56`, release
`1.0.0-platform-v1-power-final-candidate.26`; Linux `64b3cc4`, **Reborn `1c9edd4`**. Platform as 25.

## 25 on the device (first check, archives 119–120)

Boot `f0cc8b34` healthy, taint 0, DSI hand-over dark (`backlight off until the first Linux frame` → `restored`). The
owner's card now scans complete: 311 files discovered, 0 failures (24: "11 traversal failures"). Cover Flow frame rate
not measured (the owner filmed it instead; the sampler caught only one 60-fps burst). The framebuffer stream tool reads
≈10 fps whatever the transport (raw 9.8, gzip 9.3; SSH chacha20 carries ≈19 MB/s), so it cannot show a 60-fps glide.

## Why only SBC was chosen

The platform already starts BlueALSA with every compiled codec (`--codec=AAC --codec=aptX --codec=aptX-HD
--codec=LDAC`, `/run/y2/codec-runtime.json`). Live `org.bluealsa.Manager1.Codecs` = `A2DP-source:SBC`, `…:AAC`,
`…:aptX`, `…:aptX-HD`, `…:LDAC`. Reborn accepted only the lowercase prefix `a2dp-source:`, so every codec, SBC included,
was `runtime_enabled=false`; the policy failed (`no_eligible_codec_PHYSICAL_GATE_or_distribution_gate`), the codec
choice (Auto included) stayed hidden and the saved preference was the old default, SBC. The AirPods Pro were on AAC
only because BlueZ negotiated it at connect.

## What 26 changes (Reborn `1c9edd4`)

- The A2DP-source profile in `Codecs` matches case-insensitively (`a2dp_source_codecs`).
- Default codec preference is Auto: LDAC → aptX-HD → aptX → AAC among mutually usable codecs, SBC fallback, requested
  only while the PCM is idle (unchanged policy code).
- Sessions saved before `codec_revision` 1 that hold SBC (the old default; the choice was never offered) move to Auto
  once; another saved codec, or SBC chosen afterwards, is kept.

## Tests

Reborn fmt, clippy `-D warnings`, workspace tests pass; the discovery test now uses the BlueALSA 5.0.0 names seen on
the Y2, and both codec tests fail without the fix. Platform: `validate.py` PASS, ELF closure 354 PASS, installed ARM
PASS, privacy clean, inventory 108 packages, container suite 693 OK.

## Owner checks after the flash

1. Settings → Bluetooth codec shows Auto, SBC, AAC for the AirPods Pro; Auto selected.
2. Status `bluetooth.codec_policy`: `runtime_enabled` true for all five, `selected`/`pcms[0].codec` AAC after a
   reconnect with playback stopped.
3. aptX / aptX-HD / LDAC need headphones that offer them (NOT_RUN).
