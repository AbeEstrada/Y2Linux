# Y2 Platform 1.0 power / battery final investigation

2026-10-05. **IN_PROGRESS; MORE_WORK_REQUIRED.** Hardware corrections need owner
installation; endurance and full-suspend acceptance remain open.
Machine evidence: [power report](data/y2-platform-v1-power-final.json).
Private raw incident/media/network receipts remain ignored and are not exported.

## 1. INSTALLED FIRMWARE IDENTITY

SSH, persisted boot records and candidate metadata identify USB-FINAL-02, release
1.0.0-platform-v1-usb-final-candidate.2, Linux0cb779267ca90740853dc02695166d75f36faa29 /
Reborn2444e0f65811e688250a8cd069a57dd780b2d6d3. Kernel6.18.0-y2linux-platform-v1-usb-final-02;
root2025.02.18-platform-v1.26; Buildroot2025.02.18. API1, featurecontract2,
batteryprofile1, lowbatterypolicy2, DATA/layout1. mediatek_drm is the sole loaded
module; radio/audio/power drivers are built in. The actual owner image is the
USB-final worktree's usb-validation-02, not main or Baseline01.
BOOTIMG rehash4fea3d1e0fac307d7cb444d38d560e0cbc4f29d5c4e6be574247dc6833047382;
Y2ROOT fresh rehash ab5a93da8a8642b587fd7eef50dbb76c2026825a90114145110e28b70c0587ce.
Dedicated paired codex/platform-v1-power-final worktrees start at that exact pair.
All yesterday's USB source remains inherited.

## 2. OVERNIGHT INCIDENT FORENSICS

Owner reports unplugging around01:00, dead around09:00, then wall charge required
to power on; the preceding UI value was88%. Incident boot6f2838c9 records voltage
decline, no full-system suspend and orderly shutdown_complete; no unclean boot.
Last retained low-voltage sample is3.400268V at monotonic22449.233s. Retained
maximum is3.920141V, full=0; there is no retained charge termination or>4.1V
sample. This proves a real voltage-floor shutdown, not merely a displayed0%.
It does not prove pack protection cutoff, initial usable capacity or that charge
was full before retained logging. Minute voltage/status records and shutdown
journal existed, but no exact last-night device/process/clock journal did.
Wi-Fi was enabled/associated, playback was paused and display had blanked.
NTP/wall-clock corrections mean durations must use monotonic timestamps.
Old USB allowance2000uA/sourceSDP is a USB budget/state observation, not measured
battery current or proof contradicting the owner's cable removal.
New persistent journal retains events and five-minute snapshots with bounded
rotation, no extra sampling timer, and a nonblocking writer lock.

## 3. BATTERY MEASUREMENT ARCHITECTURE

BAT0 voltage is a real MT6323 AUXADC observation. SOC is a provisional filtered
voltage estimate. No validated pack-current, coulomb-counter or pack-temperature
telemetry is exposed. PMIC ISENSE/BATSNS raw ADC channels exist; board differential
shunt wiring/calibration is not established, so raw counts cannot become mA.
A PMIC die temperature is not battery NTC temperature. Nominal capacity is unknown.
Exact vendor battery net-current/coulomb methods are stubs; its charger differential
ADC estimate assumes68mOhm, which is not verified on this Y2.

## 4. CHARGER / MT6323 ARCHITECTURE

The built-in charger is the sole policy owner: source/budget selection,1Hz safety
sampling, watchdog service, checked CV/OVP/thermal/engine state, latching faults,
voltage-limited full/recharge. Its4-second hardware watchdog and2500ms late-service
fault remain. USB supplies the allocation; a selected ceiling is not actual pack
current. DORMANT PCM has autonomous PMIC-wrapper requests outside regmap write
validation; those requests require correct slot initialization.
Pinned primary source: [MT6582 vendor tree](https://android.googlesource.com/kernel/mediatek/+/d53dd75c3ff77cac3f5be58fddfe660e94f94d64/).
The observed protection fault correctly inhibited charging; it was never cleared
or bypassed experimentally.

## 5. SOC ALGORITHM

Curve(uV,%):3400000/0,3500000/5,3600000/10,3700000/25,3800000/45,
3900000/65,4000000/80,4100000/95,4175000/100. Filtering30s,rest120s,
15mV deadband,75mV charging correction,1percentage-point/minute rate bound.
ChargerFull plus>=4.160V permits100%. Load sag, relaxation, temperature, pack aging
and unknown capacity defeat an exact voltage-to-percent mapping. There is no
source hard88% cap; that owner observation does not prove full. SOC math is
preserved pending calibrated charge/discharge evidence; drain is not fixed by
changing the percentage. Fresh same-boot voltage from the protection owner is
reused by Reborn; stale/absent/invalid records fall back to AUXADC.

## 6. SAFE CHARGING LIMITS

Configured maxima: SDP>=500mA allocation450mA; SDP100–499mA70mA;
SDP<100mA0; DCP/CDP/Apple650mA; unknown70mA. Deep-discharge/prechargeDCP
is limited450mA. CV4.175V, independent upper guard4.2V. No current/voltage/
temperature/low-voltage protection limit was raised or disabled.

## 7. PC USB CHARGING

Live current boot reports SDP,500mA allocation,450mA selected,Charging,fault0,
positive voltage trend and working ECM/MTP. Baseline return after the first wall
fault remained latched and did not charge until the one graceful diagnostic-module
removal/recovery reboot. Current PC charging is a bounded PASS; near-full
termination and actual charge-current accuracy are not qualified.

## 8. WALL CHARGING

First detached DCP window300.620s selected650mA with C3 active; protection
fault0x80 appeared at monotonic1610.374s:CHR_CON0=0x62 lost HV enable,
subsequent verified stop and voltage decline. Read-only matching-kernel probe
found broader regulation-field losses. Second detached DCP window300.299s with
C3 automatically quarantined charged throughout,3.701513→3.740185V,SOC8→13,
fault0. The device remained on wall charge beyond each bounded window.
Different boots limit attribution; the second test is not a matched post-fix result.
No wall enumeration dependency or MUSB IRQ activity was observed detached.

## 9. CPU FREQUENCY

schedutil,598000–1300000kHz. Effective stats record all five OPPs598000,
747500,1040000,1196000,1300000. Quiet PC windows are predominantly598MHz;
no evidence of an overnight permanently high-frequency/QoS lock. Exact per-window
frequency residency is in the JSON report. Safety floor/OPPs are unchanged.

## 10. CORE PARKING

Natural hotplug parks secondary cores after adaptive post-burst hold; all four
can remain online during short observer-affected windows. Second wall window
parked cores around257/262/267s. Heavy endpoint descriptions can trigger demand
and extend hold, so report online states and per-CPU wall denominators rather
than infer perfect core utilization. No forced core disable or arbitrary IRQ
redistribution was applied.

## 11. C1

Real WFI entries in every recorded idle window. First wall CPU0:14426 entries,
83.5625%wall residency. Second wall:7471,28.9026%. USB windows have larger C1
share because live USB owns required clocks. Machine report holds per-CPU counts.

## 12. C2

Real SLIDLE works. First wall CPU0:1246entries,1.5491%;second wall18690,
64.4756%. Clock restore safeguards remain. C2 persists during safe charger C3
exclusion; active watchdog service does not require removing C2.

## 13. C3

Implementation present and physically entered in the first wall window:2554
CPU0 entries,11.7177%. This is context-loss DORMANT, not full-system suspend.
Historical65.245%UART01 evidence is a different workload/image. Current WARN
boot has0 entries and must remain quarantined.
A concrete defect is identified: retained480-word PCM requests wrapper slots5/6,
while normal CPU preparation initializes0–2 only; live5–7 were0:0. Full-suspend
preparation populated them, but runtime C3 did not call it. Autonomous requests
can then address charger register0 instead of VPROC. Source now initializes and
readbacks5–7 to the verified active VPROC bank/selector72(existing1.15V floor)
before C3 admission. Failed initialization/request checks quarantine C3. Physical
post-fix proof is pending; no claim that all observed register losses are bus-traced.

## 14. C3 PRODUCTION POLICY

Installed USB02 fresh healthy boot:Enabled,budget-1,state2disable0. This firmware
is not the historical fresh-boot budget-zero policy. Overnight logs show startup
Enabled. After the necessary reboot, DRM WARN/taint512 makes policySkipped,
reasonkernel_tainted_or_unknown,budget0,state2disable1. That guard was respected.
Source adds PMIC-slot readiness and active-charger/watchdog prerequisites;
USB/CONSYS/display/workload/topology/deadline/context/UART/CIRQ guards remain.
Actual overnight residency is unknown because the old journal lacked counters.

## 15. CPUIDLE BLOCKERS

| Blocker | Owner | Observed idle behavior | Action |
| --- | --- | --- | --- |
| USB clock | MUSB/configfs/ECM | Valid whilePCconfigured; detachedoff/noIRQ | Preserve yesterday's lifecycle |
| CONN/APDMA/BTIF | Shared CONSYS radios | Wi-FiOn owns clocks; runtimeOff releases | Test radio states; no fake clock gate |
| Topology | Natural CPU parking | Post-burst adaptive hold | Preserve safe demand restore |
| Display/vblank warning | DRM first takeover | Reboot warning quarantinesC3 | Checked first-only inheritedOVLstop |
| PMIC wrapper idle slots | PWRAP/SPM | Slots5–7zero beforeruntimeC3 | Initialize/readbackactivebank1.15V |
| Active charge watchdog | Charger | Needs1Hz safe service | Explicit DORMANT exclusion;C1/C2remain |
| AFE/CS43131 | ALSA/DAC | PausedPCMclosed/runtime suspended | Preserve idle release |
| eMMC/SD | MSDC | Clockgatebetweenrequests; UUIDprobes recurring | CacheUUIDbyfreshmount/diskseq |
| UART | UARTPIO/SPM ACK | Existing conditionalrequest/ACK | Preserve validated handoff |
| I2C/input | APT32F/keypad/GPIOkeys | Wheel/keypad IRQquiet; navigation50Hzpoll | No unverified EINT remux |

Exact blocker registers/counters for each recorded window are retained privately;
missing decoded-owner states are not guessed.

## 16. WAKEUP SOURCES

No unique whole-CPU wakeups/s measurement is available; wakeup_sources counts
system-suspend blockers, not every runtime idle exit. JSON separately reports
IRQ/s, context-switch/s, per-thread CPU, cpuidle entries/exits and available wakeup
source deltas. These proxies must not be renamed battery current or CPU wakeups.

## 17. IRQ OFFENDERS

Ranked IRQ deltas per window are in the JSON. Timer/IPI/scheduler activity dominates
the retained short windows; no detached MUSB storm, untouchedwheel/I2C0/keypad
storm or AFE playback activity was observed. Per-CPU IRQ counters can decrease
across hotplug; report those discontinuities as unknown rather than fabricated
negative/overflow event rates. Detailed timer attribution remains for healthy
post-install windows.

## 18. USERSPACE POLLING

Same-boot PC/radiosOff/paused-screenOff60-second comparisons:

| Source | Before | Isolated after | Unit |
| --- | ---: | ---: | --- |
| MTPio_thread |49.7586|0|threadcontext-switches/s |
| BThelper main |15.1216|0.1989|threadcontext-switches/s |
| BThelper gmain |15.6356|0|threadcontext-switches/s |
| Reborn main |20.1124|NOT_MEASURED|threadcontext-switches/s |
| Rebornwatchdog |1.2436|NOT_MEASURED|CPU%ofonecore |

MTP replaces20ms timedcondwait withsignaled blockingwait, preserving32×64KiB
queue/DMA/FIFO/confinement/cancellation. BThelper watches only privateintentdir,
not everypower.json publication in/run/y2. Sole reconnect ownership stays.
SSH now waits on passive rtnetlink plus signal FD, retains5s fresh readiness
heartbeat, checks stableUSBaddress at60s backstop ratherthan spawningipevery1s;
address changes/childdeath/termination wakeimmediately. Reborn static/dark waits
are workload-bound and evdev/control/AVRCP event-driven. No high-frequency new
telemetry or permanent lab module is shipped.

## 19. REBORN IDLE

Baseline main~0.85%onecore/20.11switches/s; watchdog~1.24% due recurring
source/voltage probes. Source:pauseddark1s bounded wait;litstatic250ms;playing50ms;
dirtylit34ms framebudget, with evdev/control/AVRCP wake descriptors. UUID caches
are keyed by live device,mountID,kerneldev/diskseq and boundedfour; every source
observation retains mount/card/CID revalidation. ADC reuse is freshsameboot<5s
and positiveonly. AVRCP bus/projection/shutdown descriptorwait removes200ms
polling; actualremotecommands wakeUI immediately and senderauthorization remains.
The temporaryARMReborn trial hit the existing stalled DRM commit, controlRPC
could not answer, so no matched after claim is made. Originalbinary restored;
healthy image is required to qualify rendering/idle/control responsiveness.

## 20. DISPLAY / GPU

Healthy first boot screen-off released scanout/Lima/MFG and backlight. Reboot
firstvblank warnings then repeatedflip/commit/mutex timeout caused owner-visible
black/frozen UI even after briefPower wake, taint512 andC3safeSkip. DSIprobe
alreadyparks inheritedDSI, mutexownerclears membership, but OVLclk_enable leaves
loaderOVL_EN1; config then intentionallyskipsreset toavoidreset-with-enabledSOF
hang. Source now stops/verifies inheritedOVL/layers onlyatfirstownedclkenable,
then normalconfig/reset/start. Subsequentliveplanes are unchanged. Native dropped
write/clockerror/nonY2/live-pathtests pass; actual cold/warmboot fix is NOT_PROVEN.
No warning suppression, C3 bypass, newtiming/PLL/rails or broadGPU redesign.

## 21. AUDIO / CS43131

Paused/stopped ALSAPCM is closed; AFE/I2S idle clocks gate andCS43131runtime
suspends in retained healthy snapshots. No temporaryhighreslabmodule is installed.
NativeS16/44.1/48 path, buffers/volume/pacing and codecPM rollback instrumentation
remain. Audio idle/playback matrix and post-full-resume restoration must be rerun
on the owner-installed warning-free build.

## 22. WI-FI

Wi-Fi was enabled/associated overnight and validly ownsCONSYS; no stored per-IRQ
night trace establishes scans/retry count. RuntimeOff removesradio blockers.
Campaign freshness/30sRSSI/inventory/DNSreuse is inherited. FAST_PSP was historically
reverted toCAM and cannot be cited as successfulpower saving. On/disconnected/
connected matched battery-only matrix remains pending; no arbitraryfullmac power
mode/keepalive or reconnect owner changes were made.

## 23. BLUETOOTH

Saved/runtimeOff during recordedisolatedwindows,attempts0/completed0. No peer
reconnect storm was observed; high helperwake rate came from shared-directory
inotify notifications. Privateintentdirfix achieves0.199main/0gmain switches/s
with intent responsiveness preserved by actualnativefixture. Realon/disconnected/
connectedpeer tests remain pending; no availableheadset is assumed.

## 24. USB

DetachedMUSBbusclockoff,noMUSBIRQ; MTPresponder exits with cable detached, so
its PC50Hz thread is not by itself the unpluggedovernight cause. Installed USB02
lifecycle/configfs/MTP+ECM/PIO/DMA/FIFO/32×64KiB ring is inherited unchanged.
MTPwaitfix passed real16MiB KDEdesktopupload/download withdevice andreturned
SHA25684ebb5bc9e1e188628f3c87ff3c06906d45b775f2692555efc2be7deb7795696;
ownedfiledeleted afterwards. ECM/SSH returned after responder replacement in
sameboot,450mAcharging/no fault. Originalresponder restored andverified.
Hostinterface wasbusy with desktopowners; none werekilled to force libusb access.

## 25. STORAGE

Recurring safe UUIDsuperblock probes every2s were traced towatchdog sources().
Source caches only UUIDby fresh mount/diskseq identity; never caches oldcard
admission, never skipsCID/currentmount/no-follow checks. Failedprobesare notcached.
MMCclock/runtime-PM and ext4/journaling remain unchanged; no broadcache drop,
filesystemreset, artificialwrite suppression ormedia-library modification.
Persistentjournalsteadywrite cadence is5minutes,rotated2×256KiB.

## 26. INPUT

APT32F is interrupt-driven, oneI2Cread pervaliddataready IRQ, untouchedwheel
IRQquiet. Hardwarekeypad/PMICPowerare IRQ-driven. Five GPIO navigationkeys remain
upstreamgpio-keys-polled20ms, a real50Hz runtime-idle limitation. Exactnavigation
GPIO/EINT mux is not proven; no guessedremux, slowedbuttons or losttransportkeys.
Fullsuspend wouldfreeze this poll if qualified. Evdev heldkeytiming stays15ms
whileheld, input/controlarrivalwake staticwait immediately.

## 27. TIMERS / RTC

CONFIG_NO_HZ_IDLE andCPU_FREQ_STAT enabled. GPT/localarchitecturaltimer/dormant
handoff are inherited. Requiredcharger safety/watchdog remains1Hz. Knownoptional
20msMTP,50msdarkUI and sharedBThelpernotification work is removed in source;
GPIOnavigation50Hz remains. Actualtimer/IRQ/softirq andcontextdeltas are captured
at boundedendpoints; no perpetualtimerstats/trace observer runs overnight.
Awake RTC and realfullsuspend RTC are separate gates.

## 28. FULL SYSTEM SUSPEND

Installedcode includes campaignSPMcontext/BIU/normalPCM/timer/CIRQrestore,
CS43131rollback/substepjournal andRebornquiescence ACK. Ordinaryproductrequest
still returnsphysical_qualification_required (orcharger_active). Overnight stayed
runtimeidle. HistoricalBaseline02 RTC trial watchdogrebooted afterdevice resume:
DEVICES_RESUMING,wake0x20,PCM596,reset59325253,unmatchedCS43131resumeentry.
That isFAIL, notsamebootresume. CurrentWARN-tainted/displaystalledboot is unsuitable
for newfullsuspend. After ownerinstallation:freezer/devices/platform/processors/core,
thenboundedRTC/Power withbackstop; requirecompletejournal,positiveactualresidency,
sameboot, restoredUI/audio/USB/storage/radios. No automatic sleep until qualified.

## 29. POWER-BUTTON POLICY

Current shortpausedPower requests guarded fullsleep and mayonlyblank onrefusal;
playingPowerblanks, darkshortPowerwakesdisplay, longPoweropensshutdownconfirmation.
It cannot promise deep sleep. No five-/30minute automaticfullsuspend policy is
activated because samebootwake is still unqualified. PreserveUX while closing
that hardware gate; onceproven, add bounded paused-inactive sleep withplayback,
transfer/update/charger busy exclusions and configurabletimeout.

## 30. LOW-BATTERY POLICY

Independent3400000uV floor; low3500000/recover3600000;5consecutive1Hz
samples;10sgrace; provisionalSOC alone cannot force shutdown. Existingfloor
caused orderlyincident shutdown. No deepdischarge, loweredfloor or protection
bypass. Shutdownjournal records exactreasonandvoltage forfutureincidents.

## 31. BATTERY HEALTH EVIDENCE

Unknownnominal/effectivecapacity and no packcurrentintegrator. The pack has not
beenfully chargedunder verifiedterminationthencharacterized withcontrolledload.
No justifieddegradationdiagnosis. Softwaredefects andmissingdeep sleep are real,
but exact fraction ofovernightenergy explained is unknown. Aftersoftwarequalification,
characterize safe normalidle/playback untilbeforeexistingfloor, recordingvoltage,
SOC,time,sag/relaxation andstate; no intentionalprotectioncutoff.

## 32. BEFORE / AFTER POWER MATRIX

The JSON provides6 sanitizedwindows, exactdurations/counters andrawreceipt
hashes. Matchedcomponentcomparisons arePC60s/radiosOff/pauseddark/sameWARNboot;
whole-systembefore383.11context/s/259.87IRQ/s, MTPisolatedafter289.54/211.70.
Thoseare eventrates, notuniquewakeups ormeasuredmA; hotplug/observer constraints
are retained. BTisolatedafter342.73context/s/250.78IRQ/s withoriginalMTP restored.
AllA–J healthy-final-buildstates,60sand5mincleanunpluggedC3,playing,radiopeer
andfullsleep remain pending. Differentwallboots arediagnosticassociation only.

## 33. LONG-IDLE RESULTS

Two5minwallwindows completed: firstfaulted/voltagefell, secondchargednormally
withC3gated. Optimizedbattery-only5min,30min,2h andovernight NOT_RUN.
Requirehealthyowner-installedkernel andsafechargedbattery beforeendurance;
short/proxyresults are not battery-life qualification. Diagnosticobserver~0.62CPU
seconds in60s atcounterendpoints (~1%onecore); heavy~1.8CPU seconds ofdescriptions
areoutsidewindow. Itdoesnothing duringthe declared60s sleep. Five-minutewindows
reduceendpointbias; no claimedzerooverhead.

## 34. CHANGES MADE

CheckedruntimePCMidle-slotinitialization/readiness;activechargerC3guard;
firstprotectionregister-mismatchdiagnostics;source-change-onlyUSBsupplynotification;
first-onlyOVLtakeover;event-drivenMTPRXwait;privateBTintentwatch;
passiveSSHaddressmonitor;boundedpersistentpowerjournal;duplicateAUXADCreduction;
Rebornpaused/staticeventwait andAVRCPnotifier;freshmount/diskseq UUIDcache;
endpoint-onlypoweraudit withobserveraccounting/counterdiscontinuity handling.
All changes stay on isolatedpairedpowerbranches; main/USBownerworktrees unchanged.

## 35. CHANGES REJECTED

No arbitrarychargeincrease,voltagefloorlowering,protectionfaultreset,coulomb/mA
fiction,unsafe1.05Vvendoridleselector,guesspinmux/clockgate,forcedcoreoffline,
C3taintbypass,unqualifiedautosuspend,wakeupreboot-as-success,high-frequencyjournal,
stockfirmwareflash,USBtransportrollback orbatterydegradationblame. Original
firmwarelive comparison mayuseexistingADB later; SSHpatchisnotneeded now.

## 36. TESTS

Affected CPU/charger native suite72PASS; SSH/transfer7PASS;
newpowerjournal5/poweraudit2/displaytakeover1PASS; USB28/nativeMTPringcancel/
protocol/filesystemPASS; Bluetooth12/nativeeventfixturePASS. Rebornfmt/strict
workspacealltargetClippy/fullworkspace326PASS afterAVRCPwatchregistration repair.
Intermediatefailedtestreceipts retained; none treatedasPASS. ARMreleasebuilt before
lastAVRCPadjustment; latestARM/fullproduction/QEMU/package gates pending.
KernelImage/zImage/modulescompilePASS includingnewslot/OVL/chargercode; inherited
vendorWi-Fiwarnings remain. Finalsource-boundcandidatechecks willbe appended.

## 37. COMMITS

InstalledbaseLinux0cb7792/Reborn2444e0f; correctivework presentlyuncommitted.
Recordcompiledsourcepair andsubsequentdocumentation-onlyseal separately.

## 38. CANDIDATE / HASHES IF BUILT

NOT_BUILT. A coherentpreservingBOOTIMG/Y2ROOTpair willbe sealed aftersoftware
andpackagevalidation. Userflashes; agentneverflashes/pushes. Futurecanonicalpath:
/home/luca/Dokumente/Code/Y2Linux/out/y2linux-platform-v1-power-final-candidate.
Afterownerflashresumeexactpendingmatrix; do notrestartforensics.
