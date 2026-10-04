// SPDX-License-Identifier: GPL-2.0-only
/* Temporary MT6582 AFE register/DMA laboratory (whitelisted, restorable).
 *
 * Purpose: find out, on the physical Y2, which AFE memory-interface and
 * interconnect features exist in this exact silicon. Development instrument,
 * not product code, never part of a candidate.
 *
 * Safety model (there is deliberately NO generic MMIO write primitive):
 *   - writes only to registers in wl[] and only to bits in that entry's mask;
 *   - every register's pre-experiment value is snapshotted on first touch and
 *     restore_all puts all of them back (reverse order);
 *   - writes are refused unless: this module holds the only runtime-PM
 *     reference of the AFE (no PCM stream open), DL1 is off and the external
 *     I2S output (AFE_I2S_CON3.EN) is off;
 *   - after each write DAC_CON0 and the IRQ status are checked; an unexpected
 *     change restores the register and reports ABORT;
 *   - every write/probe appends one JSON line to the "log" file.
 * Register access is limited to the AFE window (0x11220000, 0x000-0x7fc).
 * CONFIG_MODULE_UNLOAD=n on the installed kernel: stay resident until reboot.
 */
#include <linux/debugfs.h>
#include <linux/dma-mapping.h>
#include <linux/io.h>
#include <linux/ktime.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/pm_runtime.h>
#include <linux/slab.h>
#include <linux/uaccess.h>
#include <linux/utsname.h>
#include <linux/delay.h>
#include <linux/vmalloc.h>

#define AFE_WINDOW	0x800
#define SLOTS		4
#define OUT_MAX		(64 * 1024)
#define LOG_MAX		(256 * 1024)
#define MAX_DMA		(512 * 1024)
#define GPIO_DIN_PHYS	0x10005500 /* GPIO DIN block, read-only; group 2 (GPIO32-47) at +0x20 */
#define SLA_MAX		(128 * 1024)

#define DAC_CON0	0x010
#define I2S_CON3	0x04c
#define IRQ_STATUS	0x3a4
#define TOP_CON3	0x00c
#define DL1_ON		BIT(1)
#define DAC_STATE_MASK	0x000000ff /* enables; *_RETM monitor bits excluded */

struct wl_entry {
	u16 off;
	const char *name;
	u32 mask;	/* the only bits this entry may ever modify */
};

static const struct wl_entry wl[] = {
	/* documented control */
	{ 0x010, "AFE_DAC_CON0",	0x00000046 }, /* DL1/DL2/AWB enable */
	{ 0x014, "AFE_DAC_CON1",	0x0360f0ff }, /* rates, mono, per-memif */
	{ 0x020, "AFE_CONN0",		0xffffffff },
	{ 0x024, "AFE_CONN1",		0xffffffff },
	{ 0x028, "AFE_CONN2",		0xffffffff },
	{ 0x02c, "AFE_CONN3",		0xffffffff },
	{ 0x030, "AFE_CONN4",		0xffffffff },
	{ 0x04c, "AFE_I2S_CON3",	0x80000f2a }, /* EN (bit0) excluded */
	{ 0x040, "AFE_DL1_BASE",	0xfffffff8 },
	{ 0x048, "AFE_DL1_END",		0xfffffff8 },
	{ 0x050, "AFE_DL2_BASE",	0xfffffff8 },
	{ 0x058, "AFE_DL2_END",		0xfffffff8 },
	{ 0x070, "AFE_AWB_BASE",	0xfffffff8 },
	{ 0x078, "AFE_AWB_END",		0xfffffff8 },
	{ 0x3d8, "AFE_MEMIF_PBUF_SIZE",	0x00ff00ff },
	{ 0x410, "AFE_GAIN1_CON0",	0x0000ffff },
	{ 0x414, "AFE_GAIN1_CON1",	0x000fffff },
	{ 0x418, "AFE_GAIN1_CON2",	0x000fffff },
	{ 0x41c, "AFE_GAIN1_CON3",	0x000fffff },
	{ 0x420, "AFE_GAIN1_CONN",	0x03ffffff },
	{ 0x428, "AFE_GAIN2_CON0",	0x0000ffff },
	{ 0x42c, "AFE_GAIN2_CON1",	0x000fffff },
	{ 0x430, "AFE_GAIN2_CON2",	0x000fffff },
	{ 0x434, "AFE_GAIN2_CON3",	0x000fffff },
	{ 0x438, "AFE_GAIN2_CONN",	0xffffffff },
	{ 0x440, "AFE_GAIN2_CONN2",	0x0000007f },
	/* candidates defined only by later/related MediaTek sources (hypotheses) */
	{ 0x05c, "CAND_AFE_CONN5",	0x0000ffff },
	{ 0x06c, "CAND_AFE_CONN_24BIT",	0x0007ffff },
	{ 0x0bc, "CAND_AFE_CONN6",	0x0000ffff },
	{ 0x0cc, "CAND_AFE_MEMIF_MSB",	0x00ffffff },
	{ 0x340, "CAND_AFE_DL1_D2_BASE", 0x0000fff8 },
	{ 0x348, "CAND_AFE_DL1_D2_END",	0x0000fff8 },
	{ 0x350, "CAND_AFE_VUL_D2_BASE", 0x0000fff8 },
	{ 0x358, "CAND_AFE_VUL_D2_END",	0x0000fff8 },
	{ 0x370, "CAND_AFE_HDMI_OUT_CON0", 0xfffffffe }, /* enable bit excluded */
	{ 0x374, "CAND_AFE_HDMI_BASE",	0x0000fff8 },
	{ 0x37c, "CAND_AFE_HDMI_END",	0x0000fff8 },
	{ 0x390, "CAND_AFE_HDMI_CONN0",	0x0000ffff },
	{ 0x3d0, "AFE_MEMIF_MINLEN",	0x77777777 },
	{ 0x3d4, "AFE_MEMIF_MAXLEN",	0x77777777 },
};

static struct device *afe;
static void __iomem *base;
static struct dentry *dir;
static DEFINE_MUTEX(lock);
static bool held;
static void __iomem *gpio_din;
static u16 *sla_buf;
static unsigned int sla_n;
static u64 sla_ns;
static char *out, *logbuf;
static size_t out_len, log_len;

static struct {
	void *area;
	dma_addr_t addr;
	size_t bytes;
} slot[SLOTS];

/* first-touch snapshot, in touch order for reverse restore */
static struct { u16 off; u32 orig; } touched[ARRAY_SIZE(wl)];
static unsigned int ntouched;

static __printf(1, 2) void emit(const char *fmt, ...)
{
	va_list ap;

	if (out_len >= OUT_MAX - 1)
		return;
	va_start(ap, fmt);
	out_len += vscnprintf(out + out_len, OUT_MAX - out_len, fmt, ap);
	va_end(ap);
}

static __printf(1, 2) void jlog(const char *fmt, ...)
{
	va_list ap;

	if (log_len >= LOG_MAX - 1)
		return;
	va_start(ap, fmt);
	log_len += vscnprintf(logbuf + log_len, LOG_MAX - log_len, fmt, ap);
	va_end(ap);
}

static u32 rd(unsigned int off)
{
	return readl(base + off);
}

static const struct wl_entry *find_wl(unsigned long off)
{
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(wl); i++)
		if (wl[i].off == off)
			return &wl[i];
	return NULL;
}

static bool read_ok(unsigned long off)
{
	return off < AFE_WINDOW && !(off & 3);
}

static int need_hold(void)
{
	if (!held) {
		emit("error: need 'hold 1' first (AFE clocks must be on)\n");
		return -EAGAIN;
	}
	return 0;
}

/* Preconditions for any write. Returns 0 if safe. */
static int preconditions(void)
{
	int usage = atomic_read(&afe->power.usage_count);

	if (need_hold())
		return -EAGAIN;
	if (usage != 1) {
		emit("error: refused, AFE has %d runtime-PM references (PCM open?)\n", usage);
		return -EBUSY;
	}
	if (rd(DAC_CON0) & DL1_ON) {
		emit("error: refused, DL1 enabled\n");
		return -EBUSY;
	}
	if (rd(I2S_CON3) & 1) {
		emit("error: refused, external I2S output enabled\n");
		return -EBUSY;
	}
	return 0;
}

static void snap(unsigned int off)
{
	unsigned int i;

	for (i = 0; i < ntouched; i++)
		if (touched[i].off == off)
			return;
	touched[ntouched].off = off;
	touched[ntouched].orig = rd(off);
	ntouched++;
}

struct state { u32 dac0, i2s3, irq, top3; int usage; };

static void get_state(struct state *s)
{
	s->dac0 = rd(DAC_CON0);
	s->i2s3 = rd(I2S_CON3);
	s->irq = rd(IRQ_STATUS);
	s->top3 = rd(TOP_CON3);
	s->usage = atomic_read(&afe->power.usage_count);
}

/* Write masked bits, verify no unexpected side effect; returns readback. */
static int do_write(const struct wl_entry *e, u32 req, const char *kind, u32 *rb_out,
		    bool restore_now, u32 *restored_out, u32 *rrb_out)
{
	struct state a, b;
	u32 orig, val, rb = 0, rrb = 0, restored = 0;
	bool abort = false;
	u64 ts = ktime_get_real_ns();

	snap(e->off);
	orig = rd(e->off);
	val = (orig & ~e->mask) | (req & e->mask);
	get_state(&a);
	writel(val, base + e->off);
	rb = rd(e->off);
	get_state(&b);
	/* side-effect check: enables must not change except in DAC_CON0 itself,
	 * IRQ status must not appear, decode flags must not change. */
	if (e->off != DAC_CON0 && ((a.dac0 ^ b.dac0) & DAC_STATE_MASK))
		abort = true;
	if (e->off == DAC_CON0 && ((a.dac0 ^ b.dac0) & DAC_STATE_MASK & ~e->mask))
		abort = true;
	if (b.irq != a.irq || b.top3 != a.top3)
		abort = true;
	if (abort || restore_now) {
		writel(orig, base + e->off);
		restored = rd(e->off);
		rrb = restored;
		if (abort)
			emit("ABORT: unexpected state change at %s; restored\n", e->name);
	}
	if (rb_out)
		*rb_out = rb;
	if (restored_out)
		*restored_out = restored;
	if (rrb_out)
		*rrb_out = rrb;
	jlog("{\"ts_ns\":%llu,\"kernel\":\"%s\",\"kind\":\"%s\",\"reg\":\"0x%03x\","
	     "\"name\":\"%s\",\"mask\":\"0x%08x\",\"orig\":\"0x%08x\",\"req\":\"0x%08x\","
	     "\"write\":\"0x%08x\",\"readback\":\"0x%08x\",\"restored\":%s,"
	     "\"restore_readback\":\"0x%08x\",\"pm_usage\":%d,\"dac_con0\":\"0x%08x\","
	     "\"i2s_con3\":\"0x%08x\",\"irq_status\":\"0x%08x\",\"top_con3\":\"0x%08x\","
	     "\"irq_delta\":%u,\"abort\":%s}\n",
	     ts, utsname()->release, kind, e->off, e->name, e->mask, orig, req, val, rb,
	     (abort || restore_now) ? "true" : "false", rrb, b.usage, b.dac0, b.i2s3,
	     b.irq, b.top3, b.irq != a.irq, abort ? "true" : "false");
	return abort ? -EIO : 0;
}

static void restore_all(void)
{
	int i;

	for (i = ntouched - 1; i >= 0; i--) {
		const struct wl_entry *e = find_wl(touched[i].off);
		u32 now = rd(touched[i].off), rb;

		writel(touched[i].orig, base + touched[i].off);
		rb = rd(touched[i].off);
		jlog("{\"ts_ns\":%llu,\"kernel\":\"%s\",\"kind\":\"restore_all\",\"reg\":\"0x%03x\","
		     "\"name\":\"%s\",\"before\":\"0x%08x\",\"restored\":\"0x%08x\","
		     "\"restore_readback\":\"0x%08x\",\"ok\":%s}\n",
		     ktime_get_real_ns(), utsname()->release, touched[i].off,
		     e ? e->name : "?", now, touched[i].orig, rb,
		     rb == touched[i].orig ? "true" : "false");
		emit("%03x: %08x -> %08x readback %08x%s\n", touched[i].off, now,
		     touched[i].orig, rb, rb == touched[i].orig ? "" : " MISMATCH");
	}
	ntouched = 0;
}

static void do_cmd(char *line)
{
	char *tok = strsep(&line, " \t\n");
	char *s1, *s2;
	unsigned long a, b;
	unsigned int n, i;
	const struct wl_entry *e;

	if (!tok || !*tok)
		return;
	s1 = strsep(&line, " \n");
	s2 = strsep(&line, " \n");

	if (!strcmp(tok, "hold")) {
		int ret;

		if (!s1 || kstrtoul(s1, 0, &a))
			goto usage;
		if (a && !held) {
			ret = pm_runtime_resume_and_get(afe);
			if (ret < 0) {
				emit("error: resume %d\n", ret);
				return;
			}
			held = true;
		} else if (!a && held) {
			if (ntouched)
				restore_all();
			pm_runtime_put(afe);
			held = false;
		}
		emit("hold=%d usage=%d\n", held, atomic_read(&afe->power.usage_count));
	} else if (!strcmp(tok, "r")) {
		if (!s1 || kstrtoul(s1, 0, &a) || !read_ok(a))
			goto usage;
		n = 1;
		if (s2 && !kstrtoul(s2, 0, &b) && b && b < 256)
			n = b;
		if (need_hold())
			return;
		for (i = 0; i < n && read_ok(a + 4 * i); i++)
			emit("%04lx=%08x\n", a + 4 * i, rd(a + 4 * i));
	} else if (!strcmp(tok, "dump")) {
		if (!s1 || !s2 || kstrtoul(s1, 0, &a) || kstrtoul(s2, 0, &b) ||
		    !read_ok(a) || !read_ok(b) || b < a)
			goto usage;
		if (need_hold())
			return;
		for (; a <= b; a += 4)
			emit("%04lx=%08x\n", a, rd(a));
	} else if (!strcmp(tok, "wl")) {
		for (i = 0; i < ARRAY_SIZE(wl); i++)
			emit("%03x %s mask=%08x\n", wl[i].off, wl[i].name, wl[i].mask);
	} else if (!strcmp(tok, "state")) {
		struct state s;

		if (need_hold())
			return;
		get_state(&s);
		emit("dac_con0=%08x i2s_con3=%08x irq=%08x top_con3=%08x usage=%d touched=%u\n",
		     s.dac0, s.i2s3, s.irq, s.top3, s.usage, ntouched);
	} else if (!strcmp(tok, "probe_bits")) {
		/* Single-bit toggle of each mask bit, restoring after every bit. */
		u32 toggled = 0, orig, rb, bit;

		if (!s1 || kstrtoul(s1, 0, &a))
			goto usage;
		e = find_wl(a);
		if (!e) {
			emit("error: 0x%lx not whitelisted\n", a);
			return;
		}
		if (preconditions())
			return;
		snap(e->off);
		orig = rd(e->off);
		for (bit = 1; bit; bit <<= 1) {
			u32 restored, rrb;
			int ret;

			if (!(e->mask & bit))
				continue;
			ret = do_write(e, orig ^ bit, "probe_bit", &rb, true, &restored, &rrb);
			if (ret || restored != orig) {
				emit("ABORT at bit 0x%08x (ret=%d restored=%08x)\n", bit, ret, restored);
				break;
			}
			if ((rb ^ orig) & bit)
				toggled |= bit;
		}
		emit("%03x %s orig=%08x mask=%08x toggled=%08x fixed=%08x now=%08x\n", e->off,
		     e->name, orig, e->mask, toggled, e->mask & ~toggled, rd(e->off));
	} else if (!strcmp(tok, "probe")) {
		u32 rb, restored, rrb;

		if (!s1 || !s2 || kstrtoul(s1, 0, &a) || kstrtoul(s2, 0, &b))
			goto usage;
		e = find_wl(a);
		if (!e) {
			emit("error: 0x%lx not whitelisted\n", a);
			return;
		}
		if (preconditions())
			return;
		do_write(e, b, "probe", &rb, true, &restored, &rrb);
		emit("%03x %s req=%08lx readback=%08x restored=%08x\n", e->off, e->name, b, rb,
		     rrb);
	} else if (!strcmp(tok, "w")) {
		u32 rb;
		u32 cur;

		if (!s1 || !s2 || kstrtoul(s1, 0, &a) || kstrtoul(s2, 0, &b))
			goto usage;
		e = find_wl(a);
		if (!e) {
			emit("error: 0x%lx not whitelisted\n", a);
			return;
		}
		if (preconditions())
			return;
		cur = rd(e->off);
		if ((cur ^ b) & ~e->mask) {
			emit("error: value touches bits outside mask %08x (cur %08x)\n", e->mask, cur);
			return;
		}
		do_write(e, b, "exp_write", &rb, false, NULL, NULL);
		emit("%03x %s <= %08lx readback %08x\n", e->off, e->name, b, rb);
	} else if (!strcmp(tok, "sla")) {
		/* Read-only pad sampler: poll GPIO32-47 DIN (I2S pads are 43/44/46). */
		unsigned long flags, k;
		u64 t0;

		if (!s1 || kstrtoul(s1, 0, &a) || !a || a > SLA_MAX)
			goto usage;
		local_irq_save(flags);
		t0 = ktime_get_ns();
		for (k = 0; k < a; k++)
			sla_buf[k] = readl(gpio_din + 0x20);
		sla_ns = ktime_get_ns() - t0;
		local_irq_restore(flags);
		sla_n = a;
		emit("sla n=%lu elapsed_ns=%llu\n", a, sla_ns);
	} else if (!strcmp(tok, "sla_dump")) {
		char *s3 = strsep(&line, " \n");

		if (!s1 || !s2 || kstrtoul(s1, 0, &a) || kstrtoul(s2, 0, &b) || a + b > sla_n || b > 8192)
			goto usage;
		(void)s3;
		for (i = 0; i < b; i++)
			emit("%04x%c", sla_buf[a + i], (i & 15) == 15 ? '\n' : ' ');
		emit("\n");
	} else if (!strcmp(tok, "curtrace")) {
		/* curtrace <off> <count> <usec>: timestamped CUR reads (read-only). */
		char *s3 = strsep(&line, " \n");
		unsigned long usec, cnt;

		if (!s1 || !s2 || !s3 || kstrtoul(s1, 0, &a) || !read_ok(a) ||
		    kstrtoul(s2, 0, &cnt) || kstrtoul(s3, 0, &usec) || !cnt || cnt > 256 || usec > 100000)
			goto usage;
		if (need_hold())
			return;
		for (i = 0; i < cnt; i++) {
			emit("%llu %08x\n", ktime_get_ns(), rd(a));
			udelay(usec);
		}
	} else if (!strcmp(tok, "restore_all")) {
		if (need_hold())
			return;
		restore_all();
		emit("restored\n");
	} else if (!strcmp(tok, "dma_alloc")) {
		if (!s1 || !s2 || kstrtouint(s1, 0, &n) || n >= SLOTS ||
		    kstrtoul(s2, 0, &a) || !a || a > MAX_DMA || (a & 15))
			goto usage;
		if (slot[n].area) {
			emit("error: slot %u in use\n", n);
			return;
		}
		slot[n].area = dma_alloc_coherent(afe, a, &slot[n].addr, GFP_KERNEL);
		if (!slot[n].area) {
			emit("error: alloc\n");
			return;
		}
		slot[n].bytes = a;
		memset(slot[n].area, 0, a);
		emit("slot%u addr=0x%08llx bytes=%lu\n", n, (unsigned long long)slot[n].addr, a);
	} else if (!strcmp(tok, "dma_free")) {
		if (!s1 || kstrtouint(s1, 0, &n) || n >= SLOTS || !slot[n].area)
			goto usage;
		dma_free_coherent(afe, slot[n].bytes, slot[n].area, slot[n].addr);
		slot[n].area = NULL;
		emit("freed slot%u\n", n);
	} else if (!strcmp(tok, "dma_fill32")) {
		/* dma_fill32 <slot> <w0> [w1 ...]: repeat a little-endian word pattern. */
		char *w;
		u32 pat[64];
		unsigned int count = 0;
		size_t off;

		if (!s1 || kstrtouint(s1, 0, &n) || n >= SLOTS || !slot[n].area)
			goto usage;
		w = s2;
		while (w && *w && count < ARRAY_SIZE(pat)) {
			if (kstrtoul(w, 0, &a))
				goto usage;
			pat[count++] = a;
			w = strsep(&line, " \n");
		}
		if (!count)
			goto usage;
		for (off = 0, i = 0; off + 4 <= slot[n].bytes; off += 4, i = (i + 1) % count)
			((u32 *)slot[n].area)[off / 4] = pat[i];
		emit("filled slot%u with %u-word pattern\n", n, count);
	} else if (!strcmp(tok, "dma_zero")) {
		if (!s1 || kstrtouint(s1, 0, &n) || n >= SLOTS || !slot[n].area)
			goto usage;
		memset(slot[n].area, 0, slot[n].bytes);
		emit("zeroed slot%u\n", n);
	} else if (!strcmp(tok, "dma_peek")) {
		char *s3 = strsep(&line, " \n");

		if (!s1 || !s2 || !s3 || kstrtouint(s1, 0, &n) || n >= SLOTS ||
		    !slot[n].area || kstrtoul(s2, 0, &a) || kstrtoul(s3, 0, &b) ||
		    (a & 3) || a + b > slot[n].bytes || b > 8192)
			goto usage;
		for (i = 0; i < b; i += 4)
			emit("%06lx=%08x\n", a + i, ((u32 *)slot[n].area)[(a + i) / 4]);
	} else if (!strcmp(tok, "dma_info")) {
		for (i = 0; i < SLOTS; i++)
			if (slot[i].area)
				emit("slot%u addr=0x%08llx bytes=%zu\n", i,
				     (unsigned long long)slot[i].addr, slot[i].bytes);
	} else {
		goto usage;
	}
	return;
usage:
	emit("usage: hold 0|1 | r <off> [n] | dump <a> <b> | wl | state\n"
	     "       sla <n> | sla_dump <start> <n> | curtrace <off> <count> <usec>\n"
	     "       probe_bits <off> | probe <off> <val> | w <off> <val> | restore_all\n"
	     "       dma_alloc <slot> <bytes> | dma_free <slot> | dma_fill32 <slot> <w...>\n"
	     "       dma_zero <slot> | dma_peek <slot> <off> <len> | dma_info\n");
}

static ssize_t cmd_write(struct file *f, const char __user *ubuf, size_t len, loff_t *pos)
{
	char *kbuf, *p, *next;

	if (len > 2048)
		return -E2BIG;
	kbuf = memdup_user_nul(ubuf, len);
	if (IS_ERR(kbuf))
		return PTR_ERR(kbuf);
	mutex_lock(&lock);
	out_len = 0;
	out[0] = 0;
	for (p = kbuf; p; p = next) {
		next = strchr(p, '\n');
		if (next)
			*next++ = 0;
		do_cmd(p);
	}
	mutex_unlock(&lock);
	kfree(kbuf);
	return len;
}

static ssize_t out_read(struct file *f, char __user *ubuf, size_t len, loff_t *pos)
{
	ssize_t ret;

	mutex_lock(&lock);
	ret = simple_read_from_buffer(ubuf, len, pos, out, out_len);
	mutex_unlock(&lock);
	return ret;
}

static ssize_t log_read(struct file *f, char __user *ubuf, size_t len, loff_t *pos)
{
	ssize_t ret;

	mutex_lock(&lock);
	ret = simple_read_from_buffer(ubuf, len, pos, logbuf, log_len);
	mutex_unlock(&lock);
	return ret;
}

static const struct file_operations cmd_fops = { .owner = THIS_MODULE, .write = cmd_write,
						  .llseek = noop_llseek };
static const struct file_operations out_fops = { .owner = THIS_MODULE, .read = out_read,
						  .llseek = default_llseek };
static const struct file_operations log_fops = { .owner = THIS_MODULE, .read = log_read,
						  .llseek = default_llseek };

static int __init lab_init(void)
{
	struct resource *res;

	afe = bus_find_device_by_name(&platform_bus_type, NULL, "11220000.audio-controller");
	if (!afe || !of_device_is_compatible(afe->of_node, "mediatek,mt6582-afe"))
		return -ENODEV;
	res = platform_get_resource(to_platform_device(afe), IORESOURCE_MEM, 0);
	if (!res || res->start != 0x11220000)
		return -ENODEV;
	out = kzalloc(OUT_MAX, GFP_KERNEL);
	logbuf = kzalloc(LOG_MAX, GFP_KERNEL);
	base = ioremap(res->start, AFE_WINDOW);
	gpio_din = ioremap(GPIO_DIN_PHYS, 0x40);
	sla_buf = vmalloc(SLA_MAX * sizeof(*sla_buf));
	if (!out || !logbuf || !base || !gpio_din || !sla_buf) {
		kfree(out);
		kfree(logbuf);
		return -ENOMEM;
	}
	dir = debugfs_create_dir("y2_afe_lab", NULL);
	debugfs_create_file("cmd", 0200, dir, NULL, &cmd_fops);
	debugfs_create_file("out", 0400, dir, NULL, &out_fops);
	debugfs_create_file("log", 0400, dir, NULL, &log_fops);
	return 0;
}
module_init(lab_init);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Temporary Y2 MT6582 AFE whitelisted register/DMA laboratory (no unload)");
