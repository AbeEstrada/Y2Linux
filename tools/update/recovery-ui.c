/* SPDX-License-Identifier: GPL-2.0-only
 * Y2 recovery screen. One CPU-mapped dumb buffer, no GPU, no input. It shows
 * what the recovery installer is doing:
 *   /run/y2/recovery-screen    title line, then up to five body lines
 *   /run/y2/recovery-progress  "<percent> <step>" written by y2-update-core
 * and redraws only when either file changes. The installer never depends on
 * this process: a missing panel just means an update without a picture.
 */
#define _GNU_SOURCE
#include <fcntl.h>
#include <poll.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <drm_fourcc.h>
#include <xf86drm.h>
#include <xf86drmMode.h>
#include "font-ter16x32.h"

/* Reborn's boot palette (tools/graphics/reborn-splash-mark.h). */
#define BG 0x06070au
#define TEXT 0xf6f6f8u
#define DIM 0x9a9ba3u
#define TRACK 0x2d2e30u
#define FILL 0xf6f6f8u
#define LINES 6
#define COLUMNS 28

typedef struct {
    int fd;
    uint32_t connector, crtc, fb, handle, pitch;
    unsigned width, height;
    size_t size;
    uint8_t *pixels;
    drmModeModeInfo mode;
} Display;

static int display_open(Display *d) {
    *d = (Display){.fd = -1};
    for (unsigned i = 0; i < 16 && d->fd < 0; i++) {
        char path[40];
        snprintf(path, sizeof(path), "/dev/dri/card%u", i);
        int fd = open(path, O_RDWR | O_CLOEXEC);
        if (fd < 0)
            continue;
        drmVersionPtr v = drmGetVersion(fd);
        bool match = v && v->name && !strcmp(v->name, "mediatek");
        drmFreeVersion(v);
        if (match)
            d->fd = fd;
        else
            close(fd);
    }
    if (d->fd < 0 || drmSetMaster(d->fd))
        return -1;
    drmModeRes *r = drmModeGetResources(d->fd);
    if (!r)
        return -1;
    for (int i = 0; i < r->count_connectors && !d->connector; i++) {
        drmModeConnector *c = drmModeGetConnector(d->fd, r->connectors[i]);
        if (c && c->connection == DRM_MODE_CONNECTED && c->count_modes) {
            d->connector = c->connector_id;
            d->mode = c->modes[0];
            for (int k = 0; k < c->count_modes; k++)
                if (c->modes[k].type & DRM_MODE_TYPE_PREFERRED) {
                    d->mode = c->modes[k];
                    break;
                }
            for (int k = 0; k < c->count_encoders && !d->crtc; k++) {
                drmModeEncoder *e = drmModeGetEncoder(d->fd, c->encoders[k]);
                if (e) {
                    d->crtc = e->crtc_id;
                    for (int j = 0; !d->crtc && j < r->count_crtcs; j++)
                        if (e->possible_crtcs & (1U << j))
                            d->crtc = r->crtcs[j];
                    drmModeFreeEncoder(e);
                }
            }
        }
        drmModeFreeConnector(c);
    }
    drmModeFreeResources(r);
    d->width = d->mode.hdisplay;
    d->height = d->mode.vdisplay;
    if (!d->crtc || d->width < 480 || d->width > 1024 || d->height < 360 || d->height > 1024)
        return -1;
    struct drm_mode_create_dumb create = {.width = d->width, .height = d->height, .bpp = 32};
    if (drmIoctl(d->fd, DRM_IOCTL_MODE_CREATE_DUMB, &create))
        return -1;
    d->handle = create.handle;
    d->pitch = create.pitch;
    d->size = create.size;
    if (d->pitch < d->width * 4 || d->size < (uint64_t)d->pitch * d->height || d->size > 8 * 1024 * 1024)
        return -1;
    uint32_t handles[4] = {d->handle}, pitches[4] = {d->pitch}, offsets[4] = {0};
    if (drmModeAddFB2(d->fd, d->width, d->height, DRM_FORMAT_XRGB8888, handles, pitches, offsets, &d->fb, 0))
        return -1;
    struct drm_mode_map_dumb map = {.handle = d->handle};
    if (drmIoctl(d->fd, DRM_IOCTL_MODE_MAP_DUMB, &map))
        return -1;
    d->pixels = mmap(NULL, d->size, PROT_READ | PROT_WRITE, MAP_SHARED, d->fd, map.offset);
    if (d->pixels == MAP_FAILED) {
        d->pixels = NULL;
        return -1;
    }
    return 0;
}
static void light(const char *value) {
    int fd = open("/sys/class/backlight/y2-backlight/bl_power", O_WRONLY | O_CLOEXEC);
    if (fd < 0)
        return;
    if (write(fd, value, 2) != 2) {
    }
    close(fd);
}
/* As the boot splash: keep the light off across the first modeset (LK's
 * picture would show noise), then always turn it back on. */
static int show(Display *d) {
    light("4\n");
    int ret = drmModeSetCrtc(d->fd, d->crtc, d->fb, 0, 0, &d->connector, 1, &d->mode);
    if (!ret) {
        drmVBlank vbl = {.request = {.type = DRM_VBLANK_RELATIVE, .sequence = 2}};
        if (drmWaitVBlank(d->fd, &vbl))
            poll(NULL, 0, 40);
    }
    light("0\n");
    return ret;
}
static void rect(Display *d, unsigned x, unsigned y, unsigned w, unsigned h, uint32_t rgb) {
    if (x + w > d->width || y + h > d->height)
        return;
    for (unsigned row = y; row < y + h; row++) {
        uint32_t *p = (uint32_t *)(d->pixels + (size_t)row * d->pitch) + x;
        for (unsigned col = 0; col < w; col++)
            p[col] = rgb;
    }
}
static void text(Display *d, unsigned x, unsigned y, const char *s, uint32_t rgb) {
    for (; *s && x + FONT_W <= d->width; s++, x += FONT_W) {
        unsigned char c = (unsigned char)*s;
        if (c < FONT_FIRST || c >= FONT_FIRST + FONT_COUNT)
            c = '?';
        const unsigned char *g = font_ter16x32 + (c - FONT_FIRST) * 64;
        for (unsigned row = 0; row < FONT_H && y + row < d->height; row++) {
            uint32_t *p = (uint32_t *)(d->pixels + (size_t)(y + row) * d->pitch) + x;
            unsigned bits = (unsigned)g[row * 2] << 8 | g[row * 2 + 1];
            for (unsigned col = 0; col < FONT_W; col++)
                if (bits & (0x8000u >> col))
                    p[col] = rgb;
        }
    }
}
static void centered(Display *d, unsigned oy, unsigned y, const char *s, uint32_t rgb) {
    size_t n = strlen(s);
    if (n > COLUMNS)
        n = COLUMNS;
    char line[COLUMNS + 1];
    memcpy(line, s, n);
    line[n] = 0;
    text(d, (d->width - (unsigned)n * FONT_W) / 2, oy + y, line, rgb);
}
static bool slurp(const char *path, char *buf, size_t cap) {
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0)
        return false;
    ssize_t n = read(fd, buf, cap - 1);
    close(fd);
    if (n < 0)
        return false;
    buf[n] = 0;
    return true;
}
/* Installer steps (y2-update-core progress()) in words. */
static const char *step_text(const char *step) {
    static const char *const map[][2] = {
        {"verify", "Checking the update"},      {"backup", "Saving the current system"},
        {"system", "Installing the system"},    {"check", "Verifying the system"},
        {"boot", "Installing the kernel"},      {"installed", "Update installed"},
        {"restore", "Restoring the old system"}, {"restored", "Old system restored"},
        {"probe", "Recovery works"},            {"done", "Nothing to install"},
    };
    for (size_t i = 0; i < sizeof(map) / sizeof(map[0]); i++)
        if (!strcmp(map[i][0], step))
            return map[i][1];
    return "";
}
static void draw(Display *d, const char *screen, const char *progress) {
    unsigned ox = (d->width - 480) / 2, oy = (d->height - 360) / 2;
    rect(d, 0, 0, d->width, d->height, BG);
    char copy[1024];
    snprintf(copy, sizeof(copy), "%s", screen);
    /* Blank lines are spacing, so split exactly at each newline. */
    char *line = copy;
    for (unsigned i = 0; *line && i < LINES; i++) {
        char *end = strchr(line, '\n');
        if (end)
            *end = 0;
        centered(d, oy, i ? 72 + i * 36 : 28, line, i ? DIM : TEXT);
        if (!end)
            break;
        line = end + 1;
    }
    unsigned percent = 0;
    char step[32] = {0};
    if (sscanf(progress, "%u %31s", &percent, step) >= 1) {
        if (percent > 100)
            percent = 100;
        const char *words = step_text(step);
        if (*words)
            centered(d, oy, 252, words, TEXT);
        rect(d, ox + 40, oy + 300, 400, 6, TRACK);
        rect(d, ox + 40, oy + 300, 4 * percent, 6, FILL);
    }
}
int main(void) {
    Display d;
    bool ready = false;
    /* The display module loads in the background (y2-platform-start). */
    for (unsigned attempt = 0; attempt < 300 && !ready; attempt++) {
        if (!display_open(&d))
            ready = true;
        else {
            if (d.fd >= 0)
                close(d.fd);
            poll(NULL, 0, 100);
        }
    }
    if (!ready)
        return 1;
    char screen[1024] = {0}, progress[64] = {0}, last_screen[1024] = {1}, last_progress[64] = {1};
    bool shown = false;
    for (;;) {
        if (!slurp("/run/y2/recovery-screen", screen, sizeof(screen)))
            screen[0] = 0;
        if (!slurp("/run/y2/recovery-progress", progress, sizeof(progress)))
            progress[0] = 0;
        if (strcmp(screen, last_screen) || strcmp(progress, last_progress)) {
            draw(&d, screen, progress);
            if (!shown)
                shown = !show(&d);
            else
                drmModeDirtyFB(d.fd, d.fb, NULL, 0);
            memcpy(last_screen, screen, sizeof(screen));
            memcpy(last_progress, progress, sizeof(progress));
        }
        poll(NULL, 0, 200);
    }
}
