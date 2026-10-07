"""Exercise Python's real buffering against a sysfs-style store failure."""
import errno
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/platform'))
from y2_platform.common import Context
from y2_platform.product_sleep import kernel_sleep


class Store(io.RawIOBase):
    """The first store can refuse; a repeated store would enter suspend."""
    def __init__(self, result):
        super().__init__()
        self.result = result
        self.calls = []

    def writable(self):
        return True

    def write(self, data):
        self.calls.append(bytes(data))
        if len(self.calls) == 1:
            if isinstance(self.result, BaseException):
                raise self.result
            return self.result
        return len(data)


class PMControlWrite(unittest.TestCase):
    def invoke(self, result):
        raw = Store(result)
        self.addCleanup(raw.close)

        def opened(path, mode='r', buffering=-1, encoding=None, errors=None, newline=None):
            self.assertEqual(str(path), '/sys/power/state')
            if buffering == 0:
                self.assertEqual(mode, 'wb')
                return raw
            # Real BufferedWriter/TextIOWrapper reproduce the installed bug.
            return io.TextIOWrapper(io.BufferedWriter(raw), encoding=encoding,
                                    errors=errors, newline=newline)

        with patch.object(Path, 'open', opened):
            try:
                kernel_sleep(Context())
            finally:
                self.assertEqual(raw.calls, [b'mem\n'], 'PM command was replayed')
                self.assertTrue(raw.closed)

    def test_busy_and_failed_store_never_retries_during_close(self):
        for code in (errno.EBUSY, errno.EAGAIN, errno.EIO):
            with self.subTest(errno=code):
                with self.assertRaises(OSError) as caught:
                    self.invoke(OSError(code, 'fixture store refused'))
                self.assertEqual(caught.exception.errno, code)

    def test_short_store_fails_without_writing_remainder(self):
        for size in (0, 2, None):
            with self.subTest(size=size):
                with self.assertRaises(OSError) as caught:
                    self.invoke(size)
                self.assertEqual(caught.exception.errno, errno.EIO)

    def test_successful_store_is_issued_once(self):
        self.invoke(4)


if __name__ == '__main__':
    unittest.main()
