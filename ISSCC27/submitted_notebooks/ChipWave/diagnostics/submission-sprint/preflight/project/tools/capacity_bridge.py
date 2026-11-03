import json,socket,sys
from pathlib import Path
if sys.argv[1]=='result':
 reply=json.loads(Path(sys.argv[2]).read_text())
 print(reply['output'],end='')
 raise SystemExit(reply['exit_code'])
event=json.load(sys.stdin)
try:
 with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
  connection.connect('/run/study-check.sock')
  connection.sendall(json.dumps(event).encode()+b'\n')
  connection.shutdown(socket.SHUT_WR)
  chunks=[]
  while True:
   chunk=connection.recv(65536)
   if not chunk:break
   chunks.append(chunk)
 reply=json.loads(b''.join(chunks))
except Exception:
 if event.get('hook_event_name')=='PreToolUse':
  reply={'hookSpecificOutput':{'hookEventName':'PreToolUse','permissionDecision':'deny',
   'permissionDecisionReason':'Protected tool controller unavailable; call rejected.'}}
 else:
  reply={'continue':False,'stopReason':'Protected tool observer unavailable.'}
print(json.dumps(reply))
