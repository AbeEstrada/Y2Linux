#!/usr/bin/env python3
"""Bounded synthetic brief Power gesture through the real evdev path."""
import json, struct, sys, time
from pathlib import Path
sys.path.insert(0, '/usr/lib/y2-platform')
from y2_platform.common import Context
from y2_platform.suspend_record import application_rpc
ctx=Context()
if len(sys.argv)!=2 or sys.argv[1] not in ('on','off'): raise SystemExit('on|off required')
want_off=sys.argv[1]=='off'
before=application_rpc(ctx,'status')
if before.get('playback',{}).get('state') not in ('paused','stopped') or before.get('library',{}).get('scanning'): raise SystemExit('paused/no scan prerequisite failed')
if before.get('screen_off') is not want_off:
 paths=[p for p in Path('/sys/class/input').glob('event*') if (p/'device/name').read_text().strip()=='mtk-pmic-keys']
 if len(paths)!=1: raise SystemExit('power evdev identity ambiguous')
 with (Path('/dev/input')/paths[0].name).open('wb',buffering=0) as f:
  for value in (1,0):
   f.write(struct.pack('llHHi',0,0,1,116,value))
   f.write(struct.pack('llHHi',0,0,0,0,0))
   if value: time.sleep(.025)
 time.sleep(.5)
after=application_rpc(ctx,'status')
print(json.dumps({'before_screen_off':before.get('screen_off'),'after_screen_off':after.get('screen_off'),'playback':after.get('playback',{}).get('state'),'origin':'synthetic balanced brief Power gesture; not mechanical input latency proof'}))
if after.get('screen_off') is not want_off: raise SystemExit('screen transition failed')
