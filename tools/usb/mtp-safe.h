/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef Y2_MTP_SAFE_H
#define Y2_MTP_SAFE_H
#include <dirent.h>
#include <stdint.h>
#include <sys/stat.h>
struct y2_upload;
/* Roots are pinned once per responder, never reopened after a card swap. */
int y2_fs_init(const char *internal, const char *sd, const char *events);
int y2_open(const char *path, int flags, mode_t mode);
int y2_stat(const char *path, struct stat64 *st);
DIR *y2_opendir(const char *path);
int y2_remove(const char *path);
int y2_mkdir(const char *path, mode_t mode);
int y2_rename(const char *from, const char *to);
struct y2_upload *y2_upload_begin(const char *path, uint64_t size);
int y2_upload_write(struct y2_upload *upload, const void *data, size_t length);
int y2_upload_finish(struct y2_upload *upload);
void y2_upload_abort(struct y2_upload *upload);
void y2_transfer_activity(int active, int error);
#endif
