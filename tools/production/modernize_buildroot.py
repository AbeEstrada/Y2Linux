#!/usr/bin/env python3
"""Apply the reviewed userspace package pins to the locked Buildroot tree.

POWER-FINAL-15: the base is Buildroot 2026.08. Packages whose newest upstream
release is newer than that Buildroot ships are raised here, each with the
SHA-256 of the exact archive. The edits are applied after extracting that exact
release, so the resulting source tree is fully reproducible without carrying a
private Buildroot fork.
"""
from pathlib import Path

# (package, recipe edits (old, new), old archive, new archive, new sha256, patches dropped)
BUMPS = (
    ("bluez5_utils", (("BLUEZ5_UTILS_VERSION = 5.86", "BLUEZ5_UTILS_VERSION = 5.87"),),
     "bluez-5.86.tar.xz", "bluez-5.87.tar.xz",
     "26bdcf2cebd7310c6f598850606b037ef0c515fe6608ebc54d22c50c4c32b35f", ()),
    ("bluez5_utils-headers", (("BLUEZ5_UTILS_HEADERS_VERSION = 5.86", "BLUEZ5_UTILS_HEADERS_VERSION = 5.87"),),
     "bluez-5.86.tar.xz", "bluez-5.87.tar.xz",
     "26bdcf2cebd7310c6f598850606b037ef0c515fe6608ebc54d22c50c4c32b35f", ()),
    ("sbc", (("SBC_VERSION = 2.1", "SBC_VERSION = 2.2"),),
     "sbc-2.1.tar.xz", "sbc-2.2.tar.xz",
     "a1ada76ef35e5af9c2fbd063754dc9e37a8d989417c6eb1ecebb089b1383ae9e", ()),
    ("sqlite", (("SQLITE_VERSION = 3.53.4", "SQLITE_VERSION = 3.54.0"),
                ("SQLITE_TAR_VERSION = 3530400", "SQLITE_TAR_VERSION = 3540000")),
     "sqlite-autoconf-3530400.tar.gz", "sqlite-autoconf-3540000.tar.gz",
     "134ec0802dda5795816e25d25872d20b312cb3973438c49b30bc40b7705ea9ed", ()),
    ("libopenssl", (("LIBOPENSSL_VERSION = 3.6.4", "LIBOPENSSL_VERSION = 4.0.3"),),
     "openssl-3.6.4.tar.gz", "openssl-4.0.3.tar.gz",
     "325b5c806167c13b40b1ffeadfe0248197c00eccc4cf123ec1e28d2d2fd216d9",
     # ppc64 big-endian only; not this ARM target.
     ("0002-Configure-use-ELFv2-ABI-on-some-ppc64-big-endian-sys.patch",)),
    ("python3", (("PYTHON3_VERSION_MAJOR = 3.14", "PYTHON3_VERSION_MAJOR = 3.15"),
                 ("PYTHON3_VERSION = $(PYTHON3_VERSION_MAJOR).7", "PYTHON3_VERSION = $(PYTHON3_VERSION_MAJOR).0")),
     "Python-3.14.7.tar.xz", "Python-3.15.0.tar.xz",
     "ba4bed1ba346b916890b76d9e320451420aa69f6408997d33c66482eeae3d575",
     # A 3.14 build fix for the remote debugging module, part of 3.15.
     ("0010-gh-139275-Fix-compilation-of-Modules-_remote_debuggi.patch",)),
    ("mesa3d", (("MESA3D_VERSION = 26.1.8", "MESA3D_VERSION = 26.2.4"),),
     "mesa-26.1.8.tar.xz", "mesa-26.2.4.tar.xz",
     "bce5f7fbebb934373b86c999a064d52fb5065878dc57f287f95346648ec832e9", ()),
    ("libglib2", (("LIBGLIB2_VERSION_MAJOR = 2.88", "LIBGLIB2_VERSION_MAJOR = 2.90"),
                  ("LIBGLIB2_VERSION = $(LIBGLIB2_VERSION_MAJOR).3", "LIBGLIB2_VERSION = $(LIBGLIB2_VERSION_MAJOR).1")),
     "glib-2.88.3.tar.xz", "glib-2.90.1.tar.xz",
     "93c941aa17d5eb1d53fe838365f29a8b4e539c222a256d974ec8f30fc413e396", ()),
    ("openssh", (("OPENSSH_VERSION_MAJOR = 10.5", "OPENSSH_VERSION_MAJOR = 10.6"),),
     "openssh-10.5p1.tar.gz", "openssh-10.6p1.tar.gz",
     "a9dc9565dffe8640f64d863cd29a32bc4a3dbdec0566a7fc44c5d6ee767d5f39", ()),
    ("util-linux", (("UTIL_LINUX_VERSION_MAJOR = 2.41", "UTIL_LINUX_VERSION_MAJOR = 2.42"),
                    ("UTIL_LINUX_VERSION = $(UTIL_LINUX_VERSION_MAJOR).5", "UTIL_LINUX_VERSION = $(UTIL_LINUX_VERSION_MAJOR).4")),
     "util-linux-2.41.5.tar.xz", "util-linux-2.42.4.tar.xz",
     "fbd62a100ab7bb8746ba0661255c3c48185b1e9021507c624da01fbc696330ec", ()),
    ("iproute2", (("IPROUTE2_VERSION = 7.1.0", "IPROUTE2_VERSION = 7.2.0"),),
     "iproute2-7.1.0.tar.xz", "iproute2-7.2.0.tar.xz",
     "4c2fa124c2cf0afd7ca34d1eeacba6ba048a56f6374e2aab93dafbdbd4eea9c0", ()),
    ("expat", (("EXPAT_VERSION = 2.8.4", "EXPAT_VERSION = 2.9.0"),),
     "expat-2.8.4.tar.xz", "expat-2.9.0.tar.xz",
     "1e6371862cc31999b368c3b89b49994f0677e1bab5f1b2b85ae3741f5d803051", ()),
    ("exfatprogs", (("EXFATPROGS_VERSION = 1.2.9", "EXFATPROGS_VERSION = 1.4.3"),),
     "exfatprogs-1.2.9.tar.xz", "exfatprogs-1.4.3.tar.xz",
     "57226a8ec1bfbce06d68a42cde8cd980414a9457882e691fbce4a4f86c8d5f08", ()),
    ("fdk-aac", (("FDK_AAC_VERSION = 2.0.3", "FDK_AAC_VERSION = 3.0.0"),),
     "fdk-aac-2.0.3.tar.gz", "fdk-aac-3.0.0.tar.gz",
     "70b95857b958fb8f794489307a87845dde4cc1fcea060f3f29f40e4b2fe16c82", ()),
    ("iperf3", (("IPERF3_VERSION = 3.21", "IPERF3_VERSION = 3.22"),),
     "iperf-3.21.tar.gz", "iperf-3.22.tar.gz",
     "1c0d0fb02c52626111d6e132db80edfbf27bbaff8bd9245df2a371dcb0b35a92", ()),
    ("json-c", (("JSON_C_VERSION = 0.18", "JSON_C_VERSION = 0.19"),),
     "json-c-0.18.tar.gz", "json-c-0.19.tar.gz",
     "37ad0249902e301bd9052bf712e511fcc6acff4ecaad4b5900aad9ce564e26de", ()),
    ("pcre2", (("PCRE2_VERSION = 10.47", "PCRE2_VERSION = 10.49"),),
     "pcre2-10.47.tar.bz2", "pcre2-10.49.tar.bz2",
     "53c156e1ba416a20da8e65395daa132da0d80e76910424caca3fcdae7831d384", ()),
    ("procps-ng", (("PROCPS_NG_VERSION = 4.0.6", "PROCPS_NG_VERSION = 4.0.7"),),
     "procps-ng-4.0.6.tar.xz", "procps-ng-4.0.7.tar.xz",
     "9d2021f47a4501c667862c9942a92d1953694b21d11bcd1702e83eb594e3d67d", ()),
    ("strace", (("STRACE_VERSION = 7.1", "STRACE_VERSION = 7.2"),),
     "strace-7.1.tar.xz", "strace-7.2.tar.xz",
     "4bde6246926890dcee824f6e6ac42a06752f47d77e5097d86e3c0d6d4b709fe5", ()),
    ("ca-certificates", (("CA_CERTIFICATES_VERSION = 20260223", "CA_CERTIFICATES_VERSION = 20260816"),
                         ("archive/debian/20260223T202245Z/", "archive/debian/20260817T022356Z/")),
     "ca-certificates_20260223.tar.xz", "ca-certificates_20260816.tar.xz",
     "d939bcdd0cb058712cf4175bac76997676eb8b68fe9473765e1b40fb3d5b186a", ()),
    # Buildroot 2025.02.18 (September 2026) already carried a newer database
    # than 2026.08 (August 2026); tools/build/regulatory.py pins the same file.
    ("wireless-regdb", (("WIRELESS_REGDB_VERSION = 2026.05.30", "WIRELESS_REGDB_VERSION = 2026.09.03"),),
     "wireless-regdb-2026.05.30.tar.xz", "wireless-regdb-2026.09.03.tar.xz",
     "b22e0901227b820cd1c280abe681a15b773a5103a5e10dc442e94ebb34cbf58d", ()),
)

BLUEZ_ALSA_VERSION = "5.0.0"
BLUEZ_ALSA_SHA256 = "e1249cbebd24925c977814f62adab71f2ebd771e28e6a4ac58bb1ac97ce3beb5"
TOOLCHAIN_VERSION = "2026.08-1"
TOOLCHAIN_SHA256 = "9b7e25a74e87dac1e05d399444295e254a3073a056101e3197a859490e5701cd"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if old in text:
        path.write_text(text.replace(old, new, 1))
    elif new not in text:
        raise ValueError(f"expected pin missing from {path}: {old}")


def replace_archive_hash(path: Path, old_archive: str, new_archive: str, sha256: str) -> None:
    """Every hash line of the old archive becomes one SHA-256 line of the new one."""
    lines = path.read_text().splitlines()
    kept = [line for line in lines if not line.rstrip().endswith("  " + old_archive)]
    new_line = f"sha256  {sha256}  {new_archive}"
    if len(kept) == len(lines) and new_line not in lines:
        raise ValueError(f"expected source hash missing from {path}: {old_archive}")
    if new_line not in kept:
        kept.append(new_line)
    path.write_text("\n".join(kept) + "\n")


def bump(buildroot_source: Path, name, edits, old_archive, new_archive, sha256, dropped) -> None:
    package = buildroot_source / "package" / name
    for old, new in edits:
        replace_once(package / f"{name}.mk", old, new)
    replace_archive_hash(package / f"{name}.hash", old_archive, new_archive, sha256)
    for patch_name in dropped:
        patch = package / patch_name
        if patch.exists():
            patch.unlink()


def bluez_alsa(buildroot_source: Path) -> None:
    package = buildroot_source / "package/bluez-alsa"
    recipe = package / "bluez-alsa.mk"
    replace_once(recipe, "BLUEZ_ALSA_VERSION = 4.3.1", f"BLUEZ_ALSA_VERSION = {BLUEZ_ALSA_VERSION}")
    replace_once(recipe, "--enable-cli", "--enable-ctl")
    # BlueALSA 5 has more optional A2DP/profile switches. Keep every one
    # disabled in the product package; a future codec decision must change the
    # Buildroot configuration deliberately and add its own evidence.
    marker = "\t--disable-debug-time \\\n"
    text = recipe.read_text()
    disables = (
        "\t--disable-asha \\\n"
        "\t--disable-faststream \\\n"
        "\t--disable-lc3plus \\\n"
        "\t--disable-lc3-swb \\\n"
        "\t--disable-ldac \\\n"
        "\t--disable-lhdc \\\n"
    )
    if "--disable-ldac" not in text:
        if marker not in text:
            raise ValueError("BlueALSA configure option anchor missing")
        recipe.write_text(text.replace(marker, disables + marker, 1))
    # Explicit owner-private qualification profile. Keep this after the stock
    # option branches: independently selecting another library must never enable
    # an unreviewed encoder or mix GPL-3 libopenaptx with FDK-AAC.
    text = recipe.read_text()
    experiment_options = """# Y2 owner-private optional encoder profile
ifeq ($(BR2_PACKAGE_Y2_CODEC_EXPERIMENTS),y)
ifeq ($(BR2_PACKAGE_LIBOPENAPTX),y)
$(error Y2 codec profile requires libfreeaptx, not libopenaptx)
endif
BLUEZ_ALSA_DEPENDENCIES += fdk-aac libfreeaptx libldac
BLUEZ_ALSA_CONF_OPTS := $(filter-out --disable-aac --disable-aptx --disable-aptx-hd --disable-ldac,$(BLUEZ_ALSA_CONF_OPTS))
BLUEZ_ALSA_CONF_OPTS += --enable-aac --with-libfreeaptx --enable-aptx --enable-aptx-hd --enable-ldac
endif

"""
    if "# Y2 owner-private optional encoder profile" not in text:
        anchor = "$(eval $(autotools-package))"
        if anchor not in text:
            raise ValueError("BlueALSA package evaluation anchor missing")
        recipe.write_text(text.replace(anchor, experiment_options + anchor, 1))
    # BlueALSA 5.0.0 places -static in AM_CFLAGS. With Buildroot's normal
    # shared D-Bus/ALSA/BlueZ stack that flag reaches the bluealsad link and
    # makes the ARM build reject dynamic libraries. Keep the stack dynamic and
    # carry this narrowly scoped, source-pinned integration fix.
    (package / "0001-bluealsad-use-shared-system-libraries.patch").write_text(
        """--- a/src/Makefile.am
+++ b/src/Makefile.am
@@ -171,8 +171,7 @@
\t@MPG123_CFLAGS@ \\
\t@OPUS_CFLAGS@ \\
\t@SBC_CFLAGS@ \\
-\t@SPANDSP_CFLAGS@ \\
-\t-static
+\t@SPANDSP_CFLAGS@

 libbluealsad_la_LIBADD = \\
\tshared/libshared.la \\
"""
    )
    replace_archive_hash(package / "bluez-alsa.hash", "bluez-alsa-4.3.1.tar.gz",
                         f"bluez-alsa-{BLUEZ_ALSA_VERSION}.tar.gz", BLUEZ_ALSA_SHA256)
    replace_once(
        package / "bluez-alsa.hash",
        "956564dcf06ba65cd7a5eb6cdfd695e2ab0f09ea9684e4eaf079f5d533bd206d",
        "47a67fe6b44d4aff90c837ebce38814bf89fdf5efd6bc6c9c078f960c35f61b8",
    )


def bootlin_toolchain(buildroot_source: Path) -> None:
    """Bootlin armv7-eabihf glibc stable 2025.08-1 -> 2026.08-1 (GCC 15.3, glibc 2.44)."""
    base = buildroot_source / "toolchain/toolchain-external/toolchain-external-bootlin"
    options = base / "Config.in.options"
    text = options.read_text()
    start = text.index("config BR2_TOOLCHAIN_EXTERNAL_BOOTLIN_ARMV7_EABIHF_GLIBC_STABLE\n")
    end = text.index("\nconfig ", start + 1)
    block = text[start:end]
    updated = (block.replace('bool "armv7-eabihf glibc stable 2025.08-1"',
                             f'bool "armv7-eabihf glibc stable {TOOLCHAIN_VERSION}"')
                    .replace("\tdepends on !BR2_ARCH_NEEDS_GCC_AT_LEAST_15\n", "")
                    .replace("select BR2_TOOLCHAIN_GCC_AT_LEAST_14\n", "select BR2_TOOLCHAIN_GCC_AT_LEAST_15\n")
                    # Buildroot checks a Bootlin toolchain's headers strictly: 2026.08-1 has 5.10.
                    .replace("select BR2_TOOLCHAIN_HEADERS_AT_LEAST_5_4\n", "select BR2_TOOLCHAIN_HEADERS_AT_LEAST_5_10\n"))
    if (f"stable {TOOLCHAIN_VERSION}" not in updated or "GCC_AT_LEAST_15" not in updated
            or "HEADERS_AT_LEAST_5_10" not in updated):
        raise ValueError("Bootlin armv7-eabihf glibc stable option anchor missing")
    options.write_text(text[:start] + updated + text[end:])
    recipe = base / "toolchain-external-bootlin.mk"
    text = recipe.read_text()
    anchor = "ifeq ($(BR2_TOOLCHAIN_EXTERNAL_BOOTLIN_ARMV7_EABIHF_GLIBC_STABLE),y)\nTOOLCHAIN_EXTERNAL_BOOTLIN_VERSION = 2025.08-1\n"
    if anchor in text:
        recipe.write_text(text.replace(anchor, anchor.replace("2025.08-1", TOOLCHAIN_VERSION), 1))
    elif anchor.replace("2025.08-1", TOOLCHAIN_VERSION) not in text:
        raise ValueError("Bootlin armv7-eabihf glibc stable version anchor missing")
    replace_archive_hash(base / "toolchain-external-bootlin.hash",
                         "armv7-eabihf--glibc--stable-2025.08-1.tar.xz",
                         f"armv7-eabihf--glibc--stable-{TOOLCHAIN_VERSION}.tar.xz", TOOLCHAIN_SHA256)


def apply(buildroot_source: Path) -> None:
    for row in BUMPS:
        bump(buildroot_source, *row)
    bluez_alsa(buildroot_source)
    bootlin_toolchain(buildroot_source)
    # Local product-policy patches follow the pinned package security fixes.
    for package in ('dropbear', 'openssh', 'bluez-alsa'):
        for policy in (Path(__file__).resolve().parents[2] / 'buildroot/patches' / package).glob('*.patch'):
            (buildroot_source / 'package' / package / policy.name).write_bytes(policy.read_bytes())


if __name__ == "__main__":
    import sys

    apply(Path(sys.argv[1]))
