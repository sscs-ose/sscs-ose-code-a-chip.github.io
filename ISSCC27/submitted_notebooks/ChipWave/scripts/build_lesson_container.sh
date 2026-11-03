#!/usr/bin/env bash
# Build only the teaching simulator; the formal physical toolchain is separate.
set -euo pipefail
case_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
engine=${CONTAINER_ENGINE:-podman}
command -v "$engine" >/dev/null
lesson_build=$(mktemp -d)
trap 'rm -rf -- "$lesson_build"' EXIT
curl -fL --retry 2 --max-time 600 \
  https://cdimage.ubuntu.com/ubuntu-base/releases/24.04/release/ubuntu-base-24.04.3-base-amd64.tar.gz \
  -o "$lesson_build/ubuntu-base.tar.gz"
(cd "$lesson_build" && echo '6bc2cde3930ad088b3bb46fa45279e96d25bc3810f209850ecbe4722711874f9  ubuntu-base.tar.gz' | sha256sum -c -)
cp "$case_root/toolchain/Containerfile.lesson" "$lesson_build/Containerfile"
"$engine" build "$@" -t localhost/chipwave-lesson:20261030 -f "$lesson_build/Containerfile" "$lesson_build"
