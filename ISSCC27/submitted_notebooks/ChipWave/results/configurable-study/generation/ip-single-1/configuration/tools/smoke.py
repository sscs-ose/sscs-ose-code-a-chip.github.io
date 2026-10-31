from pathlib import Path
import json,socket,sys
with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
    connection.connect('/run/study-check.sock')
    connection.sendall(b'{"check":"smoke"}\n')
    connection.shutdown(socket.SHUT_WR)
    chunks=[]
    while True:
        data=connection.recv(65536)
        if not data:break
        chunks.append(data)
reply=json.loads(b''.join(chunks))
print(reply['output'],end='')
print('Trusted check receipt:',reply['check_id'])
sys.exit(reply['exit_code'])
