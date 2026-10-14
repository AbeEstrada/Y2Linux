# SPDX-License-Identifier: GPL-2.0-only
# Y2 recovery image (OTA-35). init sources this when the kernel was loaded from
# RECOVERY (y2.recovery=1 in that image's own DTB). It installs or restores
# BOOTIMG + Y2ROOT through y2-update-core, records what happened on Y2DATA and
# powers off: a software restart leaves the panel dark (open defect), so the
# owner starts the new system with Power. It never starts the normal system,
# formats storage or reboots in a loop. Uses init's y2_stage, start_observer
# and y2_find_partition.

recovery_screen() {
    printf '%s\n' "$@" > /run/y2/recovery-screen.tmp &&
        mv -f /run/y2/recovery-screen.tmp /run/y2/recovery-screen
}

recovery_log() {
    echo "<6>Y2RECOVERY: $*" > /dev/kmsg
}

# The owner's restart switch (/data/updates/restart.json, "mode": "reboot"),
# read while Y2DATA is mounted: restart into the result instead of power off.
recovery_restart=
recovery_restart_mode() {
    grep -q '"mode": *"reboot"' /newdata/updates/restart.json 2>/dev/null && recovery_restart=1
}

# Keep evidence on Y2DATA (the normal system's diagnostics read it), then turn off
# or, with the owner's switch, restart.
recovery_off() {
    if [ -n "$recovery_data_mounted" ]; then
        mkdir -p /newdata/logs
        cp /run/y2/recovery-result.json /newdata/updates/recovery-last.json 2>/dev/null
        dmesg > /newdata/logs/recovery-last.log 2>/dev/null
        sync
        umount /newdata 2>/dev/null
    fi
    sync
    sleep "${1:-12}"
    if [ -n "$recovery_restart" ]; then
        recovery_log 'restart'
        reboot -f
    fi
    recovery_log 'power off'
    poweroff -f
    # poweroff never returns on this hardware; keep PID1 alive if it does.
    while :; do sleep 60; done
}

# Unknown or manual-repair state: keep the request (LK returns here) and keep
# PID1 with a console shell, exactly like the BOOTIMG rescue.
recovery_stuck() {
    recovery_log "$*; staying in recovery"
    recovery_screen 'Update needs attention' "$1" '' 'Connect the player' 'to a computer.'
    if [ -n "$recovery_data_mounted" ]; then
        cp /run/y2/recovery-result.json /newdata/updates/recovery-last.json 2>/dev/null
        dmesg > /newdata/logs/recovery-last.log 2>/dev/null
        sync
    fi
    while :; do
        /bin/busybox sh </dev/console >/dev/console 2>&1
        sleep 1
    done
}

charger_online() {
    for supply in /sys/class/power_supply/*; do
        case "$(cat "$supply/type" 2>/dev/null)" in USB|Mains) ;; *) continue ;; esac
        [ "$(cat "$supply/online" 2>/dev/null)" = 1 ] && return 0
    done
    return 1
}

y2_stage recovery
recovery_data_mounted=
recovery_screen 'Software Update' 'Starting' '' "Don't turn off the player."
[ -x /sbin/y2-recovery-ui ] && /sbin/y2-recovery-ui &
recovery_log "$(cat /sys/firmware/y2_boot/metadata 2>/dev/null)"
echo 1 > /sys/firmware/y2_boot/normal_boot || recovery_stuck 'Storage did not start'
if [ -w /sys/devices/system/cpu/cpufreq/policy0/scaling_governor ]; then
    echo schedutil > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor
fi
start_observer
n=0
while [ "$n" -lt 800 ]; do
    datadev=$(y2_find_partition Y2DATA 79324c69-6e75-4801-8000-000000000102 2104320 1638400)
    [ -n "$datadev" ] && break
    n=$((n+1))
    sleep 0.05
done
[ -n "$datadev" ] || recovery_stuck 'Storage not found'
e2fsck -p "$datadev" > /dev/kmsg 2>&1
[ "$?" -le 1 ] || recovery_stuck 'Storage check failed'
mount -t ext4 -o rw,nosuid,nodev "$datadev" /newdata || recovery_stuck 'Storage did not mount'
recovery_data_mounted=1
[ "$(cat /newdata/.y2data-schema 2>/dev/null)" = 1 ] || recovery_stuck 'Unknown storage format'
recovery_restart_mode
/bin/busybox timeout 10 /bin/busybox seedrng --seed-dir=/newdata/system/entropy > /dev/kmsg 2>&1 || :
y2_stage recovery_install

attempt=0
while :; do
    /sbin/y2-update-core recovery > /run/y2/recovery-result.json
    outcome=$(sed -n 's/.*"outcome":"\([a-z_]*\)".*/\1/p' /run/y2/recovery-result.json)
    recovery_log "outcome=${outcome:-none} $(cat /run/y2/recovery-result.json)"
    [ "$outcome" = needs_power ] || break
    # A low battery and no charger: wait for one (ten minutes), else turn off.
    # The request stays set, so the next power-on returns here.
    recovery_screen 'Connect the charger' 'The battery is too low' 'to install the update.'
    attempt=0
    until charger_online || [ "$attempt" -ge 300 ]; do
        sleep 2
        attempt=$((attempt+1))
    done
    charger_online || { recovery_screen 'Battery too low' 'Charge the player, then' 'press Power to continue.'; recovery_off 10; }
    recovery_screen 'Software Update' 'Continuing' '' "Don't turn off the player."
done

case "$outcome" in
    installed)
        if [ -n "$recovery_restart" ]; then
            recovery_screen 'Update installed' '' 'Starting the new version.'
            recovery_off 4
        fi
        recovery_screen 'Update installed' '' 'The player turns off now.' 'Press Power to start.'
        recovery_off ;;
    rolled_back)
        if [ -n "$recovery_restart" ]; then
            recovery_screen 'Update not installed' 'The previous version' 'was restored.' '' 'Restarting.'
            recovery_off 8
        fi
        recovery_screen 'Update not installed' 'The previous version' 'was restored.' '' 'Press Power to start.'
        recovery_off ;;
    failed_unchanged)
        recovery_screen 'Update not installed' 'Nothing was changed.' '' 'The player turns off now.' 'Press Power to start.'
        recovery_off ;;
    probe)
        recovery_screen 'Recovery works' '' 'The player turns off now.' 'Press Power to start.'
        recovery_off ;;
    nothing)
        recovery_screen 'Nothing to install' '' 'The player turns off now.' 'Press Power to start.'
        recovery_off 6 ;;
    *)
        recovery_stuck 'The update stopped' ;;
esac
