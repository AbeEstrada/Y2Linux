import re
import unittest
from pathlib import Path

from test_power import run_c

ROOT = Path(__file__).resolve().parents[1]
# The header is pasted into each test; not every test calls every helper.
UNUSED_OK = '#pragma clang diagnostic ignored "-Wunused-function"\n'
PATCH = ROOT / 'buildroot/patches/bluez-alsa/0002-y2-aac-adaptive-bitrate.patch'


def header():
    """y2-aac-abr.h exactly as the BlueALSA patch adds it."""
    text = PATCH.read_text()
    body = text.split('+++ b/src/y2-aac-abr.h\n', 1)[1]
    lines = []
    for line in body.splitlines():
        if line.startswith('@@'):
            continue
        if not line.startswith('+'):
            break
        lines.append(line[1:])
    return '\n'.join(lines) + '\n'


class AacAdaptiveBitrate(unittest.TestCase):
    def test_steps_down_under_congestion_and_recovers_only_when_quiet(self):
        run_c(UNUSED_OK + header() + r'''
#include <assert.h>
int main(void) {
 struct y2_aac_abr a;
 y2_aac_abr_init(&a, 256000, true);
 assert(a.enabled && a.rates[0] == 256000 && a.rates[1] == 192000 && a.rates[2] == 160000 && a.rates[3] == 128000);
 /* An idle link never changes anything. */
 for (int i = 0; i < 5000; i++) assert(y2_aac_abr_update(&a, i % 2, false) == 0);
 assert(a.level == 0);
 /* Two queued packets: step down at once, then hold ~0.2 s between steps. */
 assert(y2_aac_abr_update(&a, 2, false) == 192000);
 for (int i = 0; i < Y2_AAC_ABR_HOLD - 1; i++) assert(y2_aac_abr_update(&a, 3, false) == 0);
 assert(y2_aac_abr_update(&a, 0, true) == 160000);   /* a blocked write counts */
 for (int i = 0; i < Y2_AAC_ABR_HOLD - 1; i++) assert(y2_aac_abr_update(&a, 2, false) == 0);
 assert(y2_aac_abr_update(&a, 2, false) == 128000);
 for (int i = 0; i < 100; i++) assert(y2_aac_abr_update(&a, 9, true) == 0);  /* floor */
 assert(a.level == 3);
 /* One queued packet is not calm: no recovery. */
 for (int i = 0; i < 2 * Y2_AAC_ABR_CALM; i++) assert(y2_aac_abr_update(&a, 1, false) == 0);
 /* A quiet stretch interrupted by congestion starts over. */
 for (int i = 0; i < Y2_AAC_ABR_CALM - 1; i++) assert(y2_aac_abr_update(&a, 0, false) == 0);
 assert(y2_aac_abr_update(&a, 2, false) == 0 && a.level == 3);
 for (int i = 0; i < Y2_AAC_ABR_CALM - 1; i++) assert(y2_aac_abr_update(&a, 0, false) == 0);
 assert(y2_aac_abr_update(&a, 0, false) == 160000);
 for (int i = 0; i < Y2_AAC_ABR_CALM - 1; i++) assert(y2_aac_abr_update(&a, 0, false) == 0);
 assert(y2_aac_abr_update(&a, 0, false) == 192000);
 for (int i = 0; i < Y2_AAC_ABR_CALM - 1; i++) assert(y2_aac_abr_update(&a, 0, false) == 0);
 assert(y2_aac_abr_update(&a, 0, false) == 256000 && a.level == 0);
 /* Off, or nothing to adapt at or below the floor: never a change. */
 y2_aac_abr_init(&a, 256000, false);
 assert(!a.enabled && y2_aac_abr_update(&a, 9, true) == 0);
 y2_aac_abr_init(&a, 128000, true);
 assert(!a.enabled);
 y2_aac_abr_init(&a, 96000, true);
 assert(!a.enabled && a.rates[3] == 96000);
 y2_aac_abr_init(&a, 220000, true);
 assert(a.enabled && a.rates[1] == 165000 && a.rates[3] == 128000);
}
''')

    def test_frames_fit_one_packet(self):
        run_c(UNUSED_OK + header() + r'''
#include <assert.h>
int main(void) {
 /* The common 672-byte L2CAP MTU keeps BlueALSA's tested 220 kbit/s. */
 assert(y2_aac_mtu_bitrate(672, 44100) > 220000 && y2_aac_mtu_bitrate(672, 44100) < 225000);
 /* A larger MTU allows the AirPods' advertised 256 kbit/s. */
 assert(y2_aac_mtu_bitrate(895, 44100) > 256000);
 /* A frame at the capped rate fits: rate * 1024 / fs / 8 + overhead <= MTU. */
 for (unsigned mtu = 100; mtu < 2000; mtu += 37)
  for (unsigned fs = 44100; fs <= 48000; fs += 3900) {
   unsigned r = y2_aac_mtu_bitrate(mtu, fs);
   assert((unsigned long long)r * 1024 / fs / 8 + Y2_AAC_FRAME_OVERHEAD <= mtu);
  }
 assert(y2_aac_mtu_bitrate(20, 44100) == 0 && y2_aac_mtu_bitrate(672, 0) == 0);
}
''')

    def test_encoder_uses_the_decisions_once_per_frame(self):
        patch = PATCH.read_text()
        aac = patch.split('+++ b/src/a2dp-aac.c\n', 1)[1].split('\n--- ', 1)[0]
        added = '\n'.join(line[1:] for line in aac.splitlines() if line.startswith('+'))
        self.assertIn('y2_aac_abr_init(&abr, bitrate, config.aac_abr && !configuration->vbr)', added)
        self.assertEqual(added.count('y2_aac_abr_update('), 1)
        self.assertIn('AACENC_PEAK_BITRATE, next', added)
        self.assertRegex(added, r'bitrate > mtu_bitrate\)\s*bitrate = mtu_bitrate')


if __name__ == '__main__':
    unittest.main()
