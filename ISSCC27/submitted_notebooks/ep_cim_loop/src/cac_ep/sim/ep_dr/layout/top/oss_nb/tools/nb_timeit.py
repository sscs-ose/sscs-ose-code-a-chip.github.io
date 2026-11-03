"""/usr/bin/time -f "%e %M" 대신 (빈 이미지에 time 이 없을 수 있음). 쓰임: python3 nb_timeit.py <출력 파일> <명령 …>
출력 파일에 "<벽시계 초> <최대 RSS kB>" 한 줄 (opensrc/chip/summarize.py 가 읽는 꼴). 종료 코드는 명령의 것."""
import resource
import subprocess
import sys
import time

t0 = time.time()
rc = subprocess.call(sys.argv[2:])
rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
open(sys.argv[1], 'w').write(f'{time.time() - t0:.2f} {rss}\n')
sys.exit(rc)
