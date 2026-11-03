#!/usr/bin/env bash
echo "=== docker ==="
docker ps --format '{{.Names}} {{.Status}}'
echo "=== yosys log tail ==="
tail -4 $HOME/flashattn_expmul/syn/d4_base/yosys.log 2>/dev/null
echo "=== synth dirs ==="
du -sh $HOME/flashattn_expmul/syn/* 2>/dev/null
echo "=== fetch ==="
tail -3 $HOME/flashattn_expmul/fetch.log
du -sh $HOME/flashattn_expmul/models/flan-t5-base
ls -la $HOME/flashattn_expmul/models/flan-t5-base | head -8
