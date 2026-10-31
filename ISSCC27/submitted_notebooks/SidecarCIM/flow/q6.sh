#!/bin/bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"
bash flow/runw2.sh
bash flow/p128q.sh 35 w6a4 w4a4 s3k4
