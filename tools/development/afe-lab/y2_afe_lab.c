// SPDX-License-Identifier: GPL-2.0-only
/* Temporary MT6582 AFE register/DMA laboratory.
 *
 * Purpose: answer, on the physical Y2, which AFE memory-interface and
 * interconnect features exist in this exact silicon revision. It is a
 * development instrument, not product code. It is bounded as follows:
 *   - register access is limited to the 0x11220000 AFE window (0x000-0x7fc);
 *   - while "hold 1" is active it owns one runtime-PM reference of the
 *     production AFE device so the audio clocks stay on;
 *   - DMA buffers are ordinary coherent allocations below 4 GiB;
 *   - there is no raw physical memory or other-peripheral access.
 * The installed kernel has CONFIG_MODULE_UNLOAD=n, so this module stays
 * resident until the next reboot. Every experiment is therefore driven through
 * the generic command file rather than by reloading new module code.
 */
#include <linux/debugfs.h>
#include <linux/dma-mapping.h>
#include <linux/io.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/mutex.h>
#include <linux/platform_device.h>
#include <linux/pm_runtime.h>
#include <linux/slab.h>
#include <linux/uaccess.h>

#define AFE_WINDOW	0x800
#define SLOTS		4
#define OUT_MAX		(64 * 1024)
#define MAX_DMA		(512 * 1024)

static struct device *afe;
static void __iomem *base;
static struct dentry *dir;
static DEFINE_MUTEX(lock);
static bool held;
static char *out;
static size_t out_len;

static struct {
	void *area;
	dma_addr_t addr;
	size_t bytes;
} slot[SLOTS];

static __printf(1, 2) void emit(const char *fmt, ...)
{
	va_list ap;

	if (out_len >= OUT_MAX - 1)
		return;
	va_start(ap, fmt);
	out_len += vscnprintf(out + out_len, OUT_MAX - out_len, fmt, ap);
	va_end(ap);
}

static bool reg_ok(unsigned long off)
{
	return off < AFE_WINDOW && !(off & 3);
}

static int ensure_hold(void)
{
	if (!held) {
		emit("error: need 'hold 1' first (AFE clocks must be on)\n");
		return -EAGAIN;
	}
	return 0;
}

static void do_cmd(char *line)
{
	char *tok = strsep(&line, " \t\n");
	unsigned long a, b, c;
	unsigned int n, i;

	if (!tok || !*tok)
		return;
	if (!strcmp(tok, "hold")) {
		int ret;

		if (kstrtoul(strsep(&line, " \n") ?: "", 0, &a))
			goto usage;
		if (a && !held) {
			ret = pm_runtime_resume_and_get(afe);
			if (ret < 0) {
				emit("error: resume %d\n", ret);
				return;
			}
			held = true;
		} else if (!a && held) {
			pm_runtime_put(afe);
			held = false;
		}
		emit("hold=%d\n", held);
	} else if (!strcmp(tok, "r")) {
		char *s1 = strsep(&line, " \n"), *s2 = strsep(&line, " \n");

		if (!s1 || kstrtoul(s1, 0, &a) || !reg_ok(a))
			goto usage;
		n = 1;
		if (s2 && !kstrtoul(s2, 0, &b) && b && b < 256)
			n = b;
		if (ensure_hold())
			return;
		for (i = 0; i < n && reg_ok(a + 4 * i); i++)
			emit("%04lx=%08x\n", a + 4 * i, readl(base + a + 4 * i));
	} else if (!strcmp(tok, "dump")) {
		char *s1 = strsep(&line, " \n"), *s2 = strsep(&line, " \n");

		if (!s1 || !s2 || kstrtoul(s1, 0, &a) || kstrtoul(s2, 0, &b) ||
		    !reg_ok(a) || !reg_ok(b) || b < a)
			goto usage;
		if (ensure_hold())
			return;
		for (; a <= b; a += 4)
			emit("%04lx=%08x\n", a, readl(base + a));
	} else if (!strcmp(tok, "w")) {
		char *s1 = strsep(&line, " \n"), *s2 = strsep(&line, " \n");

		if (!s1 || !s2 || kstrtoul(s1, 0, &a) || kstrtoul(s2, 0, &b) ||
		    !reg_ok(a))
			goto usage;
		if (ensure_hold())
			return;
		writel(b, base + a);
		emit("%04lx<=%08lx now %08x\n", a, b, readl(base + a));
	} else if (!strcmp(tok, "m")) {
		char *s1 = strsep(&line, " \n"), *s2 = strsep(&line, " \n"),
		     *s3 = strsep(&line, " \n");
		u32 v;

		if (!s1 || !s2 || !s3 || kstrtoul(s1, 0, &a) ||
		    kstrtoul(s2, 0, &b) || kstrtoul(s3, 0, &c) || !reg_ok(a))
			goto usage;
		if (ensure_hold())
			return;
		v = readl(base + a);
		v = (v & ~(u32)b) | ((u32)c & (u32)b);
		writel(v, base + a);
		emit("%04lx mask %08lx val %08lx now %08x\n", a, b, c, readl(base + a));
	} else if (!strcmp(tok, "dma_alloc")) {
		char *s1 = strsep(&line, " \n"), *s2 = strsep(&line, " \n");

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
		emit("slot%u addr=0x%08llx bytes=%lu\n", n,
		     (unsigned long long)slot[n].addr, a);
	} else if (!strcmp(tok, "dma_free")) {
		char *s1 = strsep(&line, " \n");

		if (!s1 || kstrtouint(s1, 0, &n) || n >= SLOTS || !slot[n].area)
			goto usage;
		dma_free_coherent(afe, slot[n].bytes, slot[n].area, slot[n].addr);
		slot[n].area = NULL;
		emit("freed slot%u\n", n);
	} else if (!strcmp(tok, "dma_fill32")) {
		/* dma_fill32 <slot> <w0> [w1 ...]: repeat a little-endian word pattern. */
		char *s1 = strsep(&line, " \n"), *w;
		u32 pat[64];
		unsigned int count = 0;
		size_t off;

		if (!s1 || kstrtouint(s1, 0, &n) || n >= SLOTS || !slot[n].area)
			goto usage;
		while ((w = strsep(&line, " \n")) && *w && count < ARRAY_SIZE(pat)) {
			if (kstrtoul(w, 0, &a))
				goto usage;
			pat[count++] = a;
		}
		if (!count)
			goto usage;
		for (off = 0, i = 0; off + 4 <= slot[n].bytes; off += 4, i = (i + 1) % count)
			((u32 *)slot[n].area)[off / 4] = pat[i];
		emit("filled slot%u with %u-word pattern\n", n, count);
	} else if (!strcmp(tok, "dma_zero")) {
		char *s1 = strsep(&line, " \n");

		if (!s1 || kstrtouint(s1, 0, &n) || n >= SLOTS || !slot[n].area)
			goto usage;
		memset(slot[n].area, 0, slot[n].bytes);
		emit("zeroed slot%u\n", n);
	} else if (!strcmp(tok, "dma_peek")) {
		char *s1 = strsep(&line, " \n"), *s2 = strsep(&line, " \n"),
		     *s3 = strsep(&line, " \n");

		if (!s1 || !s2 || !s3 || kstrtouint(s1, 0, &n) || n >= SLOTS ||
		    !slot[n].area || kstrtoul(s2, 0, &a) || kstrtoul(s3, 0, &b) ||
		    (a & 3) || a + b > slot[n].bytes || b > 4096)
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
	emit("usage: hold 0|1 | r <off> [n] | dump <a> <b> | w <off> <val> | m <off> <mask> <val>\n"
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

static const struct file_operations cmd_fops = { .owner = THIS_MODULE, .write = cmd_write,
						  .llseek = noop_llseek };
static const struct file_operations out_fops = { .owner = THIS_MODULE, .read = out_read,
						  .llseek = default_llseek };

static int __init lab_init(void)
{
	struct resource *res;
	struct platform_device *pdev;

	afe = bus_find_device_by_name(&platform_bus_type, NULL, "11220000.audio-controller");
	if (!afe || !of_device_is_compatible(afe->of_node, "mediatek,mt6582-afe"))
		return -ENODEV;
	pdev = to_platform_device(afe);
	res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
	if (!res || res->start != 0x11220000)
		return -ENODEV;
	out = kzalloc(OUT_MAX, GFP_KERNEL);
	base = ioremap(res->start, AFE_WINDOW);
	if (!out || !base) {
		kfree(out);
		return -ENOMEM;
	}
	dir = debugfs_create_dir("y2_afe_lab", NULL);
	debugfs_create_file("cmd", 0200, dir, NULL, &cmd_fops);
	debugfs_create_file("out", 0400, dir, NULL, &out_fops);
	return 0;
}
module_init(lab_init);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Temporary Y2 MT6582 AFE register/DMA laboratory (no unload)");
