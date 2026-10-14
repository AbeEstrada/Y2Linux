/* SPDX-License-Identifier: GPL-2.0-only
 * Signed full-system updater (OTA-35). One native policy authority shared by
 * the normal system, the BOOTIMG rescue and the Y2 recovery image:
 *
 *   normal    check/queue a signed package, install a newer RECOVERY image,
 *             request recovery through the MISC bootloader message, ack/rollback
 *   rescue    boot-check: route an unfinished update to recovery, never install
 *   recovery  back up BOOTIMG + Y2ROOT, write and read back both, restore both
 *
 * LK boots RECOVERY while MISC starts with "boot-recovery"; the request is
 * cleared only after the installed or restored images are verified, so a power
 * loss re-enters recovery. A kernel never writes the image it was booted from
 * (kernel/platform/storage-policy.h enforces the same rule below this tool).
 * Y2_UPDATE_TEST enables regular-file/fault fixtures; never used in the image.
 */
#define _GNU_SOURCE
#define _FILE_OFFSET_BITS 64
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <json-c/json.h>
#include <limits.h>
#include <linux/fs.h>
#include <sodium.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/ioctl.h>
#include <sys/random.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <unistd.h>
#include <zlib.h>

#define LIMIT (820ULL * 1024 * 1024)
#define RESERVE (96ULL * 1024 * 1024)
#define CHUNK 131072
/* Stock logical disk (mmcblk0, 15203328 sectors); see storage-policy.h. */
#define DISK_SECTORS 15203328ULL
#define IMAGE_BYTES (16ULL * 1024 * 1024)
#define BOOTIMG_OFFSET (60416ULL * 512)
#define RECOVERY_OFFSET (93184ULL * 512)
#define MISC_OFFSET (138240ULL * 512)
#define MISC_BYTES 4096
#define BOOT_NAME "Y2Linux-M1"
#define RECOVERY_NAME "Y2Recovery-1"
#define RECOVERY_API 1
#define HEALTH_BOOTS 2

enum kind { ROOT, BOOT, RECOVERY, REGION };
static const char *const payload_key[] = {"rootfs", "bootimg", "recovery", ""};
static const char *const payload_file[] = {"rootfs.ext4.gz", "bootimg.img.gz", "recovery.img.gz", ""};

static char error_text[192];
static int basefd = -1;
static const char *testroot;
static bool recovery_env;
static bool failure(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(error_text, sizeof(error_text), fmt, ap);
    va_end(ap);
    return false;
}
static const char *path(const char *p) {
    static char slots[8][PATH_MAX];
    static unsigned slot;
    char *out = slots[slot++ % 8];
    if (snprintf(out, PATH_MAX, "%s%s", testroot ? testroot : "", p) >= PATH_MAX)
        return "";
    return out;
}
static bool writeall(int fd, const void *buf, size_t n) {
    const char *p = buf;
    while (n) {
        ssize_t done = write(fd, p, n);
        if (done < 0 && errno == EINTR)
            continue;
        if (done <= 0)
            return failure("write: %s", strerror(errno));
        p += done;
        n -= (size_t)done;
    }
    return true;
}
static int openfile(int dir, const char *name, int flags, mode_t mode) {
    int fd = openat(dir, name, flags | O_CLOEXEC | O_NOFOLLOW, mode);
    struct stat st;
    if (fd < 0) {
        failure("open %s: %s", name, strerror(errno));
        return -1;
    }
    if (fstat(fd, &st) || !S_ISREG(st.st_mode) || st.st_nlink != 1) {
        close(fd);
        failure("not a private regular file: %s", name);
        return -1;
    }
    return fd;
}
static char *readfile(int dir, const char *name, size_t limit, size_t *len) {
    int fd = openfile(dir, name, O_RDONLY, 0);
    if (fd < 0)
        return NULL;
    struct stat st;
    if (fstat(fd, &st) || st.st_size < 0 || (uint64_t)st.st_size > limit) {
        close(fd);
        failure("file size: %s", name);
        return NULL;
    }
    char *buf = calloc((size_t)st.st_size + 1, 1);
    if (!buf) {
        close(fd);
        failure("allocation");
        return NULL;
    }
    size_t got = 0, need = (size_t)st.st_size;
    while (got < need) {
        ssize_t n = read(fd, buf + got, need - got);
        if (n < 0 && errno == EINTR)
            continue;
        if (n <= 0) {
            free(buf);
            close(fd);
            failure("short read: %s", name);
            return NULL;
        }
        got += (size_t)n;
    }
    close(fd);
    *len = got;
    return buf;
}
static json_object *parse(const char *buf, size_t n) {
    json_tokener *tok = json_tokener_new_ex(16);
    if (!tok)
        return NULL;
    json_tokener_set_flags(tok, JSON_TOKENER_STRICT | JSON_TOKENER_VALIDATE_UTF8);
    json_object *j = json_tokener_parse_ex(tok, buf, (int)n);
    bool ok = json_tokener_get_error(tok) == json_tokener_success &&
              json_tokener_get_parse_end(tok) == n && j && json_object_is_type(j, json_type_object);
    json_tokener_free(tok);
    if (!ok) {
        if (j)
            json_object_put(j);
        failure("invalid JSON object");
        return NULL;
    }
    return j;
}
static json_object *load(int dir, const char *name) {
    errno = 0;
    size_t n;
    char *buf = readfile(dir, name, 16384, &n);
    if (!buf)
        return NULL;
    json_object *j = parse(buf, n);
    free(buf);
    if (!j)
        errno = EINVAL;
    return j;
}
static json_object *field(json_object *j, const char *k) {
    json_object *v = NULL;
    json_object_object_get_ex(j, k, &v);
    return v;
}
static const char *str(json_object *j, const char *k) {
    json_object *v = field(j, k);
    return v && json_object_is_type(v, json_type_string) ? json_object_get_string(v) : "";
}
static int64_t num(json_object *j, const char *k) {
    json_object *v = field(j, k);
    return v && json_object_is_type(v, json_type_int) ? json_object_get_int64(v) : -1;
}
static bool yes(json_object *j, const char *k) {
    json_object *v = field(j, k);
    return v && json_object_is_type(v, json_type_boolean) && json_object_get_boolean(v);
}
static void setstr(json_object *j, const char *k, const char *v) {
    json_object_object_add(j, k, json_object_new_string(v));
}
static void setnum(json_object *j, const char *k, int64_t v) {
    json_object_object_add(j, k, json_object_new_int64(v));
}
static bool save(const char *name, json_object *j) {
    char tmp[80];
    if (snprintf(tmp, sizeof(tmp), ".%s.tmp", name) >= (int)sizeof(tmp))
        return failure("record name");
    /* An interrupted temp file can only belong to this locked writer. */
    if (unlinkat(basefd, tmp, 0) && errno != ENOENT)
        return failure("record cleanup");
    int fd = openfile(basefd, tmp, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd < 0)
        return false;
    const char *s = json_object_to_json_string_ext(j, JSON_C_TO_STRING_PLAIN);
    bool ok = writeall(fd, s, strlen(s)) && fsync(fd) == 0;
    close(fd);
    if (!ok || renameat(basefd, tmp, basefd, name) || fsync(basefd))
        return failure("durable record: %s", strerror(errno));
    return true;
}
static bool hex(const char *s, size_t bytes, unsigned char *out) {
    if (strlen(s) != 2 * bytes)
        return false;
    for (const char *p = s; *p; p++)
        if (!(*p >= '0' && *p <= '9') && !(*p >= 'a' && *p <= 'f'))
            return false;
    return sodium_hex2bin(out, bytes, s, 2 * bytes, NULL, NULL, NULL) == 0;
}
static bool sha_match(const unsigned char *sum, const char *wanted) {
    unsigned char expected[32];
    return hex(wanted, 32, expected) && sodium_memcmp(sum, expected, 32) == 0;
}
static const char *hash_string(const unsigned char *sum) {
    static char out[65];
    sodium_bin2hex(out, sizeof(out), sum, 32);
    return out;
}
static bool readtext(const char *name, char *buf, size_t cap) {
    FILE *f = fopen(path(name), "re");
    if (!f)
        return false;
    bool ok = fgets(buf, (int)cap, f) != NULL && !ferror(f);
    fclose(f);
    if (ok)
        buf[strcspn(buf, "\r\n")] = 0;
    return ok;
}
static bool text_is(const char *name, const char *want) {
    char buf[256];
    return readtext(name, buf, sizeof(buf)) && !strcmp(buf, want);
}
/* Progress for the recovery screen, and (OTA-48) for the normal system's
 * download check that Reborn shows: "<percent> <step>". Best effort. Each new
 * recovery step is also logged to the kernel log, whose timestamps time the
 * install. */
static const char *progress_step;
static const char *progress_name;
static void progress(unsigned percent, const char *step) {
    if (!progress_name)
        return;
    if (recovery_env && (!progress_step || strcmp(progress_step, step))) {
        progress_step = step;
        int log = open(path("/dev/kmsg"), O_WRONLY | O_APPEND | O_CLOEXEC);
        if (log >= 0) {
            dprintf(log, "<6>Y2RECOVERY step=%s percent=%u\n", step, percent);
            close(log);
        }
    }
    char buf[64];
    int n = snprintf(buf, sizeof(buf), "%u %s\n", percent > 100 ? 100 : percent, step);
    char tmp[64];
    snprintf(tmp, sizeof(tmp), "%s.tmp", progress_name);
    int fd = open(path(tmp), O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
    if (fd < 0)
        return;
    bool ok = n > 0 && writeall(fd, buf, (size_t)n);
    close(fd);
    if (ok)
        rename(path(tmp), path(progress_name));
}
/* A step that moves the bar from base to base+span over total bytes. */
static struct {
    const char *step;
    unsigned base, span, last;
    uint64_t total;
} prog;
static void progress_span(const char *step, unsigned base, unsigned span, uint64_t total) {
    prog.step = step;
    prog.base = base;
    prog.span = span;
    prog.total = total;
    prog.last = base;
    progress(base, step);
}
static void progress_bytes(uint64_t done) {
    if (!prog.step || !prog.total)
        return;
    unsigned p = prog.base + (unsigned)((done > prog.total ? prog.total : done) * prog.span / prog.total);
    if (p != prog.last) {
        prog.last = p;
        progress(p, prog.step);
    }
}
static bool enough(int fd, uint64_t bytes) {
#ifdef Y2_UPDATE_TEST
    if (getenv("Y2_TEST_FAULT") && !strcmp(getenv("Y2_TEST_FAULT"), "reserve"))
        return failure("data reserve unavailable");
#endif
    struct statvfs st;
    if (fstatvfs(fd, &st) || !st.f_frsize || (st.f_flag & ST_RDONLY) ||
        (uint64_t)st.f_bavail * st.f_frsize < RESERVE + bytes || (st.f_files && st.f_favail < 128))
        return failure("data reserve unavailable");
    return true;
}
static uint16_t u16(const unsigned char *p) { return (uint16_t)p[0] | (uint16_t)p[1] << 8; }
static uint32_t u32(const unsigned char *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static uint64_t root_bytes(const unsigned char *buf) {
    const unsigned char uuid[16] = {0x79, 0x32, 0x4c, 0x69, 0x6e, 0x75, 0x48, 0x01,
                                    0x80, 0,    0,    0,    0,    0,    1,    1};
    const unsigned char *s = buf + 1024;
    uint32_t log = u32(s + 24);
    if (u16(s + 56) != 0xef53 || memcmp(s + 104, uuid, 16) || memcmp(s + 120, "Y2ROOT\0", 7) ||
        log > 2)
        return 0;
    uint64_t blocks = u32(s + 4);
    if (u32(s + 96) & 0x80)
        blocks |= (uint64_t)u32(s + 336) << 32;
    uint64_t size = blocks * (1024ULL << log);
    return size >= 8 * 1024 * 1024 && size <= LIMIT ? size : 0;
}
/* The one reviewed legacy Android/MTK layout (tools/validation/bootimg.py):
 * 2048-byte pages, MTK-wrapped KERNEL and ROOTFS/RECOVERY, our image name. */
static bool boot_identity(const unsigned char *b, uint64_t len, enum kind kind) {
    if (len < 4096 || len > IMAGE_BYTES || memcmp(b, "ANDROID!", 8) || u32(b + 36) != 2048)
        return false;
    char name[17] = {0};
    memcpy(name, b + 48, 16);
    if (strcmp(name, kind == RECOVERY ? RECOVERY_NAME : BOOT_NAME))
        return false;
    uint64_t k = u32(b + 8), r = u32(b + 16);
    uint64_t ko = 2048, ro = ko + ((k + 2047) & ~2047ULL);
    if (k < 512 || r < 512 || ro + ((r + 2047) & ~2047ULL) > len)
        return false;
    const char *label = kind == RECOVERY ? "RECOVERY" : "ROOTFS";
    char want[32] = {0};
    memcpy(want, label, strlen(label));
    return u32(b + ko) == 0x58881688 && u32(b + ko + 4) == k - 512 &&
           !memcmp(b + ko + 8, "KERNEL\0", 7) && u32(b + ro) == 0x58881688 &&
           u32(b + ro + 4) == r - 512 && !memcmp(b + ro + 8, want, 32);
}
/* gzip must have one member, exact encoded and raw lengths, the SHA-256 of the
 * encoded bytes (signed manifest or our backup record) and the kind's identity.
 * The encoded hash authenticates the payload; zlib checks the gzip CRC-32 and
 * length trailer of the output, and a record's raw_crc32 when it has one.
 * STREAM_RAW_SHA also requires the raw SHA-256 (backups recorded before
 * OTA-38 carry only that). STREAM_SKIP_SAME writes only the 128 KiB chunks
 * that differ from what the output already holds. Root streams to a
 * descriptor; boot images and the 16 MiB span backups decode into a
 * zero-filled buffer for aligned I/O. *crc receives the raw CRC-32.
 */
#define STREAM_INJECT 1u
#define STREAM_RAW_SHA 2u
#define STREAM_SKIP_SAME 4u
static uint64_t stream_written;
static bool stream_image(int input, int output, unsigned char *mem, json_object *payload,
                         enum kind kind, unsigned flags, uint32_t *crc) {
    bool inject = flags & STREAM_INJECT;
    uint64_t limit = kind == ROOT ? LIMIT : IMAGE_BYTES;
    uint64_t minimum = kind == ROOT ? 8 * 1024 * 1024 : 4096;
    if (num(payload, "bytes") <= 0 || num(payload, "bytes") > (int64_t)LIMIT ||
        num(payload, "raw_bytes") < (int64_t)minimum || num(payload, "raw_bytes") > (int64_t)limit ||
        (kind == REGION && num(payload, "raw_bytes") != (int64_t)IMAGE_BYTES))
        return failure("image metadata bounds");
    static unsigned char in[CHUNK], out[CHUNK], old[CHUNK];
    unsigned char header[4096], csum[32], rsum[32];
    size_t head = 0;
    uint64_t compressed = 0, raw = 0;
    uLong rawcrc = crc32(0L, Z_NULL, 0);
    crypto_hash_sha256_state ch, rh;
    crypto_hash_sha256_init(&ch);
    crypto_hash_sha256_init(&rh);
    z_stream z = {0};
    if (inflateInit2(&z, 15 + 16) != Z_OK)
        return failure("gzip init");
    if (lseek(input, 0, SEEK_SET) < 0 || (output >= 0 && lseek(output, 0, SEEK_SET) < 0)) {
        inflateEnd(&z);
        return failure("image seek");
    }
    if (mem)
        memset(mem, 0, IMAGE_BYTES);
    bool ok = false, ended = false;
    for (;;) {
        ssize_t n = read(input, in, sizeof(in));
        if (n < 0 && errno == EINTR)
            continue;
        if (n < 0) {
            failure("payload read");
            break;
        }
        if (!n) {
            if (!ended)
                failure("incomplete gzip");
            else
                ok = true;
            break;
        }
        if (ended) {
            failure("trailing gzip bytes");
            break;
        }
        compressed += (uint64_t)n;
        if (compressed > (uint64_t)num(payload, "bytes")) {
            failure("encoded size");
            break;
        }
        crypto_hash_sha256_update(&ch, in, (size_t)n);
        z.next_in = in;
        z.avail_in = (uInt)n;
        do {
            z.next_out = out;
            z.avail_out = sizeof(out);
            int rc = inflate(&z, Z_NO_FLUSH);
            size_t count = sizeof(out) - z.avail_out;
            if (raw + count > (uint64_t)num(payload, "raw_bytes")) {
                failure("raw size");
                goto done;
            }
            if (head < sizeof(header)) {
                size_t copy = count < sizeof(header) - head ? count : sizeof(header) - head;
                memcpy(header + head, out, copy);
                head += copy;
            }
            if (mem && count)
                memcpy(mem + raw, out, count);
            if (output >= 0 && count) {
                bool same = false;
                if (flags & STREAM_SKIP_SAME) {
                    ssize_t got = pread(output, old, count, (off_t)raw);
                    same = got == (ssize_t)count && !memcmp(old, out, count);
                }
                if (!same) {
                    size_t done = 0;
                    while (done < count) {
                        ssize_t w = pwrite(output, out + done, count - done, (off_t)(raw + done));
                        if (w < 0 && errno == EINTR)
                            continue;
                        if (w <= 0) {
                            failure("write: %s", w < 0 ? strerror(errno) : "short");
                            goto done;
                        }
                        done += (size_t)w;
                    }
                    stream_written += count;
                }
            }
            raw += count;
            rawcrc = crc32(rawcrc, out, (uInt)count);
            if (flags & STREAM_RAW_SHA)
                crypto_hash_sha256_update(&rh, out, count);
            progress_bytes(raw);
            if (kind == ROOT && head == sizeof(header) &&
                root_bytes(header) != (uint64_t)num(payload, "raw_bytes")) {
                failure("root ext4 identity/extent");
                goto done;
            }
#ifdef Y2_UPDATE_TEST
            if (inject && getenv("Y2_TEST_FAULT") &&
                !strcmp(getenv("Y2_TEST_FAULT"), "write_interrupt") && raw >= CHUNK)
                _exit(91);
#else
            (void)inject;
#endif
            if (rc == Z_STREAM_END) {
                ended = true;
                if (z.avail_in) {
                    failure("multiple gzip members");
                    goto done;
                }
                break;
            }
            if (rc == Z_BUF_ERROR && !z.avail_in && z.avail_out == sizeof(out))
                break;
            if (rc != Z_OK) {
                failure("gzip corruption");
                goto done;
            }
        } while (z.avail_in || z.avail_out == 0);
    }
    if (!ok)
        goto done;
    crypto_hash_sha256_final(&ch, csum);
    crypto_hash_sha256_final(&rh, rsum);
    ok = head == sizeof(header) && raw == (uint64_t)num(payload, "raw_bytes") &&
         compressed == (uint64_t)num(payload, "bytes") && sha_match(csum, str(payload, "sha256")) &&
         (!(flags & STREAM_RAW_SHA) || sha_match(rsum, str(payload, "raw_sha256"))) &&
         (!field(payload, "raw_crc32") || num(payload, "raw_crc32") == (int64_t)rawcrc);
    if (!ok)
        failure("payload hash/size mismatch");
    else if (crc)
        *crc = (uint32_t)rawcrc;
    else if ((kind == BOOT || kind == RECOVERY) && !(mem && boot_identity(mem, raw, kind)))
        ok = failure("%s image identity", payload_key[kind]);
done:
    inflateEnd(&z);
    return ok;
}
static bool drop_cache(int fd) {
    /* Read back the medium, not the page cache that the write just filled. */
    if (ioctl(fd, BLKFLSBUF, 0) && errno != ENOTTY && errno != EINVAL)
        return failure("cache invalidate: %s", strerror(errno));
    posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);
    return true;
}
/* Readback of the medium against the CRC-32 computed while writing: detects
 * storage faults at memory speed; authenticity was settled before writing. */
static bool file_crc(int fd, uint64_t count, uint32_t expected) {
    if (!drop_cache(fd))
        return false;
    static unsigned char buf[CHUNK];
    uLong c = crc32(0L, Z_NULL, 0);
    uint64_t at = 0;
    while (at < count) {
        ssize_t n = pread(fd, buf, count - at < sizeof(buf) ? (size_t)(count - at) : sizeof(buf), (off_t)at);
        if (n < 0 && errno == EINTR)
            continue;
        if (n <= 0)
            return failure("readback short read");
        c = crc32(c, buf, (uInt)n);
        at += (uint64_t)n;
        progress_bytes(at);
    }
    return (uint32_t)c == expected || failure("readback mismatch");
}
static bool file_hash(int fd, uint64_t count, const char *expected) {
    if (!drop_cache(fd))
        return false;
    if (lseek(fd, 0, SEEK_SET) < 0)
        return failure("readback seek");
    crypto_hash_sha256_state h;
    crypto_hash_sha256_init(&h);
    unsigned char buf[CHUNK], sum[32];
    uint64_t total = count;
    while (count) {
        ssize_t n = read(fd, buf, count < sizeof(buf) ? (size_t)count : sizeof(buf));
        if (n < 0 && errno == EINTR)
            continue;
        if (n <= 0)
            return failure("readback short read");
        crypto_hash_sha256_update(&h, buf, (size_t)n);
        count -= (uint64_t)n;
        progress_bytes(total - count);
    }
    crypto_hash_sha256_final(&h, sum);
    return sha_match(sum, expected) || failure("readback hash mismatch");
}
static bool crypto_ready(void) {
    /* sodium_init may need the CSPRNG even for verification. Never weaken it. */
    unsigned char ready;
    return (getrandom(&ready, 1, GRND_NONBLOCK) == 1 && sodium_init() >= 0) ||
           failure("kernel entropy not ready");
}
static bool payload_contract(json_object *p, enum kind kind) {
    unsigned char hash[32];
    uint64_t limit = kind == ROOT ? LIMIT : IMAGE_BYTES;
    return p && json_object_is_type(p, json_type_object) &&
           !strcmp(str(p, "name"), payload_file[kind]) && !strcmp(str(p, "encoding"), "gzip") &&
           num(p, "bytes") >= 1 && num(p, "bytes") <= (int64_t)LIMIT &&
           num(p, "raw_bytes") >= (kind == ROOT ? 8 * 1024 * 1024 : 4096) &&
           num(p, "raw_bytes") <= (int64_t)limit && hex(str(p, "sha256"), 32, hash) &&
           hex(str(p, "raw_sha256"), 32, hash);
}
static json_object *payload(json_object *m, enum kind kind) {
    return field(field(m, "payloads"), payload_key[kind]);
}
static bool check_payload(int package, json_object *m, enum kind kind, unsigned char *mem) {
    int fd = openfile(package, payload_file[kind], O_RDONLY, 0);
    if (fd < 0)
        return false;
    bool ok = stream_image(fd, -1, mem, payload(m, kind), kind, 0, NULL);
    close(fd);
    return ok;
}
/* SHA-256 of the encoded bytes against the record: the authenticity check that
 * the recovery repeats before it writes (the decoded content follows). */
static bool file_digest(int dir, const char *name, json_object *p) {
    int fd = openfile(dir, name, O_RDONLY, 0);
    if (fd < 0)
        return false;
    static unsigned char buf[CHUNK];
    unsigned char sum[32];
    crypto_hash_sha256_state h;
    crypto_hash_sha256_init(&h);
    uint64_t total = 0;
    for (;;) {
        ssize_t n = read(fd, buf, sizeof(buf));
        if (n < 0 && errno == EINTR)
            continue;
        if (n < 0) {
            close(fd);
            return failure("payload read");
        }
        if (!n)
            break;
        crypto_hash_sha256_update(&h, buf, (size_t)n);
        total += (uint64_t)n;
    }
    close(fd);
    crypto_hash_sha256_final(&h, sum);
    return (total == (uint64_t)num(p, "bytes") && sha_match(sum, str(p, "sha256"))) ||
           failure("%s hash/size mismatch", name);
}
static unsigned char *image_buffer(void) {
    void *p = NULL;
    if (posix_memalign(&p, 4096, IMAGE_BYTES)) {
        failure("image buffer allocation");
        return NULL;
    }
    return p;
}
/* installed < 0: the running system's compat sequence. The recovery image
 * passes the sequence the normal system recorded when it queued the package:
 * its own compat file names the recovery's release, which may be this one. */
/* check: 0 manifest only, 1 decode every payload (staging), 2 SHA-256 of the
 * encoded payloads only (the recovery, which decodes while it writes). */
static json_object *verify(int package, int check, int64_t installed_sequence) {
    if (!crypto_ready())
        return NULL;
    size_t length, siglen;
    char *raw = readfile(package, "manifest.json", 16384, &length);
    if (!raw)
        return NULL;
    json_object *m = parse(raw, length), *trust = NULL, *compat = NULL;
    char *sig = NULL;
    if (!m)
        goto fail;
    trust = load(AT_FDCWD, path("/etc/y2linux/update-trust.json"));
    compat = load(AT_FDCWD, path("/etc/y2linux/update-compat.json"));
    if (!trust || !compat)
        goto fail;
    if (num(trust, "schema") != 1 || num(compat, "schema") != 2) {
        failure("schema incompatible");
        goto fail;
    }
    json_object *keys = field(trust, "keys"), *key = NULL;
    if (!keys || !json_object_is_type(keys, json_type_array) ||
        json_object_array_length(keys) > 16) {
        failure("trust store");
        goto fail;
    }
    for (size_t i = 0; i < json_object_array_length(keys); i++) {
        json_object *item = json_object_array_get_idx(keys, i);
        if (!strcmp(str(item, "id"), str(m, "key_id"))) {
            if (key) {
                failure("ambiguous key");
                goto fail;
            }
            key = item;
        }
    }
    unsigned char pub[32];
    if (!key || strcmp(str(key, "status"), "active") || !hex(str(key, "public_key_hex"), 32, pub)) {
        failure("unknown/revoked signing key");
        goto fail;
    }
    sig = readfile(package, "manifest.sig", 64, &siglen);
    if (!sig || siglen != 64 ||
        crypto_sign_verify_detached((const unsigned char *)sig, (const unsigned char *)raw, length,
                                    pub)) {
        failure("invalid signature");
        goto fail;
    }
    /* Nothing from the manifest is acted on before authentication. */
    if (num(m, "schema") != 2) {
        failure("manifest schema");
        goto fail;
    }
    const char *exact[] = {"product", "hardware_revision", "rootfs_contract", NULL};
    for (unsigned i = 0; exact[i]; i++)
        if (!*str(m, exact[i]) || strcmp(str(m, exact[i]), str(compat, exact[i]))) {
            failure("incompatible %s", exact[i]);
            goto fail;
        }
    if (num(m, "layout_schema") != num(compat, "layout_schema") ||
        num(m, "data_schema") != num(compat, "data_schema") || num(m, "data_schema") < 1 ||
        num(m, "recovery_api") != RECOVERY_API || num(m, "reborn_database_schema") != 1 ||
        num(m, "sequence") < 1 || num(m, "minimum_sequence") < 0 ||
        num(m, "sequence") < num(key, "minimum_sequence") ||
        num(m, "sequence") > num(key, "maximum_sequence") || !*str(m, "release_version") ||
        !*str(m, "rootfs_version") || !*str(m, "kernel")) {
        failure("version/schema/key policy");
        goto fail;
    }
    unsigned char commit[20];
    if (!hex(str(m, "y2linux_commit"), 20, commit) || !hex(str(m, "reborn_commit"), 20, commit)) {
        failure("source identity");
        goto fail;
    }
    int64_t installed = installed_sequence >= 0 ? installed_sequence : num(compat, "sequence");
    bool downgrade = num(m, "sequence") <= installed;
    json_object *water = load(basefd, "accepted.json");
    if (water) {
        if (num(water, "sequence") < 0 || num(water, "current_sequence") < 0) {
            json_object_put(water);
            failure("accepted sequence invalid");
            goto fail;
        }
        /* The running system's own sequence wins over a stale record, e.g.
         * after a computer flash of a newer release. */
        if (num(water, "current_sequence") > installed)
            installed = num(water, "current_sequence");
        downgrade |= num(m, "sequence") <= num(water, "sequence");
        json_object_put(water);
    } else if (errno != ENOENT) {
        failure("accepted sequence unreadable");
        goto fail;
    }
    if (num(m, "minimum_sequence") > installed) {
        failure("minimum compatible release");
        goto fail;
    }
    if (downgrade && !(yes(m, "allow_downgrade") && yes(key, "allow_downgrade") &&
                       !strcmp(str(key, "purpose"), "development"))) {
        failure("downgrade/replay refused");
        goto fail;
    }
    json_object *list = field(m, "payloads");
    if (!list || !json_object_is_type(list, json_type_object) ||
        !payload_contract(payload(m, ROOT), ROOT) || !payload_contract(payload(m, BOOT), BOOT) ||
        (payload(m, RECOVERY) && !payload_contract(payload(m, RECOVERY), RECOVERY)) ||
        json_object_object_length(list) != (payload(m, RECOVERY) ? 3 : 2)) {
        failure("payload contract");
        goto fail;
    }
    if (check == 2) {
        progress_span("verify", 0, 3, 3);
        bool ok = file_digest(package, payload_file[ROOT], payload(m, ROOT)) &&
                  file_digest(package, payload_file[BOOT], payload(m, BOOT)) &&
                  (!payload(m, RECOVERY) || file_digest(package, payload_file[RECOVERY], payload(m, RECOVERY)));
        if (!ok)
            goto fail;
    } else if (check == 1) {
        unsigned char *mem = image_buffer();
        /* The root is nearly all of the decoding work. */
        progress_span("check", 0, 96, (uint64_t)num(payload(m, ROOT), "raw_bytes"));
        bool ok = mem && check_payload(package, m, ROOT, NULL) && check_payload(package, m, BOOT, mem) &&
                  (!payload(m, RECOVERY) || check_payload(package, m, RECOVERY, mem));
        free(mem);
        if (!ok)
            goto fail;
        progress(100, "check");
    }
    unsigned char manifest_hash[32];
    crypto_hash_sha256(manifest_hash, (const unsigned char *)raw, length);
    setstr(m, "_manifest_sha256", hash_string(manifest_hash));
    setnum(m, "_previous_sequence", installed);
    free(sig);
    free(raw);
    json_object_put(trust);
    json_object_put(compat);
    error_text[0] = 0;
    return m;
fail:
    free(sig);
    free(raw);
    if (trust)
        json_object_put(trust);
    if (compat)
        json_object_put(compat);
    if (m)
        json_object_put(m);
    return NULL;
}
/* Internal eMMC by controller, media type and immutable geometry; never a
 * caller-supplied device path. Writes are confined to the matching kernel policy. */
static bool internal_disk(const char *actual, char *parent, size_t cap) {
    if (!strstr(actual, "/11230000.mmc/") || !strstr(actual, "/block/"))
        return false;
    char item[PATH_MAX + 32];
    if (snprintf(parent, cap, "%s", actual) >= (int)cap)
        return false;
    snprintf(item, sizeof(item), "%s/removable", parent);
    if (!text_is(item, "0"))
        return false;
    snprintf(item, sizeof(item), "%s/device/type", parent);
    return text_is(item, "MMC");
}
static bool environment_writer(void) {
#ifdef Y2_UPDATE_TEST
    if (testroot)
        return true;
#endif
    /* The recovery initramfs marker and the kernel's own image identity agree. */
    char meta[160];
    return (text_is("/etc/y2linux/recovery-update", "1") &&
            readtext("/sys/firmware/y2_boot/metadata", meta, sizeof(meta)) &&
            strstr(meta, " recovery_image=1")) ||
           failure("Y2 recovery environment required");
}
static int disk_device(void) {
#ifdef Y2_UPDATE_TEST
    if (testroot)
        return openfile(AT_FDCWD, path("/disk.img"), O_RDWR, 0);
#endif
    DIR *dir = opendir("/sys/class/block");
    if (!dir) {
        failure("block inventory");
        return -1;
    }
    struct dirent *e;
    int result = -1;
    while ((e = readdir(dir))) {
        if (e->d_name[0] == '.' || strchr(e->d_name, '/'))
            continue;
        char link[320], actual[PATH_MAX], parent[PATH_MAX], item[PATH_MAX + 32], dev[320];
        snprintf(link, sizeof(link), "/sys/class/block/%s", e->d_name);
        if (!realpath(link, actual))
            continue;
        snprintf(item, sizeof(item), "%s/partition", link);
        if (!access(item, F_OK))
            continue;
        if (!internal_disk(actual, parent, sizeof(parent)))
            continue;
        snprintf(item, sizeof(item), "%s/size", parent);
        if (!text_is(item, "15203328"))
            continue;
        snprintf(dev, sizeof(dev), "/dev/%s", e->d_name);
        struct stat st;
        if (lstat(dev, &st) || !S_ISBLK(st.st_mode))
            continue;
        if (result >= 0) {
            close(result);
            closedir(dir);
            failure("ambiguous internal disk");
            return -1;
        }
        result = open(dev, O_RDWR | O_CLOEXEC | O_DIRECT | O_SYNC | O_NOFOLLOW);
        uint64_t bytes = 0;
        struct stat opened;
        if (result < 0 || ioctl(result, BLKGETSIZE64, &bytes) || bytes != DISK_SECTORS * 512 ||
            fstat(result, &opened) || opened.st_rdev != st.st_rdev) {
            if (result >= 0)
                close(result);
            closedir(dir);
            failure("internal disk identity");
            return -1;
        }
    }
    closedir(dir);
    if (result < 0)
        failure("internal disk unavailable");
    return result;
}
static bool region_read(int fd, uint64_t offset, unsigned char *buf, size_t n) {
    size_t got = 0;
    while (got < n) {
        ssize_t r = pread(fd, buf + got, n - got, (off_t)(offset + got));
        if (r < 0 && errno == EINTR)
            continue;
        if (r <= 0)
            return failure("disk read: %s", r < 0 ? strerror(errno) : "short");
        got += (size_t)r;
    }
    return true;
}
/* Full span write, cache flush and an independent read of the medium. */
static bool region_write(int fd, uint64_t offset, const unsigned char *buf, size_t n) {
    size_t done = 0;
    while (done < n) {
        ssize_t w = pwrite(fd, buf + done, n - done, (off_t)(offset + done));
        if (w < 0 && errno == EINTR)
            continue;
        if (w <= 0)
            return failure("disk write: %s", w < 0 ? strerror(errno) : "short");
        done += (size_t)w;
    }
    if (fsync(fd))
        return failure("disk flush: %s", strerror(errno));
    unsigned char *check = NULL;
    if (posix_memalign((void **)&check, 4096, n))
        return failure("readback allocation");
    bool ok = region_read(fd, offset, check, n) && (!memcmp(check, buf, n) || failure("disk readback mismatch"));
    free(check);
    return ok;
}
/* Android bootloader message: command[32] status[32] recovery[768]. LK
 * compares command with "boot-recovery"; recovery names our operation. */
static bool misc_request(int disk, const char *operation) {
    unsigned char *msg = NULL;
    if (posix_memalign((void **)&msg, 4096, MISC_BYTES))
        return failure("allocation");
    bool ok = region_read(disk, MISC_OFFSET, msg, MISC_BYTES);
    if (ok) {
        memset(msg, 0, 2048);
        if (operation) {
            strcpy((char *)msg, "boot-recovery");
            snprintf((char *)msg + 64, 768, "recovery\n--%s\n", operation);
        }
        ok = region_write(disk, MISC_OFFSET, msg, MISC_BYTES);
    }
    free(msg);
    return ok;
}
static bool misc_operation(int disk, char *operation, size_t cap) {
    unsigned char *msg = NULL;
    if (posix_memalign((void **)&msg, 4096, MISC_BYTES))
        return failure("allocation");
    bool ok = region_read(disk, MISC_OFFSET, msg, MISC_BYTES);
    operation[0] = 0;
    if (ok && !strncmp((char *)msg, "boot-recovery", 32)) {
        char field[769];
        memcpy(field, msg + 64, 768);
        field[768] = 0;
        if (!strcmp(field, "recovery\n--y2-update\n"))
            snprintf(operation, cap, "y2-update");
        else if (!strcmp(field, "recovery\n--y2-probe\n"))
            snprintf(operation, cap, "y2-probe");
        else
            snprintf(operation, cap, "other");
    } else if (ok && memchr(msg, 0, 32) && msg[0])
        snprintf(operation, cap, "unknown-command");
    free(msg);
    return ok;
}
/* LK must find a Y2 recovery image before we ask it to boot one. */
static bool recovery_installed(int disk, unsigned char *mem, const char *raw_sha256, uint64_t raw_bytes) {
    if (!region_read(disk, RECOVERY_OFFSET, mem, IMAGE_BYTES))
        return false;
    if (!boot_identity(mem, IMAGE_BYTES, RECOVERY))
        return failure("RECOVERY holds no Y2 recovery image");
    if (!raw_sha256)
        return true;
    unsigned char sum[32];
    crypto_hash_sha256(sum, mem, raw_bytes);
    if (!sha_match(sum, raw_sha256))
        return failure("RECOVERY differs from package");
    for (uint64_t i = raw_bytes; i < IMAGE_BYTES; i++)
        if (mem[i])
            return failure("RECOVERY differs from package");
    return true;
}
static int root_device(void) {
#ifdef Y2_UPDATE_TEST
    if (testroot)
        return openfile(AT_FDCWD, path("/root.img"), O_RDWR, 0);
#endif
    if (!environment_writer())
        return -1;
    DIR *dir = opendir("/sys/class/block");
    if (!dir) {
        failure("block inventory");
        return -1;
    }
    struct dirent *e;
    int result = -1;
    while ((e = readdir(dir))) {
        if (e->d_name[0] == '.' || strchr(e->d_name, '/'))
            continue;
        char link[320], actual[PATH_MAX], item[PATH_MAX + 32], parent[PATH_MAX], dev[320];
        snprintf(link, sizeof(link), "/sys/class/block/%s", e->d_name);
        if (!realpath(link, actual))
            continue;
        snprintf(item, sizeof(item), "%s/partition", link);
        if (access(item, R_OK))
            continue;
        snprintf(item, sizeof(item), "%s/start", link);
        if (!text_is(item, "166912"))
            continue;
        snprintf(item, sizeof(item), "%s/size", link);
        if (!text_is(item, "1679360"))
            continue;
        char *slash = strrchr(actual, '/');
        if (!slash)
            continue;
        *slash = 0;
        if (!internal_disk(actual, parent, sizeof(parent)))
            continue;
        snprintf(item, sizeof(item), "%s/size", parent);
        if (!text_is(item, "15203328") && !text_is(item, "15269888"))
            continue;
        snprintf(dev, sizeof(dev), "/dev/%s", e->d_name);
        struct stat st;
        if (lstat(dev, &st) || !S_ISBLK(st.st_mode))
            continue;
        snprintf(item, sizeof(item), "%u:%u", major(st.st_rdev), minor(st.st_rdev));
        FILE *mounts = fopen("/proc/self/mountinfo", "re");
        char line[8192];
        bool mounted = false;
        if (!mounts) {
            failure("mount inventory");
            goto bad;
        }
        while (fgets(line, sizeof(line), mounts)) {
            char device[64];
            if (sscanf(line, "%*u %*u %63s", device) == 1 && !strcmp(device, item))
                mounted = true;
        }
        bool mount_error = ferror(mounts);
        fclose(mounts);
        if (mounted || mount_error) {
            failure("root is mounted/unknown");
            goto bad;
        }
        if (result >= 0) {
            failure("ambiguous internal root");
            goto bad;
        }
        result = open(dev, O_RDWR | O_CLOEXEC | O_EXCL | O_NOFOLLOW);
        if (result < 0) {
            failure("exclusive root open: %s", strerror(errno));
            goto bad;
        }
        uint64_t device_bytes = 0;
        if (ioctl(result, BLKGETSIZE64, &device_bytes) || device_bytes != 1679360ULL * 512) {
            failure("root device capacity");
            goto bad;
        }
        struct stat opened;
        if (fstat(result, &opened) || opened.st_rdev != st.st_rdev) {
            failure("root identity changed");
            goto bad;
        }
    }
    closedir(dir);
    if (result < 0)
        failure("internal root geometry unavailable");
    return result;
bad:
    if (result >= 0)
        close(result);
    closedir(dir);
    return -1;
}
static bool state(json_object *j, const char *value, const char *why) {
    setstr(j, "state", value);
    setstr(j, "failure", why ? why : "");
    return save("state.json", j);
}
static void boot_id(char *buf, size_t n) {
    if (!readtext("/proc/sys/kernel/random/boot_id", buf, n))
        buf[0] = 0;
}
/* Compressed copy of an image (root extent or a 16 MiB boot span), verified by
 * decompression before anything is overwritten. */
/* Compressed copy of an image (root extent or a 16 MiB boot span). The record
 * keeps the SHA-256 of the compressed file and the CRC-32 of the raw image; the
 * file is read back from the medium and hashed before anything is overwritten. */
static bool backup_stream(int source_fd, const unsigned char *source_mem, uint64_t bytes,
                          const char *name, json_object *record) {
    char tmp[64];
    snprintf(tmp, sizeof(tmp), "%s.tmp", name);
    if (!enough(basefd, CHUNK))
        return false;
    unlinkat(basefd, tmp, 0);
    int out = openfile(basefd, tmp, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (out < 0)
        return false;
    z_stream z = {0};
    bool ok = false;
    /* Level 1: the image is mostly free blocks; speed matters on battery. */
    if (deflateInit2(&z, 1, Z_DEFLATED, 15 + 16, 8, Z_DEFAULT_STRATEGY) != Z_OK) {
        failure("backup gzip init");
        close(out);
        return false;
    }
    static unsigned char in[CHUNK], encoded[CHUNK];
    unsigned char gzsum[32];
    crypto_hash_sha256_state ch;
    crypto_hash_sha256_init(&ch);
    uLong rawcrc = crc32(0L, Z_NULL, 0);
    uint64_t left = bytes, gzbytes = 0;
    if (source_fd >= 0 && !drop_cache(source_fd))
        goto done;
    while (left) {
        size_t count = left < sizeof(in) ? (size_t)left : sizeof(in);
        const unsigned char *data = in;
        if (source_mem)
            data = source_mem + (bytes - left);
        else {
            ssize_t got = pread(source_fd, in, count, (off_t)(bytes - left));
            if (got < 0 && errno == EINTR)
                continue;
            if (got <= 0) {
                failure("backup read");
                goto done;
            }
            count = (size_t)got;
        }
        left -= count;
        rawcrc = crc32(rawcrc, data, (uInt)count);
        z.next_in = (unsigned char *)data;
        z.avail_in = (uInt)count;
        int rc;
        do {
            z.next_out = encoded;
            z.avail_out = sizeof(encoded);
            rc = deflate(&z, left ? Z_NO_FLUSH : Z_FINISH);
            if (rc != Z_OK && rc != Z_STREAM_END) {
                failure("backup compression");
                goto done;
            }
            size_t made = sizeof(encoded) - z.avail_out;
            if (!enough(basefd, made) || !writeall(out, encoded, made))
                goto done;
            crypto_hash_sha256_update(&ch, encoded, made);
            gzbytes += made;
        } while (z.avail_in || z.avail_out == 0 || (!left && rc != Z_STREAM_END));
        progress_bytes(bytes - left);
    }
    if (fsync(out) || !drop_cache(out)) {
        failure("backup fsync");
        goto done;
    }
    crypto_hash_sha256_final(&ch, gzsum);
    setnum(record, "raw_bytes", (int64_t)bytes);
    setnum(record, "bytes", (int64_t)gzbytes);
    setnum(record, "raw_crc32", (int64_t)rawcrc);
    setstr(record, "sha256", hash_string(gzsum));
    ok = file_digest(basefd, tmp, record) &&
         renameat(basefd, tmp, basefd, name) == 0 && fsync(basefd) == 0;
done:
    deflateEnd(&z);
    close(out);
    if (!ok && !error_text[0])
        failure("backup failed");
    return ok;
}
static bool backup(int root, int disk, unsigned char *mem, json_object *journal) {
    unsigned char header[4096];
    if (pread(root, header, sizeof(header), 0) != sizeof(header))
        return failure("old root header");
    uint64_t bytes = root_bytes(header);
    if (!bytes)
        return failure("old root identity/extent");
    /* OTA-46: the rollback copies of the release being replaced go first, so
     * the new copies fit where they were (the platform counts them as free).
     * A failed backup ends in Failed, which never restores. */
    json_object_object_del(journal, "backup");
    unlinkat(basefd, "previous.ext4.gz", 0);
    unlinkat(basefd, "previous-bootimg.gz", 0);
    if (!state(journal, "BackingUp", NULL))
        return false;
    json_object *saved = json_object_new_object(), *r = json_object_new_object(),
                *b = json_object_new_object();
    json_object_object_add(saved, "root", r);
    json_object_object_add(saved, "bootimg", b);
    progress_span("backup", 3, 37, bytes);
    bool ok = backup_stream(root, NULL, bytes, "previous.ext4.gz", r) &&
              region_read(disk, BOOTIMG_OFFSET, mem, IMAGE_BYTES);
    if (ok) {
        progress_span("backup", 40, 2, IMAGE_BYTES);
        ok = backup_stream(-1, mem, IMAGE_BYTES, "previous-bootimg.gz", b);
    }
    if (!ok) {
        json_object_put(saved);
        return false;
    }
    json_object_object_add(journal, "backup", saved);
    return save("state.json", journal);
}
/* Backups from before OTA-38 carry only a raw SHA-256: check them that way. */
static bool legacy_record(json_object *r) { return !field(r, "raw_crc32"); }
static bool restore(int root, int disk, unsigned char *mem, json_object *j, const char *reason) {
    json_object *saved = field(j, "backup"), *r = field(saved, "root"), *b = field(saved, "bootimg");
    if (!r || !b)
        return failure("no verified backup");
    progress(2, "restore");
    int rf = openfile(basefd, "previous.ext4.gz", O_RDONLY, 0);
    int bf = rf >= 0 ? openfile(basefd, "previous-bootimg.gz", O_RDONLY, 0) : -1;
    unsigned rflags = STREAM_SKIP_SAME | (legacy_record(r) ? STREAM_RAW_SHA : 0);
    uint32_t crc = 0;
    /* Both backups must be intact before the first write. */
    bool ok = rf >= 0 && bf >= 0 && file_digest(basefd, "previous.ext4.gz", r) &&
              stream_image(bf, -1, mem, b, REGION, legacy_record(b) ? STREAM_RAW_SHA : 0, NULL) &&
              state(j, "RollingBack", reason);
    if (ok) {
        progress_span("restore", 5, 75, (uint64_t)num(r, "raw_bytes"));
        ok = stream_image(rf, root, NULL, r, ROOT, rflags, &crc) && fsync(root) == 0;
    }
    if (ok) {
        progress_span("check", 80, 15, (uint64_t)num(r, "raw_bytes"));
        ok = legacy_record(r) ? file_hash(root, (uint64_t)num(r, "raw_bytes"), str(r, "raw_sha256"))
                              : file_crc(root, (uint64_t)num(r, "raw_bytes"), crc);
    }
    if (ok) {
        progress(96, "restore");
        ok = region_write(disk, BOOTIMG_OFFSET, mem, IMAGE_BYTES);
    }
    if (rf >= 0)
        close(rf);
    if (bf >= 0)
        close(bf);
    if (!ok) {
        char why[192];
        snprintf(why, sizeof(why), "%s", error_text);
        state(j, "RescueRequired", why);
        return false;
    }
    json_object *water = load(basefd, "accepted.json");
    if (!water) {
        if (errno != ENOENT)
            return failure("accepted sequence unreadable on rollback");
        water = json_object_new_object();
        setnum(water, "sequence", 0);
    }
    setnum(water, "current_sequence", num(j, "previous_sequence") > 0 ? num(j, "previous_sequence") : 0);
    ok = save("accepted.json", water) && state(j, "RolledBack", reason) && misc_request(disk, NULL);
    json_object_put(water);
    progress(100, "restored");
    return ok;
}
static bool battery_safe(void) {
#ifdef Y2_UPDATE_TEST
    if (testroot)
        return text_is("/external-power", "1");
#endif
    DIR *d = opendir("/sys/class/power_supply");
    if (!d)
        return false;
    struct dirent *e;
    bool online = false;
    char p[PATH_MAX];
    while ((e = readdir(d))) {
        if (e->d_name[0] == '.')
            continue;
        snprintf(p, sizeof(p), "/sys/class/power_supply/%s/type", e->d_name);
        if (!text_is(p, "USB") && !text_is(p, "Mains"))
            continue;
        snprintf(p, sizeof(p), "/sys/class/power_supply/%s/online", e->d_name);
        if (text_is(p, "1"))
            online = true;
    }
    closedir(d);
    /* The owner gate (charger or 50 %) runs before power-off. This is the
     * installer's own floor: charger or a battery that is clearly not empty. */
    char volts[32];
    long uv = readtext("/sys/class/power_supply/BAT0/voltage_now", volts, sizeof(volts))
                  ? strtol(volts, NULL, 10) : 0;
    return online || uv >= 3700000;
}
static void outcome(json_object *j, const char *what) { setstr(j, "outcome", what); }
/* The installer that runs from RECOVERY. MISC stays "boot-recovery" until the
 * outcome is verified and durable; every interruption returns here. */
static bool recover(json_object *j) {
    char current[64], operation[32];
    boot_id(current, sizeof(current));
    if (!*current)
        return failure("boot identity missing");
    if (!recovery_env || !environment_writer())
        return failure("Y2 recovery environment required");
    int disk = disk_device();
    if (disk < 0)
        return false;
    unsigned char *mem = image_buffer();
    int root = -1;
    bool ok = false;
    const char *s = str(j, "state");
    if (!mem || !misc_operation(disk, operation, sizeof(operation)))
        goto done;
    if (!strcmp(operation, "y2-probe")) {
        json_object *probe = json_object_new_object();
        char meta[160];
        setstr(probe, "boot_id", current);
        setstr(probe, "metadata", readtext("/sys/firmware/y2_boot/metadata", meta, sizeof(meta)) ? meta : "");
        setstr(probe, "result", "recovery_started");
        ok = save("recovery-probe.json", probe) && misc_request(disk, NULL);
        json_object_put(probe);
        outcome(j, "probe");
        progress(100, "probe");
        goto done;
    }
    if (!strcmp(s, "Idle") || !strcmp(s, "Acknowledged") || !strcmp(s, "RolledBack") ||
        !strcmp(s, "Failed") || !strcmp(s, "PendingHealth")) {
        /* Nothing unfinished: a stale request or a completed install whose
         * clearing was interrupted. Clear it and start the system normally. */
        ok = misc_request(disk, NULL);
        outcome(j, !strcmp(s, "PendingHealth") ? "installed" : "nothing");
        progress(100, "done");
        goto done;
    }
    if (!strcmp(s, "RescueRequired")) {
        failure("manual rescue required; no automatic retry");
        goto done;
    }
    if (!battery_safe()) {
        failure("connect the charger to continue");
        outcome(j, "needs_power");
        goto done;
    }
    if (!crypto_ready())
        goto done;
    root = root_device();
    if (root < 0)
        goto done;
    if (!strcmp(s, "Installing") || !strcmp(s, "RollingBack") || !strcmp(s, "RollbackPending")) {
        ok = restore(root, disk, mem, j,
                     !strcmp(s, "RollbackPending") && *str(j, "failure") ? str(j, "failure")
                                                                          : "interrupted update");
        outcome(j, ok ? "rolled_back" : "rescue_required");
        goto done;
    }
    if (strcmp(s, "Queued") && strcmp(s, "BackingUp")) {
        failure("unknown update state");
        goto done;
    }
    int pkg = openat(basefd, "pending", O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    json_object *m = pkg >= 0 ? verify(pkg, 2, num(j, "previous_sequence")) : NULL;
    if (!m || strcmp(str(m, "y2linux_commit"), str(j, "y2linux_commit")) ||
        num(m, "sequence") != num(j, "sequence") ||
        strcmp(str(m, "_manifest_sha256"), str(j, "manifest_sha256"))) {
        char why[192];
        snprintf(why, sizeof(why), "%s", m ? "queued identity changed" : pkg < 0 ? "pending package missing" : error_text);
        if (m)
            json_object_put(m);
        if (pkg >= 0)
            close(pkg);
        ok = state(j, "Failed", why) && misc_request(disk, NULL);
        outcome(j, "failed_unchanged");
        goto done;
    }
    if (!backup(root, disk, mem, j)) {
        char why[192];
        snprintf(why, sizeof(why), "%s", error_text);
        ok = state(j, "Failed", why) && misc_request(disk, NULL);
        outcome(j, "failed_unchanged");
        json_object_put(m);
        close(pkg);
        goto done;
    }
    json_object *rp = payload(m, ROOT), *bp = payload(m, BOOT);
    int rf = openfile(pkg, payload_file[ROOT], O_RDONLY, 0);
    int bf = rf >= 0 ? openfile(pkg, payload_file[BOOT], O_RDONLY, 0) : -1;
    /* Decode and verify the new BOOTIMG before the first write of anything. */
    uint32_t crc = 0;
    ok = bf >= 0 && stream_image(bf, -1, mem, bp, BOOT, 0, NULL) && state(j, "Installing", NULL);
    if (ok) {
        progress_span("system", 42, 38, (uint64_t)num(rp, "raw_bytes"));
        stream_written = 0;
        ok = stream_image(rf, root, NULL, rp, ROOT, STREAM_INJECT | STREAM_SKIP_SAME, &crc) &&
             fsync(root) == 0;
        if (ok)
            setnum(j, "root_bytes_written", (int64_t)stream_written);
    }
#ifdef Y2_UPDATE_TEST
    if (ok && getenv("Y2_TEST_FAULT") && !strcmp(getenv("Y2_TEST_FAULT"), "readback")) {
        unsigned char b = 0xff;
        if (pwrite(root, &b, 1, 0) != 1)
            ok = false;
    }
#endif
    if (ok) {
        progress_span("check", 80, 16, (uint64_t)num(rp, "raw_bytes"));
        ok = file_crc(root, (uint64_t)num(rp, "raw_bytes"), crc);
    }
#ifdef Y2_UPDATE_TEST
    if (ok && getenv("Y2_TEST_FAULT") && !strcmp(getenv("Y2_TEST_FAULT"), "boot_interrupt"))
        _exit(92);
#endif
    if (ok) {
        progress(96, "boot");
        ok = region_write(disk, BOOTIMG_OFFSET, mem, IMAGE_BYTES);
    }
    if (rf >= 0)
        close(rf);
    if (bf >= 0)
        close(bf);
    if (ok) {
        setstr(j, "boot_id", current);
        json_object_object_del(j, "health_boots");
        ok = state(j, "PendingHealth", NULL) && misc_request(disk, NULL);
        outcome(j, "installed");
        progress(100, "installed");
    } else {
        char why[192];
        snprintf(why, sizeof(why), "%s", error_text);
        ok = restore(root, disk, mem, j, why);
        outcome(j, ok ? "rolled_back" : "rescue_required");
    }
    json_object_put(m);
    close(pkg);
done:
    if (root >= 0)
        close(root);
    free(mem);
    close(disk);
    return ok;
}
/* Normal system: put the package's recovery image in place if it is newer,
 * prove that RECOVERY holds a Y2 recovery image, then ask LK for it. */
static bool prepare(json_object *j, const char *operation) {
    const char *s = str(j, "state");
    if (!strcmp(operation, "y2-update") && strcmp(s, "Queued") && strcmp(s, "RollbackPending") &&
        strcmp(s, "BackingUp") && strcmp(s, "Installing") && strcmp(s, "RollingBack"))
        return failure("nothing to install or restore");
    if (recovery_env)
        return failure("recovery cannot request itself");
    int disk = disk_device();
    if (disk < 0)
        return false;
    unsigned char *mem = image_buffer();
    bool ok = mem != NULL;
    if (ok && !strcmp(s, "Queued") && !strcmp(operation, "y2-update")) {
        int pkg = openat(basefd, "pending", O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
        json_object *m = pkg >= 0 ? verify(pkg, 0, -1) : NULL;
        ok = m && !strcmp(str(m, "_manifest_sha256"), str(j, "manifest_sha256"));
        if (!ok && m)
            failure("queued identity changed");
        json_object *rp = ok ? payload(m, RECOVERY) : NULL;
        if (ok && rp && !recovery_installed(disk, mem, str(rp, "raw_sha256"), (uint64_t)num(rp, "raw_bytes"))) {
            /* Write the new installer while this kernel's BOOTIMG stays intact. */
            ok = check_payload(pkg, m, RECOVERY, mem) &&
                 region_write(disk, RECOVERY_OFFSET, mem, IMAGE_BYTES);
            if (ok)
                setstr(j, "recovery_installed", str(rp, "raw_sha256"));
            ok = ok && save("state.json", j);
        }
        if (m)
            json_object_put(m);
        if (pkg >= 0)
            close(pkg);
    }
    ok = ok && recovery_installed(disk, mem, NULL, 0) && misc_request(disk, operation);
    if (ok && !strcmp(operation, "y2-update")) {
        setnum(j, "recovery_requests", num(j, "recovery_requests") > 0 ? num(j, "recovery_requests") + 1 : 1);
        ok = save("state.json", j);
    }
    free(mem);
    close(disk);
    return ok;
}
/* BOOTIMG rescue, before the root is mounted. Exit 10: boot normally;
 * 20: recovery was requested, power off and tell the owner; 11: stay in rescue. */
static int boot_check(json_object *j) {
    char current[64];
    boot_id(current, sizeof(current));
    const char *s = str(j, "state");
    int disk = -1;
    int code = 10;
    if (!strcmp(s, "Idle") || !strcmp(s, "Acknowledged") || !strcmp(s, "RolledBack") ||
        !strcmp(s, "Failed"))
        return 10;
    if (!strcmp(s, "RescueRequired"))
        return 11;
    if (!strcmp(s, "Queued")) {
        /* Nothing was written. If a request is still set LK did not honour it;
         * never loop: give up the update and boot the intact system. */
        char operation[32];
        disk = disk_device();
        if (disk < 0)
            return 11;
        if (misc_operation(disk, operation, sizeof(operation)) && !strcmp(operation, "y2-update")) {
            if (!misc_request(disk, NULL) || !state(j, "Failed", "recovery did not start"))
                code = 11;
        }
        close(disk);
        return code;
    }
    if (!strcmp(s, "PendingHealth")) {
        int64_t boots = num(j, "health_boots");
        if (boots < 0)
            boots = 0;
        if (boots < HEALTH_BOOTS) {
            setnum(j, "health_boots", boots + 1);
            return save("state.json", j) ? 10 : 11;
        }
        if (!state(j, "RollbackPending", "new system did not confirm health"))
            return 11;
        s = str(j, "state");
    }
    /* RollbackPending, or an interrupted install whose request was lost. */
    if (num(j, "recovery_requests") >= 3) {
        state(j, "RescueRequired", "recovery was requested three times");
        return 11;
    }
    if (!prepare(j, "y2-update"))
        return 11;
    return 20;
}
static json_object *initial(void) {
    json_object *j = json_object_new_object();
    setnum(j, "schema", 2);
    setstr(j, "state", "Idle");
    return j;
}
static bool terminal(const char *s) {
    return !strcmp(s, "Idle") || !strcmp(s, "Acknowledged") || !strcmp(s, "RolledBack") ||
           !strcmp(s, "Failed");
}
int main(int argc, char **argv) {
#ifdef Y2_UPDATE_TEST
    testroot = getenv("Y2_TEST_ROOT");
    if (!testroot || testroot[0] != '/') {
        fputs("test root required\n", stderr);
        return 2;
    }
    recovery_env = getenv("Y2_TEST_RECOVERY") != NULL;
#endif
    if (argc < 2 || argc > 3)
        return 2;
    bool offline = !strcmp(argv[1], "recovery") || !strcmp(argv[1], "boot-check") ||
                   !strcmp(argv[1], "boot-needed");
#ifndef Y2_UPDATE_TEST
    recovery_env = !strcmp(argv[1], "recovery");
#endif
    if (recovery_env)
        progress_name = "/run/y2/recovery-progress";
    else if (!strcmp(argv[1], "check") || !strcmp(argv[1], "queue"))
        progress_name = "/run/y2/update-check-progress";
    const char *base = path(offline ? "/newdata/updates" : "/data/updates");
    basefd = open(base, O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (basefd < 0) {
        failure("update state directory unavailable");
        goto output;
    }
    struct stat bst;
    if (fstat(basefd, &bst) || (bst.st_mode & 0077) || bst.st_uid != geteuid()) {
        failure("update state permissions");
        goto output;
    }
    if (!strcmp(argv[1], "boot-needed") && argc == 2) {
        /* Read-only, on the rescue's read-only data mount: 10 = finished
         * history, nothing to do; 0 = run boot-check on a writable mount. */
        json_object *j = load(basefd, "state.json");
        int code = j && num(j, "schema") == 2 && terminal(str(j, "state")) ? 10 : !j && errno == ENOENT ? 10 : 0;
        if (j)
            json_object_put(j);
        close(basefd);
        return code;
    }
    int lock = openfile(basefd, ".lock", O_RDWR | O_CREAT, 0600);
    if (lock < 0 || flock(lock, LOCK_EX | LOCK_NB)) {
        failure("update busy");
        goto output;
    }
    bool ok = false;
    json_object *j = load(basefd, "state.json");
    if (!j) {
        if (errno == ENOENT) {
            j = initial();
            error_text[0] = 0;
        } else {
            failure("update journal unreadable");
            goto output;
        }
    }
    if (num(j, "schema") != 2 || !*str(j, "state")) {
        json_object_put(j);
        failure("update journal schema");
        goto output;
    }
    if (!strcmp(argv[1], "boot-check") && argc == 2) {
        int code = boot_check(j);
        setnum(j, "boot_check", code);
        if (code == 11 && error_text[0])
            setstr(j, "boot_check_failure", error_text);
        puts(json_object_to_json_string_ext(j, JSON_C_TO_STRING_PLAIN));
        json_object_put(j);
        close(basefd);
        return code;
    }
    if ((!strcmp(argv[1], "check") || !strcmp(argv[1], "check-manifest")) && argc == 3) {
        int pkg = open(path(argv[2]), O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
        json_object *m = pkg >= 0 ? verify(pkg, strcmp(argv[1], "check-manifest") ? 1 : 0, -1) : NULL;
        if (pkg >= 0)
            close(pkg);
        if (m) {
            puts(json_object_to_json_string_ext(m, JSON_C_TO_STRING_PLAIN));
            json_object_put(m);
            json_object_put(j);
            return 0;
        }
        if (!error_text[0])
            failure("package unavailable");
    } else if (!strcmp(argv[1], "queue") && argc == 2) {
        if (!terminal(str(j, "state")))
            failure("update already pending");
        else {
            int pkg = openat(basefd, "pending", O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
            json_object *m = pkg >= 0 ? verify(pkg, 1, -1) : NULL;
            if (pkg >= 0)
                close(pkg);
            if (m) {
                /* A new install takes fresh backups of whatever is running. */
                json_object_put(j);
                j = initial();
                setnum(j, "sequence", num(m, "sequence"));
                setnum(j, "previous_sequence", num(m, "_previous_sequence"));
                setstr(j, "manifest_sha256", str(m, "_manifest_sha256"));
                setstr(j, "y2linux_commit", str(m, "y2linux_commit"));
                setstr(j, "release_version", str(m, "release_version"));
                json_object_object_add(j, "rollback_allowed",
                                       json_object_new_boolean(yes(m, "rollback_allowed")));
                ok = state(j, "Queued", NULL);
                json_object_put(m);
            }
        }
    } else if (!strcmp(argv[1], "recovery") && argc == 2) {
        ok = recover(j);
    } else if (!strcmp(argv[1], "prepare") && argc == 2) {
        ok = prepare(j, "y2-update");
    } else if (!strcmp(argv[1], "probe") && argc == 2) {
        if (!terminal(str(j, "state")))
            failure("an update is in progress");
        else
            ok = prepare(j, "y2-probe");
    } else if (!strcmp(argv[1], "misc") && argc == 2) {
        int disk = recovery_env ? -1 : disk_device();
        unsigned char *mem = disk >= 0 ? image_buffer() : NULL;
        char operation[32];
        if (mem && misc_operation(disk, operation, sizeof(operation))) {
            setstr(j, "misc_request", *operation ? operation : "none");
            json_object_object_add(j, "recovery_image_valid",
                                   json_object_new_boolean(recovery_installed(disk, mem, NULL, 0)));
            error_text[0] = 0;
            ok = true;
        }
        free(mem);
        if (disk >= 0)
            close(disk);
    } else if (!strcmp(argv[1], "status") && argc == 2)
        ok = true;
    else if (!strcmp(argv[1], "ack") && argc == 2) {
        char current[64];
        boot_id(current, sizeof(current));
        json_object *versions = load(AT_FDCWD, path("/etc/y2linux/versions.json"));
        json_object *ready = load(AT_FDCWD, path("/run/y2/application-ready.json"));
        if (strcmp(str(j, "state"), "PendingHealth") || !versions ||
            strcmp(str(versions, "build_git_commit"), str(j, "y2linux_commit")) || !ready ||
            strcmp(str(ready, "boot_id"), current))
            failure("boot-health acknowledgement prerequisites");
        else {
            json_object *water = load(basefd, "accepted.json");
            if (!water && errno != ENOENT) {
                failure("accepted sequence unreadable");
                goto ack_done;
            }
            if (!water)
                water = json_object_new_object();
            int64_t highest = num(water, "sequence");
            setnum(water, "sequence", highest > num(j, "sequence") ? highest : num(j, "sequence"));
            setnum(water, "current_sequence", num(j, "sequence"));
            setstr(j, "boot_id", current);
            ok = save("accepted.json", water) && state(j, "Acknowledged", NULL);
            json_object_put(water);
        }
    ack_done:
        if (versions)
            json_object_put(versions);
        if (ready)
            json_object_put(ready);
    } else if (!strcmp(argv[1], "cancel") && argc == 2) {
        if (strcmp(str(j, "state"), "Queued"))
            failure("only queued updates can be cancelled");
        else
            ok = state(j, "Failed", "owner cancelled before installation");
    } else if (!strcmp(argv[1], "rollback") && argc == 2) {
        json_object *saved = field(j, "backup");
        if (!field(saved, "root") || !field(saved, "bootimg") ||
            !(yes(j, "rollback_allowed") || !strcmp(str(j, "state"), "PendingHealth")) ||
            !(!strcmp(str(j, "state"), "Acknowledged") || !strcmp(str(j, "state"), "PendingHealth")))
            failure("rollback policy/backup unavailable");
        else
            ok = state(j, "RollbackPending", "owner/health requested restore");
    } else
        failure("unknown command");
    if (ok) {
        error_text[0] = 0;
        puts(json_object_to_json_string_ext(j, JSON_C_TO_STRING_PLAIN));
        json_object_put(j);
        close(basefd);
        return 0;
    }
    if (j && field(j, "outcome")) {
        setstr(j, "error", error_text);
        puts(json_object_to_json_string_ext(j, JSON_C_TO_STRING_PLAIN));
        json_object_put(j);
        close(basefd);
        return 1;
    }
    if (j)
        json_object_put(j);
output: {
    json_object *e = json_object_new_object();
    setstr(e, "state", "Failed");
    setstr(e, "failure", *error_text ? error_text : "operation failed");
    puts(json_object_to_json_string_ext(e, JSON_C_TO_STRING_PLAIN));
    json_object_put(e);
}
    if (basefd >= 0)
        close(basefd);
    return 1;
}
