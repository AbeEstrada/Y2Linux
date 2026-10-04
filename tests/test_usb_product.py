"""Behavioral product, descriptor readiness and file-ownership regressions."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tarfile
import shutil
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/platform'))
from y2_platform.common import Context
from y2_platform.usb import USBService, SCHEMA, GADGET, config, selection, media_views, release_sd


class Child:
    pid = 123
    def __init__(self): self.result = None
    def poll(self): return self.result
    def terminate(self): self.result = 0
    def kill(self): self.result = -9
    def wait(self, **kw): return self.result


class USBProduct(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ctx = Context(self.temp.name)
        self.put('/proc/sys/kernel/random/boot_id', 'boot-one')
        self.put('/sys/class/udc/musb/state', 'not attached')
        self.ctx.path('/sys/kernel/config/usb_gadget').mkdir(parents=True)
        self.ctx.path('/run/y2').mkdir(parents=True)
        self.views = [{'path':'/data/music', 'name':'Internal Storage', 'access':'rw', 'mount_id':5}]
        self.service = USBService(self.ctx, launch=Child)
        self.mock = patch('y2_platform.usb.media_views', return_value=self.views)
        self.mock.start(); self.addCleanup(self.mock.stop)
        self.ctx.runner = lambda *_a, **_k: {'ok':True, 'reason':None, 'output':''}

    def put(self, name, value):
        path = self.ctx.path(name); path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value); return path

    def ready(self):
        self.service.tick()
        for i in (1,2,3): self.put('/dev/ffs-mtp/ep%s' % i, '')
        self.put(GADGET + '/functions/ffs.mtp/ready', '1')
        self.put('/sys/class/udc/musb/state', 'configured')
        return self.service.tick()

    def test_no_udc_bind_before_all_functionfs_descriptors(self):
        state = self.service.tick()
        self.assertEqual(state['reason'], 'waiting_for_descriptors')
        self.assertFalse(self.ctx.path(GADGET+'/UDC').exists())
        self.assertEqual(self.ready()['state'], 'Ready')
        self.assertEqual(self.ctx.read(GADGET+'/UDC'), 'musb')
        self.assertEqual(self.ctx.read(GADGET+'/os_desc/use'),'1')
        self.assertTrue(self.ctx.path(GADGET+'/os_desc/c.1').is_symlink())
        self.assertEqual(list(selection('mtp')), ['ffs.mtp','ecm.usb0'])

    def test_no_block_export_or_triple_function_selection(self):
        for invalid in ('msc','mass_storage','mtp+acm+ecm','/dev/mmcblk0','Y2DATA','BOOTIMG'):
            with self.assertRaises(ValueError): selection(invalid)
        self.assertEqual(selection('developer'), ('acm.usb0','ecm.usb0'))
        for path in ('/','/data','/dev/mmcblk0','/data/reborn','/data/ssh'):
            with self.assertRaises(ValueError): config([{'path':path,'name':'Internal Storage','access':'rw'}])
        self.assertIn('storage "/data/music" "Internal Storage" "rw"', config(self.views))

    def test_disconnect_refresh_keeps_linux_ownership_and_reconnect(self):
        self.ready()
        self.put('/sys/class/udc/musb/state','not attached')
        disconnected = self.service.tick()
        self.assertEqual(disconnected['state'],'Disconnected')
        self.assertGreater(disconnected['refresh_generation'],0)
        self.assertEqual(disconnected['filesystem_owner'],'linux')
        self.assertFalse(disconnected['block_export'])
        self.put('/sys/class/udc/musb/state','configured')
        self.assertEqual(self.service.tick()['state'],'Ready')

    def test_only_durable_generation_not_activity_requests_library_refresh(self):
        self.ready()
        self.put('/run/y2/mtp-events.json',json.dumps({'pid':123,'active':True,'generation':0}))
        value=self.service.tick(); self.assertEqual(value['state'],'Copying'); self.assertEqual(value['refresh_generation'],0)
        self.put('/run/y2/mtp-events.json',json.dumps({'pid':123,'active':False,'generation':5}))
        first=self.service.tick()['refresh_generation']; self.assertGreater(first,0)
        self.assertEqual(first,self.service.tick()['refresh_generation'])

    def test_failed_daemon_and_failed_bind_have_bounded_retry(self):
        self.ready()
        for _ in range(5):
            if self.service.child: self.service.child.result=1
            self.service.tick(); self.service.tick()
        self.assertTrue(self.service.terminal)
        self.assertEqual(self.service.tick()['state'],'Failed')

    def test_bind_failure_never_reports_host_ownership(self):
        self.service.tick()
        for i in (1,2,3): self.put('/dev/ffs-mtp/ep%s' % i,'')
        self.put(GADGET+'/functions/ffs.mtp/ready','1')
        original=self.service.write
        def failed(relative,value):
            if relative=='UDC' and value: raise OSError('bind_failed')
            original(relative,value)
        with patch.object(self.service,'write',side_effect=failed):
            value=self.service.tick()
        self.assertEqual(value['state'],'Failed')
        self.assertEqual(value['filesystem_owner'],'linux')
        self.assertFalse(self.service.bound)
        self.assertIsNone(self.service.child)

    def test_readiness_restart_unbinds_its_existing_gadget_before_setup(self):
        self.ready()
        restarted=USBService(self.ctx,launch=Child)
        seen=[]; original=restarted.write
        def observed(relative,value):
            if relative=='UDC': seen.append(value)
            original(relative,value)
        with patch.object(restarted,'write',side_effect=observed): restarted.tick()
        self.assertEqual(seen[0],'')
        self.assertEqual(seen[-1],'musb')
        self.assertEqual(restarted.tick()['filesystem_owner'],'linux')

    def test_media_identity_change_stops_old_responder_before_new_view(self):
        self.ready(); old=self.service.child
        self.views[0]['mount_id'] = 6
        self.mock.stop()
        self.mock = patch('y2_platform.usb.media_views', return_value=[dict(self.views[0])])
        self.mock.start()
        self.service.views = [{'path':'/data/music', 'name':'Internal Storage', 'access':'rw', 'mount_id':5}]
        self.put('/proc/self/mountinfo','new mount generation')
        self.service.tick()
        self.assertEqual(old.result,0)
        self.assertIsNot(self.service.child,old)

    def test_developer_change_waits_for_disconnect(self):
        self.ready(); self.put('/data/system/platform/usb-mode.json','{"mode":"developer"}')
        self.assertEqual(self.service.tick()['mode'],'mtp')
        self.put('/sys/class/udc/musb/state','not attached')
        self.assertEqual(self.service.tick()['mode'],'developer')

    def test_sd_eject_refuses_connected_host_and_preserves_mount(self):
        record={'schema':SCHEMA,'boot_id':'boot-one','cable':'configured','views':[{'path':'/media/sd'}]}
        self.put('/run/y2/usb-transfer.json',json.dumps(record))
        self.assertFalse(release_sd(self.ctx,42))
        self.assertFalse(self.ctx.path('/run/y2/usb-release-sd.json').exists())


class MediaViews(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.ctx=Context(self.temp.name)
        self.ctx.path('/data/music').mkdir(parents=True)
        self.ctx.path('/media/sd').mkdir(parents=True)
        device=self.ctx.path('/sys/dev/block/179:2'); device.mkdir(parents=True)
        (device/'start').write_text('2104320'); (device/'size').write_text('1638400')
        self.volumes=[{}, {'path':'/data','state':'Ready','uuid':'79324c69-6e75-4801-8000-000000000102'},
                         {'path':'/media/sd','state':'Unavailable'}]
        self.mount='/proc/self/mountinfo'; self.ctx.path('/proc/self').mkdir(parents=True)
        self.ctx.path(self.mount).write_text('5 1 179:2 / /data rw - ext4 /dev/mmcblk0p2 rw')
        mock=patch('y2_platform.usb.storage',return_value={'volumes':self.volumes})
        mock.start(); self.addCleanup(mock.stop)

    def test_missing_sd_never_exposes_empty_mountpoint(self):
        self.assertEqual([v['path'] for v in media_views(self.ctx)],['/data/music'])

    def test_dirty_or_failed_media_and_remount_failure_are_not_exposed(self):
        self.volumes[2].update(state='Failed',reason='filesystem_check_required')
        self.ctx.path(self.mount).write_text(self.ctx.path(self.mount).read_text()+'\n6 1 179:9 / /media/sd rw - exfat /dev/mmcblk1p1 rw')
        self.assertEqual(len(media_views(self.ctx)),1)
        self.ctx.path(self.mount).write_text('')
        self.assertEqual(media_views(self.ctx),[])

    def test_readonly_superblock_is_never_advertised_writable(self):
        self.volumes[1]['state']='Degraded'
        self.ctx.path(self.mount).write_text('5 1 179:2 / /data rw - ext4 /dev/mmcblk0p2 ro')
        self.assertEqual(media_views(self.ctx)[0]['access'],'ro')

    def test_wrong_internal_geometry_uuid_or_nested_mount_is_excluded(self):
        self.ctx.path('/sys/dev/block/179:2/start').write_text('0')
        self.assertEqual(media_views(self.ctx),[])
        self.ctx.path('/sys/dev/block/179:2/start').write_text('2104320')
        self.volumes[1]['uuid']='system-root'
        self.assertEqual(media_views(self.ctx),[])
        self.volumes[1]['uuid']='79324c69-6e75-4801-8000-000000000102'
        self.ctx.path(self.mount).write_text(self.ctx.path(self.mount).read_text()+'\n8 5 179:1 / /data/music rw - ext4 /dev/mmcblk0p1 rw')
        self.assertEqual(media_views(self.ctx),[])


class PhysicalHarness(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('usb_qualify',ROOT/'tools/usb/qualify.py')
        self.module=importlib.util.module_from_spec(spec); spec.loader.exec_module(self.module)

    def test_cpu_irq_context_switch_deltas_have_explicit_average_scope(self):
        value=self.module.delta({'stat':'cpu 10 0 20 100 0 0 0 0\nintr 100\nctxt 200'},
                                {'stat':'cpu 20 0 30 120 0 0 0 0\nintr 160\nctxt 280'},2)
        self.assertEqual(value['cpu_busy_percent'],50)
        self.assertEqual(value['irq_per_s'],30)
        self.assertEqual(value['context_switches_per_s'],40)

    def test_boot_or_media_swap_refuses_following_transfer_or_cleanup(self):
        from types import SimpleNamespace
        harness=self.module.Harness(SimpleNamespace(ssh_config=None,host='fixture'))
        harness.identity={'boot':'one','mounts':'5 1 179:2 / /data rw - ext4 /dev/data rw'}
        with patch.object(harness,'snapshot',return_value={'boot':'two','mounts':harness.identity['mounts']}):
            with self.assertRaisesRegex(RuntimeError,'identity_changed'): harness.guard()
        with patch.object(harness,'snapshot',return_value={'boot':'one','mounts':'6 1 179:2 / /data rw - ext4 /dev/data rw'}):
            with self.assertRaisesRegex(RuntimeError,'identity_changed'): harness.guard()

    def test_deadline_prevents_copy_and_many_files_use_one_sftp_batch(self):
        import time
        from types import SimpleNamespace
        harness=self.module.Harness(SimpleNamespace(ssh_config=None,host='fixture',protocol='sftp'))
        harness.device_dir='/data/unique-fixture'; harness.deadline=time.monotonic()-1
        with patch.object(harness,'sftp_batch') as batch:
            with self.assertRaisesRegex(RuntimeError,'deadline'): harness.copies([Path('one')],Path('/tmp'),True)
            batch.assert_not_called()
            harness.deadline=time.monotonic()+60
            harness.copies([Path('one'),Path('two')],Path('/tmp'),True)
            self.assertEqual(len(batch.call_args.args[0]),2)
            self.assertEqual(batch.call_count,1)


class USBFiles(unittest.TestCase):
    def test_actual_responder_operations_and_descriptors(self):
        archive=ROOT/'.cache/buildroot-dl/y2-mtp/y2-mtp-2241a803c27f1fff7537cb9504befeb810b880d3.tar.gz'
        if not archive.is_file(): self.skipTest('pinned responder archive not prepared')
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), '077ef6f4745d599bda7db0fff2993e21b969bbf414784c4ab3adf0f664177d2b')
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary)
            with tarfile.open(archive) as source: source.extractall(base,filter='data')
            source=next(base.glob('uMTP-Responder-*'))
            patchfile=ROOT/'buildroot/package/y2-mtp/0001-y2-safe-media-transfers.patch'
            subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(patchfile)],cwd=source,check=True,stdout=subprocess.DEVNULL)
            for name in ('h','c'): shutil.copyfile(ROOT/('tools/usb/mtp-safe.'+name),source/('inc' if name=='h' else 'src')/('mtp-safe.'+name))
            build=subprocess.run(['make','-j4'],cwd=source,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            self.assertEqual(build.returncode,0,build.stdout)
            flags=['cc','-I'+str(source/'inc')]
            main=base/'main.o'
            subprocess.run(flags+['-Dmain=umtprd_original_main','-c',str(source/'src/umtprd.c'),'-o',str(main)],check=True)
            binary=base/'protocol-test'
            objects=[str(o) for o in (source/'obj').glob('*.o') if o.name!='umtprd.o']
            subprocess.run(flags+[str(ROOT/'tests/usb_mtp_protocol.c'),str(main),*objects,'-lpthread','-lrt','-o',str(binary)],check=True)
            media=base/'media'; media.mkdir()
            subprocess.run([str(binary),str(media)],check=True,timeout=5)
            self.assertFalse(list(media.glob('.y2-mtp-*')))

    def test_real_atomic_files_and_fault_injection(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary); media=base/'media'; media.mkdir()
            binary=base/'fs-test'
            subprocess.run(['cc','-Wall','-Wextra','-Werror','-I'+str(ROOT/'tools/usb'),str(ROOT/'tests/usb_mtp_fs.c'),'-o',str(binary)],check=True)
            subprocess.run([str(binary),str(media)],check=True)
            expected=hashlib.sha256(b'abcdef').hexdigest()
            for file in media.glob('*.mp3'):
                if file.name!='partial.mp3': self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(),expected)
            self.assertFalse(list(media.glob('.y2-mtp-*')))


if __name__ == '__main__': unittest.main()
