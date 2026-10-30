#! /bin/bash
# run every check ignoring any error
# output summarised results at the end
cd "$(dirname "$0")/.."
LOG=build/check
mkdir -p $LOG
rm -f $LOG/summary.txt
fail=0

step() {
  name=$1; shift
  start=$(date +%s)
  if "$@" > $LOG/$name.log 2>&1; then
    result=PASS
  else 
    result=FAIL; fail=1
  fi
  echo "$result  $name  ($(( $(date +%s) - start ))s)" | tee -a $LOG/summary.txt
}

step pin_level bash scripts/run.sh
step lint bash scripts/lint.sh
step coverage bash scripts/coverage.sh
step formal bash scripts/formal.sh

step sigrok python3 scripts/sigrok_check.py

exit $fail
