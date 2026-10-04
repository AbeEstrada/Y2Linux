# MT6582 AFE register/DMA laboratory (temporary, development only)

`y2_afe_lab.ko` is a generic, bounded instrument for finding out which AFE
memory-interface and interconnect features exist in the exact MT6582 silicon.
It is **not** product code and must never be part of a candidate.

* Register access is limited to the AFE window (`0x11220000`, offsets 0-0x7fc).
* `hold 1` owns one runtime-PM reference of the production AFE device so the
  audio clocks stay on; always finish with `hold 0`.
* DMA slots are ordinary coherent buffers below 4 GiB; no raw physical memory.
* The installed kernel has `CONFIG_MODULE_UNLOAD=n`: once loaded it stays until
  reboot, so experiments are driven through the command file, not reloads.
* Hold `/tmp/y2-platform-v1-device.lock` for the whole device session.

Build against the exact installed kernel (see `tools/development/audio-observer`):

    python3 tools/build/run.py --output out/highres-observer-build -- \
        make -C /src O=/build/kernel M=/build/afe-lab modules

Commands are written to `/sys/kernel/debug/y2_afe_lab/cmd`, results read from
`.../out`: `hold 0|1`, `r <off> [n]`, `dump <a> <b>`, `w <off> <val>`,
`m <off> <mask> <val>`, `dma_alloc|dma_free|dma_fill32|dma_zero|dma_peek|dma_info`.
Writes are only for source-backed hypothesis tests with the I2S output disabled,
the headphone switch off and no PCM stream running.
