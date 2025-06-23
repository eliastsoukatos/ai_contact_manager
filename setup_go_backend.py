import os
import subprocess
import sys
import platform
import time

# Configuración de nombres y rutas
if platform.system() == "Windows":
    BIN_NAME = 'go_backend.exe'
else:
    BIN_NAME = 'go_backend'
BIN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), BIN_NAME)
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'go_backend')
PORT = 8081

def kill_process_on_port(port):
    print(f"Checking for existing process on port {port}...")
    if platform.system() == "Windows":
        cmd = f'netstat -ano | findstr :{port}'
        output = subprocess.getoutput(cmd)
        for line in output.splitlines():
            if "LISTENING" in line or "ESTABLISHED" in line:
                parts = line.strip().split()
                pid = parts[-1]
                print(f"Terminating process with PID {pid} on port {port}...")
                subprocess.run(['taskkill', '/PID', pid, '/F'])
    else:
        # Linux/macOS
        cmd = f"lsof -i :{port} -t"
        output = subprocess.getoutput(cmd)
        for pid in output.splitlines():
            print(f"Killing process {pid} on port {port}...")
            subprocess.run(['kill', '-9', pid])

def ensure_built():
    print('Building Go backend...')
    result = subprocess.run(['go', 'build', '-o', BIN_PATH, os.path.join(SRC_DIR, 'main.go')])
    if result.returncode != 0:
        raise RuntimeError('go build failed')

def start_backend():
    ensure_built()
    print('Launching backend...')
    return subprocess.Popen([BIN_PATH])

if __name__ == '__main__':
    try:
        kill_process_on_port(PORT)
        # Breve pausa para liberar el puerto antes de lanzar el backend
        time.sleep(1)
        p = start_backend()
        print('Go backend started with PID', p.pid)
        p.wait()
    except KeyboardInterrupt:
        print("Shutting down.")
    except Exception as e:
        print("Error:", e)
        sys.exit(1)
