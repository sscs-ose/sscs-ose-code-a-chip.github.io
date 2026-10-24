#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(realpath -m "$1")"
OUT="$(realpath -m "$2")"
PREFIX="$WORK/install"
mkdir -p "$WORK/src" "$OUT/logs" "$OUT/technology" "$OUT/licenses"
unset PDK_ROOT PDKPATH

fetch_source() {
    local name="$1" repo sha dest
    repo="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]]["repository"])' "$HERE/pins.json" "$name")"
    sha="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]]["commit"])' "$HERE/pins.json" "$name")"
    dest="$WORK/src/$name"
    if [[ -e "$dest" ]]; then
        echo "Refusing to reuse an existing source/build directory: $dest" >&2
        return 1
    fi
    git init -q "$dest"
    git -C "$dest" remote add origin "$repo"
    git -C "$dest" config remote.origin.promisor true
    git -C "$dest" config remote.origin.partialclonefilter blob:none
    if [[ "$name" == open_pdks ]]; then
        git -C "$dest" sparse-checkout init --cone
        git -C "$dest" sparse-checkout set common scripts sky130/magic \
            sky130/netgen sky130/custom/scripts
    fi
    git -C "$dest" fetch -q --depth=1 --filter=blob:none origin "$sha"
    git -C "$dest" checkout -q --detach FETCH_HEAD
    test "$(git -C "$dest" rev-parse HEAD)" = "$sha"
    printf '%s\t%s\t%s\n' "$name" "$sha" "$repo" >> "$OUT/sources.tsv"
    cp "$dest/VERSION" "$OUT/${name}-source-version.txt"
    if [[ "$name" == netgen ]]; then
        cp "$dest/Copying" "$OUT/licenses/$name.txt"
    else
        cp "$dest/LICENSE" "$OUT/licenses/$name.txt"
    fi
}

for name in magic netgen open_pdks; do
    fetch_source "$name" > "$OUT/logs/fetch-$name.log" 2>&1
done

export PATH="$PREFIX/bin:$PATH"
export SOURCE_DATE_EPOCH
SOURCE_DATE_EPOCH="$(git -C "$WORK/src/magic" show -s --format=%ct HEAD)"
(
    cd "$WORK/src/magic"
    ./configure --prefix="$PREFIX" --without-opengl --disable-magic-builddate
    make prepare
    make -j2
    make install
) > "$OUT/logs/build-magic.log" 2>&1
magic -dnull -noconsole --version > "$OUT/magic-executed-version.txt" 2>&1
magic -dnull -noconsole --commit > "$OUT/magic-executed-commit.txt" 2>&1
(
    cd "$WORK/src/netgen"
    ./configure --prefix="$PREFIX"
    make -j2
    make install
) > "$OUT/logs/build-netgen.log" 2>&1
(
    cd "$WORK/src/open_pdks"
    ./configure --prefix="$PREFIX" \
        --disable-primitive-sky130 --disable-io-sky130 \
        --disable-sc-hs-sky130 --disable-sc-ms-sky130 \
        --disable-sc-ls-sky130 --disable-sc-lp-sky130 \
        --disable-sc-hd-sky130 --disable-sc-hdll-sky130 \
        --disable-sc-hvl-sky130 --disable-alpha-sky130 \
        --disable-xschem-sky130 --disable-klayout-sky130 \
        --disable-precheck-sky130
    # Never invoke all, prerequisites, vendor, or a full PDK install.
    make -C sky130 magic-A netgen-A
) > "$OUT/logs/build-open_pdks.log" 2>&1

PDK="$WORK/src/open_pdks/sky130/sky130A/libs.tech"
cp "$PDK/magic/sky130A.tech" "$PDK/magic/sky130A.magicrc" \
    "$PDK/magic/sky130A.tcl" "$PDK/netgen/sky130A_setup.tcl" "$OUT/technology/"
sha256sum "$OUT/technology/"* > "$OUT/technology-sha256.txt"
find "$PREFIX" -type f \( -name '*.so' -o -name magic -o -name netgen \) \
    -exec sha256sum {} + > "$OUT/tool-binary-sha256.txt"
du -sk "$WORK/src/"* "$PREFIX" > "$OUT/toolchain-size-kib.tsv"
cp "$HERE/pins.json" "$OUT/pins.json"
uname -a > "$OUT/host.txt"
python3 --version >> "$OUT/host.txt"
dpkg-query -W -f='${binary:Package}\t${Version}\n' \
    $(cat "$HERE/apt-packages.txt") > "$OUT/apt-versions.tsv"
echo "Pinned tools and genuine tools-only sky130A staging are ready."
