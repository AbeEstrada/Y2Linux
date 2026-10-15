#!/bin/sh
# Quick host check before the container suite: the same curated production
# modules that tools/production/tests.sh runs (the release gate), on the host
# Python, about 40 s. Broad `unittest discover` also collects retained
# historical/profile tests and is not a qualification result (tests/README.md).
# Host prerequisites: clang, pyelftools; qemu-arm for the retained ARM tests.
# The container suite stays the release gate (pinned headers, ARM/QEMU checks).
set -eu
cd "$(dirname "$0")/../.."
modules=$(grep -o 'tests\.test_[a-z0-9_]*' tools/production/tests.sh | sort -u)
missing=
python3 -c 'import elftools' 2>/dev/null || missing="$missing pyelftools"
[ -z "$missing" ] || echo "host-tests: missing$missing (Arch/CachyOS: python-pyelftools); its tests will error" >&2
# shellcheck disable=SC2086 # one module name per word
PYTHONPATH=.:tests:tools/platform exec python3 -m unittest "$@" $modules
