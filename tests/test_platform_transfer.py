import hashlib
import json
import os
import signal
import socket
from pathlib import Path
import sys
import tempfile
import tarfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools/platform'))
from y2_platform.common import Context
from y2_platform.ssh import AddressEvents, entropy_ready, prerequisites, serve, usb_address
from y2_platform.transfer import begin, commit, discard
from tools.production.validate import validate_ssh_programs


class Transfer(unittest.TestCase):
    def test_package_accepts_only_existing_dropbear_client_alias(self):
        alias = tarfile.TarInfo('usr/bin/ssh')
        alias.type = tarfile.SYMTYPE
        alias.linkname = '../sbin/dropbear'
        validate_ssh_programs({'usr/bin/ssh': alias})
        validate_ssh_programs({})
        for name in ('usr/sbin/sshd', 'usr/bin/sftp', 'usr/bin/ssh'):
            with self.assertRaises(ValueError):
                validate_ssh_programs({name: tarfile.TarInfo(name)})
        alias.linkname = '../bin/unreviewed-client'
        with self.assertRaises(ValueError):
            validate_ssh_programs({'usr/bin/ssh': alias})

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.ctx = Context(self.tmp.name)
        self.volume = {'path':'/data', 'state':'Ready', 'space_state':'Normal',
                       'generation':'boot:1:179:7', 'available_bytes':1024**3}
        p = patch('y2_platform.transfer.storage', side_effect=lambda _: {'volumes':[self.volume]})
        p.start(); self.addCleanup(p.stop)
        self.payload = b'owner music test\0' * 4000

    def begin(self, name='Album/track.flac'):
        stage = begin(self.ctx, name, len(self.payload), hashlib.sha256(self.payload).hexdigest())
        return stage, self.ctx.path(stage['upload_path'])

    def test_interrupted_upload_bad_hash_and_reserve_never_publish(self):
        stage,path=self.begin(); path.write_bytes(self.payload[:100])
        with self.assertRaisesRegex(ValueError,'incomplete'): commit(self.ctx,stage['id'])
        self.assertFalse(self.ctx.path('/data/music').exists())
        path.write_bytes(b'x'*len(self.payload))
        with self.assertRaisesRegex(ValueError,'hash'): commit(self.ctx,stage['id'])
        self.assertFalse(self.ctx.path('/data/music').exists())
        discard(self.ctx,stage['id'])
        self.volume['available_bytes']=97*1024**2
        with self.assertRaisesRegex(ValueError,'insufficient_space'):
            begin(self.ctx,'large.flac',1024**2,'a'*64)

    def test_verified_copy_does_not_change_with_old_upload_fd_and_never_overwrites(self):
        stage,path=self.begin(); path.write_bytes(self.payload)
        with path.open('r+b') as old:
            value=commit(self.ctx,stage['id'])
            self.assertEqual(value['state'],'Committed')
            old.seek(0); old.write(b'changed'); old.flush()
        target=self.ctx.path('/data/music/Album/track.flac')
        self.assertEqual(target.read_bytes(),self.payload)
        self.assertEqual(commit(self.ctx,stage['id'])['state'],'Committed')
        discard(self.ctx,stage['id'])
        stage,path=self.begin(); path.write_bytes(self.payload)
        with self.assertRaises(FileExistsError): commit(self.ctx,stage['id'])
        self.assertEqual(target.read_bytes(),self.payload)

    def use_internal_media(self, cross_device):
        """Y2Media mounted and Ready: uploads stage on Y2DATA and publish on the media volume."""
        self.media = {'path':'/media/internal', 'state':'Ready', 'space_state':'Normal', 'generation':'boot:9:179:8'}
        self.ctx.path('/media/internal').mkdir(parents=True)
        for patcher in (patch('y2_platform.transfer.storage', side_effect=lambda _: {'volumes':[self.volume, self.media]}),
                        patch('y2_platform.transfer.internal_media.ready', return_value=True),
                        patch('y2_platform.transfer.same_device', return_value=not cross_device)):
            patcher.start(); self.addCleanup(patcher.stop)

    def test_uploads_publish_on_y2media_by_copy_across_filesystems_and_never_replace(self):
        self.use_internal_media(cross_device=True)
        stage,path=self.begin(); path.write_bytes(self.payload)
        self.assertEqual(commit(self.ctx,stage['id'])['state'],'Committed')
        target=self.ctx.path('/media/internal/music/Album/track.flac')
        self.assertEqual(target.read_bytes(),self.payload)
        self.assertFalse(self.ctx.path('/data/music').exists())
        self.assertEqual(sorted(p.name for p in target.parent.iterdir()),['track.flac'])      # temporary name gone
        discard(self.ctx,stage['id'])
        stage,path=self.begin(); path.write_bytes(self.payload)
        with self.assertRaises(FileExistsError): commit(self.ctx,stage['id'])
        self.assertEqual(target.read_bytes(),self.payload)
        self.assertEqual(sorted(p.name for p in target.parent.iterdir()),['track.flac'])

    def test_same_filesystem_media_still_uses_an_atomic_link(self):
        self.use_internal_media(cross_device=False)
        stage,path=self.begin(); path.write_bytes(self.payload)
        with patch('y2_platform.transfer.publish_copy') as copy:
            self.assertEqual(commit(self.ctx,stage['id'])['state'],'Committed')
        copy.assert_not_called()
        self.assertEqual(self.ctx.path('/media/internal/music/Album/track.flac').read_bytes(),self.payload)

    def test_media_replacement_and_low_space_fail_closed_before_publishing(self):
        self.use_internal_media(cross_device=True)
        stage,path=self.begin(); path.write_bytes(self.payload)
        real=__import__('y2_platform.transfer',fromlist=['x']).media_volume
        calls=[]
        def changing(ctx):
            calls.append(1)
            value=dict(real(ctx))
            if len(calls)>1: value['generation']='boot:11:179:8'      # replaced between open and publish
            return value
        with patch('y2_platform.transfer.media_volume',side_effect=changing):
            with self.assertRaisesRegex(ValueError,'media_generation_changed'): commit(self.ctx,stage['id'])
        self.assertFalse(self.ctx.path('/media/internal/music/Album/track.flac').exists())
        discard(self.ctx,stage['id'])
        stage,path=self.begin(); path.write_bytes(self.payload)
        with patch('y2_platform.transfer.RESERVE',1<<62):                       # the media volume cannot keep its reserve
            with self.assertRaisesRegex(ValueError,'transfer_storage_reserve'): commit(self.ctx,stage['id'])
        self.assertFalse(self.ctx.path('/media/internal/music/Album/track.flac').exists())
        self.assertEqual([p.name for p in self.ctx.path('/media/internal/music/Album').iterdir()],[])

    def test_mount_replacement_and_symlink_escape_fail_closed(self):
        stage,path=self.begin(); path.write_bytes(self.payload)
        self.volume['generation']='boot:2:179:7'
        with self.assertRaisesRegex(ValueError,'generation_changed'): commit(self.ctx,stage['id'])
        discard(self.ctx,stage['id'])
        outside=Path(self.tmp.name)/'outside';outside.mkdir()
        self.ctx.path('/data/music').symlink_to(outside)
        stage,path=self.begin();path.write_bytes(self.payload)
        with self.assertRaises(OSError):commit(self.ctx,stage['id'])
        self.assertEqual(list(outside.iterdir()),[])
        for name in ('../state/db','/root/key','ok/../bad','ok\nput secret'):
            with self.assertRaises(ValueError):self.begin(name)

    def test_ssh_waits_for_crng_and_usb_not_only_a_running_daemon(self):
        def not_ready(*_):raise BlockingIOError()
        self.assertFalse(entropy_ready(not_ready))
        self.assertTrue(entropy_ready(lambda *_:b'x'))
        key=self.ctx.path('/root/.ssh/authorized_keys');key.parent.mkdir(parents=True);key.write_text('fixture-public-key')
        self.assertEqual(prerequisites(self.ctx,False)[1],'kernel_crng_not_ready')
        self.ctx.runner=lambda *a,**k:{'ok':True,'output':json.dumps([{'ifname':'wlan0','addr_info':[{'local':'10.42.0.1','prefixlen':24}]}])}
        self.assertEqual(prerequisites(self.ctx,True)[1],'usb_address_not_ready')
        self.ctx.path('/data').mkdir(exist_ok=True)
        self.ctx.path('/data/.y2data-schema').write_text('1')
        self.ctx.runner=lambda *a,**k:{'ok':True,'output':json.dumps([{'ifname':'usb0','addr_info':[{'local':'10.42.0.1','prefixlen':24}]}])}
        self.assertEqual(prerequisites(self.ctx,True)[0],'Ready')

    def test_ssh_passive_address_events_and_signal_fd_wake(self):
        events = AddressEvents.__new__(AddressEvents)
        left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
        left.setblocking(False)
        events.sock = left
        rd, wr = os.pipe2(os.O_NONBLOCK)
        try:
            right.send(b'address-change')
            self.assertTrue(events.wait(1, rd))
            os.write(wr, b'signal')
            self.assertFalse(events.wait(1, rd))
            with self.assertRaises(BlockingIOError):
                os.read(rd, 1)
        finally:
            events.close()
            right.close()
            os.close(rd)
            os.close(wr)

    def test_ssh_ready_heartbeat_does_not_fork_ip_each_second(self):
        for name, value in (('/root/.ssh/authorized_keys', 'owner'), ('/data/.y2data-schema', '1'),
                            ('/proc/net/tcp', 'header\n0: 01002A0A:0016 00000000:0000 0A\n')):
            path = self.ctx.path(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value)
        self.ctx.runner = lambda *a, **k: {'output': '[{"ifname":"usb0","addr_info":[{"local":"10.42.0.1","prefixlen":24}]}]'}
        from y2_platform import ssh
        clock, waits = [0], []
        class Events:
            sock = True
            def wait(self, timeout, fd):
                waits.append(timeout)
                clock[0] += timeout
                if len(waits) == 5:
                    signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
                return False
            def close(self):
                pass
        class Child:
            pid = 123456
            def poll(self):
                return 0 if len(waits) == 5 else None
        with patch.object(ssh, 'AddressEvents', Events), patch.object(ssh, 'entropy_ready', return_value=True), \
                patch.object(ssh.subprocess, 'Popen', return_value=Child()), \
                patch.object(ssh.time, 'monotonic', side_effect=lambda: clock[0]), \
                patch.object(ssh, 'usb_address', wraps=usb_address) as address:
            serve(self.ctx)
            self.assertEqual(address.call_count, 1)
            self.assertEqual(waits, [1, 5, 5, 5, 5])


if __name__=='__main__': unittest.main()
