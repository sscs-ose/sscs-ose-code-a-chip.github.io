#!/bin/sh
# usage: sh run.sh <command...>   (runs inside the cac-eda container with this folder at /w)
D=$(cd "$(dirname "$0")" && pwd -W 2>/dev/null || pwd)
MSYS_NO_PATHCONV=1 docker run --rm -v "$D:/w" -w /w cac-eda2 "$@"
