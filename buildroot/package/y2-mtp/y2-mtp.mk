################################################################################
# File-level USB transfer. Upstream pin plus reviewed Y2 safety patch/helpers.
################################################################################
Y2_MTP_VERSION = 2241a803c27f1fff7537cb9504befeb810b880d3
Y2_MTP_SITE = $(call github,viveris,uMTP-Responder,$(Y2_MTP_VERSION))
Y2_MTP_SOURCE = y2-mtp-$(Y2_MTP_VERSION).tar.gz
Y2_MTP_SITE_METHOD = wget
Y2_MTP_LICENSE = GPL-3.0+
Y2_MTP_LICENSE_FILES = LICENSE

define Y2_MTP_COPY_SAFETY_HELPERS
	$(INSTALL) -m 0644 $(BR2_EXTERNAL_Y2LINUX_PATH)/../tools/usb/mtp-safe.h $(@D)/inc/mtp-safe.h
	$(INSTALL) -m 0644 $(BR2_EXTERNAL_Y2LINUX_PATH)/../tools/usb/mtp-safe.c $(@D)/src/mtp-safe.c
endef
Y2_MTP_POST_PATCH_HOOKS += Y2_MTP_COPY_SAFETY_HELPERS

define Y2_MTP_BUILD_CMDS
	$(TARGET_MAKE_ENV) $(MAKE) -C $(@D) CC="$(TARGET_CC)" CPPFLAGS="$(TARGET_CPPFLAGS)" CFLAGS="$(TARGET_CFLAGS) -I./inc -Wall" LDFLAGS="$(TARGET_LDFLAGS) -lpthread -lrt"
endef

define Y2_MTP_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(@D)/umtprd $(TARGET_DIR)/usr/sbin/umtprd
endef

$(eval $(generic-package))
