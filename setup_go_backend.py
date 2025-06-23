import os
import subprocess
import sys
import platform

if platform.system() == "Windows":
    BIN_NAME = 'go_backend.exe'
else:
    BIN_NAME = 'go_backend'
BIN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), BIN_NAME)
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'go_backend')



def ensure_built():
    if not os.path.exists(BIN_PATH):
        print('Building Go backend...')
        result = subprocess.run(['go', 'build', '-o', BIN_PATH, os.path.join(SRC_DIR, 'main.go')])
        if result.returncode != 0:
            raise RuntimeError('go build failed')


def start_backend():
    ensure_built()
    return subprocess.Popen([BIN_PATH])


if __name__ == '__main__':
    try:
        p = start_backend()
        print('Go backend started with PID', p.pid)
        p.wait()
    except KeyboardInterrupt:
        pass
