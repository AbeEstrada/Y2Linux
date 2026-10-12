# Stock suspend reverse-engineering ledger (POWER-FINAL-16)

Target: the Y2's own stock FM kernel, `evidence-private/20260908-ram-map/fm-decompressed.bin`
(base 0xc0008000), wrapped with its 54,692 kallsyms into `out/rea/fm-kernel.elf`
(SHA-256 `329466b3…b6d003`, generator script kept in the session scratchpad and reproducible:
one PT_LOAD at 0xc0008000 plus `.symtab` from `fm-symbols.json`). Analysed with REA 6.4 /
Ghidra 12.1.2 default auto-analysis. Everything below is **static analysis of the shipped
stock image** (pseudocode is Ghidra output, not source). Nothing here was observed running.
Evidence IDs are REA session records from 2026-10-12.

Goal of 16: stock sleep parity, ≈0.1 points/h (≈1 % per night; ≈1.3 mA average on the stock
1300 mAh model). 15 measured ≈1.6 points/h (voltage-derived), i.e. roughly 20 mA average.
Maintenance wakes are **not** the cause: 2.6 s awake per 1800 s (0.14 % duty, archive 109,
boot e2952adf rows). The floor while suspended is the gap.

## Findings

| # | Question | Stock behaviour (address, Evidence) | Y2 Linux 15 | Status |
| --- | --- | --- | --- | --- |
| F1 | Does our SPM arming differ from stock? | `spm_go_to_sleep(cpu_pdn, infra_pdn, pwake)` 0xc0033b50 (`ev_168f2760…`); `spm_kick_pcm_to_run` 0xc003308c (`ev_e1d13388…`): SPM_CLK_CON bit14 set iff !cpu_pdn, bit15 (CC_DISABLE_INFRA_PWR) set iff !infra_pdn, then `|0x60` (LOCK_INFRA_DCM, SRCLKENA_MASK); PCM_MAS_PAUSE_MASK=~0; PWR_IO_EN=0x81. `spm_set_wakeup_event` (`ev_facc0b82…`): timer default 0xfff0ffff, WAKEUP_EVENT_MASK=~wakesrc, 0x900 `&4 | 0xe00`. | `spm-suspend-policy.h` writes the same bits. | **Answered: identical.** INFRA staying powered (`last_lost=0x0`) is not caused by the kick. |
| F2 | What does stock do at screen-off to the display? | `mtkfb_early_suspend` 0xc0515f18 (`ev_1f0e761f…`): backlight 0, `DISP_PrepareSuspend`, release syncs, `DISP_PanelEnable(0)` (→ `lcm_suspend`), `DISP_PowerEnable(0)`, `DISP_PauseVsync(1)`, `disp_path_clock_off`. `spm_mtcmos_ctrl_disp` 0xc00350a8 (`ev_59e40d65…`) is called only from the clock manager (0xc003fa2c/0xc003fa4c, `ev_c9c1613e…`): off = INFRA TOPAXI_PROT_EN (0x10001220) bit1, wait PROT_STA1 (0x10001228) bit1, DIS_PWR_CON (0x1000623c) `&~0x1d | 0xf12`, wait PWR_STATUS/PWR_STATUS_S bit3 clear; on = reverse. | Only the MFG (GPU) domain is a genpd (`spm.c`). DIS is never powered off; 15's sleep rows show `power=0x314c` (bit3 DIS **on** while asleep). MMPLL/VENCPLL on at entry match this. | **Answered (static). Gap G1.** |
| F3 | Does stock switch PLLs off explicitly at suspend? | `clkmgr_early_suspend` 0xc003f494 (`ev_7ecdab45…`) only logs CLK_CFG_0..3. PLL off follows clock reference counts (last user off). | PLLs on at entry (golden rows). | **Answered: PLL-off is a consequence of releasing their users (DIS/MM, MSDC, audio), not a separate step.** |
| F4 | DRAM at screen-off | `mt_emifreq_early_suspend` 0xc0038ef4 (`ev_a810f583…`): unless disabled, `mt_h2l_dvfs_mempll()` (DRAM PLL high → low). | No EMI/MEMPLL DVFS in Linux. | **Gap G4, needs decoding of `mt_h2l_dvfs_mempll` (risky: DRAM timing).** |
| F5 | PMIC at screen-off | `pmic_early_suspend` 0xc04b3a84 (`ev_45809a69…`): VREF18_ENB=0, CLKSQ_EN_AUX=1, AUD26M_DIV4 PDN=0, AUXADC SDM HW mode/clock settings. Separate from `pmic_mt6323_suspend` 0xc04b3dd4. | Not adopted (13 decision: would change ADC behaviour). | Known, re-evaluate with G5 (PMIC golden). |
| F6 | CONNSYS when Wi-Fi/BT off | `mtk_wcn_consys_hw_pwr_off` 0xc0564cd4 (`ev_1aa5ca22…`): `consys_hw_reg_ctrl(0)` + GPIO off. | PWR_STATUS bit1 (CONN) = 0 in 15 rows. | **Answered: CONN already off.** |
| F7 | Stock suspend hook inventory | Regex procedure search (`ev_496e0cfe…`): clkmgr, emifreq, mtkfb/disp, AudDrv (`AudDrv_Suspend_Clk_Off`), msdc, musb, mt_i2c, uart, gpio, kpd, thermal (`mtktscpu_thermal_clock_off`), battery, pmic, wcn. | — | Inventory only; each still to compare. |

| F8 | When does stock compare its golden table? | `slp_suspend_ops_prepare` 0xc0035ee4 calls `mt_power_gs_dump_suspend` only if a debug flag is set (`ev_44f0433f…`). | — | **Answered: the golden table is MediaTek's reference checklist, not a recorded Y2 state.** Rows are reached by stock mechanisms, never forced blindly. |
| F9 | Boot-time DCM | `mt_dcm_init` → `dcm_enable(0x1ff)` 0xc003c154 (assembly `ev_9054224d…`): CPU (0x10208000 bit12, MCUSYS+0x5c bit9), TOPCKGEN, IFR (INFRACFG 0x08/0x10/0x14/0x50/0x54/0x58, DRAMC+0x1dc bits 24/25), PER (PERICFG 0x50/0x54/0x58 + MSDC/USB/I2C local bits), SMI/DIS (MMSYS 0x120..0x134, LARB0+0x14, SMI+0x300) only while each domain is on. | Only SLIDLE bus DCM. | **Implemented in 16** (`dcm-policy.h`): 10 golden rows. PERI DCMDBC follows stock code (0x80), not the checklist (0xf0). Peripheral-local bits not adopted. |
| F10 | Clock tables | Mux table `0xc09b17c8` (13 muxes, PDN bits, `clkmux_disable_op` sets PDN); PLL table `0xc09b1678` (6 PLLs; `mt_plls_init` sets MMPLL/VENCPLL refcount 1 for the display); `sdm_pll_disable_op` 0xc003f4dc / `sdm_pll_enable_op` 0xc0041c88 (assembly). | PLLs are read-only rate clocks in Y2 Linux; nothing ever switched one off. | **Implemented in 16 as golden sleep entry** (`golden-apply-policy.h`, `spm.golden_apply` bitmask, save/restore). MAINPLL/ARMPLL/AXI mux never touched. INFRA PMIC_WRAP (bit 23) kept on (SPM sleep PMIC access). |
| F11 | MD-side peripheral requests | Golden `PERI_PDN0_MD1_STA` = all gated; Y2 reads 0. No AP write found in stock (`gate_md1` writes 0xffffffff to an unresolved ccci block +0x14). | — | **Answered on hardware 2026-10-12 (owner-authorised live test, 16 boot `0b0e8a77`, probe module `out/power-final-16-build/md1probe/`):** layout MD1_SET 0x20 / MD1_CLR 0x28 / MD1_STA 0x30 confirmed (bit 0: 0→1→0); all 26 bits SET → STA 0x03ffffff for 200 ms with AP PDN0_STA unchanged (0x02ecf3fd), USB/SSH, Wi-Fi and charger alive; restored to 0. MD_MASK 0x38 = 3. **17: gate all MD1 requests at boot (switch).** |
| F12 | PMIC golden | `mt6323_power_gs_suspend_data` 0xc0757cd0, 44 rows. | Never compared at entry. | **16 captures it read-only** at every sleep entry (`pwrap.pmic_golden`). |
| F13 | Fuel gauge | `fgauge_get_Q_max` 0x514 (1300 mAh), `fgauge_get_profile(25)` 0xc09d117c (95 rows, 4175 → 3400 mV), `r_profile` 0xc09d1d5c (191–326 mΩ). | Estimated 9-point curve. | **Implemented in 16** (battery-profile.json, OAM charging correction, mAh estimate). |

## Gaps to close in 16 (ranked by expected sleep-current effect)

- **G1 DIS power domain + MM clocks off at screen-off** (F2): add a DIS genpd with the exact stock sequence,
  attach the display pipeline to it so DRM's disable powers it down, which also releases MMPLL/VENCPLL.
  Also the awake-dark power win the 15 handoff suspected ("Skipping unprepare" message).
- **G2 INFRA power-down never happens** (`last_lost=0x0`): F1 rules out the SPM kick. Next: find what keeps
  INFRA requested (SRCLKENA/26 MHz requesters, PCM `R7`/`SPM_PCM_SRC_REQ`, bus masters left on: DIS, MSDC, USB).
  Expected to follow partly from G1/G3.
- **G3 Golden-table rows**: INFRA/PERI clock gates, PERI MD1, bus/peri DCM, CLK_CFG mux power-down, MSDCPLL
  (eMMC/SD clock release at suspend), audio clocks (`AudDrv_Suspend_Clk_Off`), thermal clock off.
- **G4 DRAM low-power** (F4): `mt_h2l_dvfs_mempll` and DRAMC+0x1dc golden row. Last, highest risk.
- **G5 PMIC golden** (44 rows) and VEMC3V3/VGP2/panel deep standby/BAT_L interrupt (13 list).

## Non-power defects carried into 16

- **Defect B** (USB TX dead after every wake): DMA-interrupt unmask (MUSB+0x200 bits 24..31) theory; first
  read the full 32-bit value plus DMA channel registers, then re-arm in `y2_musb_enable`/`after_restore`.
- **Defect C (new, archive 109):** with VBUS present but the host unconfigured/off (`udc=default`), sleep is
  refused every 5 min (`charger_or_usb_active`) while the charger is `INHIBITED`/"Not charging": 75 % → 32 %
  in 6.3 h on a powered-off PC. Sleep policy must allow suspend when nothing charges and no host is configured.
- Python 3.15 `/dev/kmsg` flush EINVAL (S03/S05), power-journal keeps only ≈4.5 h.
