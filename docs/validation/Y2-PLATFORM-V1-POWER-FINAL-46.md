# POWER-FINAL-46 — space for every update, restart by default; first public release

Status: **SEALED and PUBLISHED** as GitHub release `baseline-46` (2026-10-16), the first release on the update
channel; awaiting the over-the-air install over Wi-Fi. Package `out/y2linux-platform-v1-power-final-candidate-46/`
(fallback = 45, which the player runs), receipts `out/deep-sleep-final/build46-receipts/`. BOOTIMG
`d5bacc9ee66b52c3894070e8f9c2846acb95e4fefa668262576856415bb5583f`, Y2ROOT
`e8dde2d1b958a21cbc862fd7eaef5b147cda82ef08c306a7343c5c241842d87a`, RECOVERY
`476567c538c7f1dbcea6b5f5cd1577595c4b862f9a9521c374b86ae4b35fe1e2`. Kernel `6.18.56-y2linux-platform-v1-power-final-46`,
update sequence 4600, Linux `d03ab29`, Reborn `850687d`. Container suite **718 OK**, host update/handover tests
**31 OK**, Reborn fmt/clippy/tests OK, all seal checks PASS. Signed with the release key; the release assets are
`…-46-ota-release/` (manifest, signature, three payloads).

## Why

Owner after 45: "does the update process also have a cleanup, so that we can guarantee there is always enough
space for users to update?" Staging 45 had failed `update_data_space_reserve` because a cancelled package stayed in
`pending`, and nothing removed disposable data (the owner's player held 330 MiB of test logs).

| Change | Detail |
| --- | --- |
| Stale package | Deleted before every download and on **Cancel Update**. |
| Rollback copies | The recovery deletes the previous copies right before writing new ones; the space check counts them as free. |
| Cleanup | If the download does not fit, disposable data goes one entry at a time until it does: `/data/logs` except `system.log`, `recovery-last.log`, `recovery-display.txt`; rotated `*.previous.jsonl` platform journals; finished qualification runs. First for the manifest (a check works on a nearly full volume), then for the payloads. Never music, settings, library or the rollback copies. |
| Refusal | `download.json` `needed_bytes`; Reborn: "the update needs N MB of system space. Your music is not affected." |
| Restart | Default: restart into the recovery and back. Override `restart.json` `{"mode": "poweroff"}`. Low battery in the recovery always turns off. Outcome screens say *Restarting*. Reborn: **Restart and Install**. |

## Owner steps

1. Player on Wi-Fi: Settings → About & Updates → **Check for Updates**, **Download Update**, **Restart and Install**.
2. The agent checks the install log, the display, `Acknowledged` and the cleaned-up package afterwards.
