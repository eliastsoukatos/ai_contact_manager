import os
import subprocess
import sys
import platform
import signal
import socket
import shutil

DEFAULT_DSN = "postgresql://contacts_user:contacts_pass@localhost/contacts_db"

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# --- PATH to Go binary ---
if platform.system() == "Windows":
    BIN_NAME = "go_backend.exe"
else:
    BIN_NAME = "go_backend"
BIN_PATH = os.path.join(PROJECT_ROOT, BIN_NAME)
SRC_DIR = os.path.join(PROJECT_ROOT, "go_backend")

# --- Windows: Add bin to PATH if gcc is present ---
def setup_gcc_path():
    if platform.system() == "Windows":
        gcc_path = os.path.join(PROJECT_ROOT, "bin", "gcc.exe")
        if os.path.exists(gcc_path):
            bin_dir = os.path.dirname(gcc_path)
            os.environ["PATH"] = f"{bin_dir};{os.environ['PATH']}"
            print(f"[INFO] Added {bin_dir} to PATH for gcc.")
        else:
            print("[WARNING] gcc.exe not found in ./bin. Make sure your compiler is available in PATH.")

# --- Kill any process using port 8081 ---
def kill_process_on_port(port):
    try:
        if platform.system() == "Windows":
            cmd = f'for /f "tokens=5" %a in (\'netstat -ano ^| findstr :{port}\') do taskkill /PID %a /F'
            os.system(cmd)
        else:
            # Unix: find pid and kill
            output = subprocess.check_output(
                f"lsof -ti tcp:{port}", shell=True, text=True
            ).strip()
            if output:
                for pid in output.splitlines():
                    os.kill(int(pid), signal.SIGTERM)
    except Exception as e:
        print(f"[WARN] Could not kill process on port {port}: {e}")

# --- Ensure PostgreSQL is installed and database exists ---
def ensure_postgres():
    dsn = os.environ.get("POSTGRES_DSN", DEFAULT_DSN)
    if shutil.which("psql") is None:
        print(
            "[ERROR] PostgreSQL not found. Please install it from https://www.postgresql.org/download/"
        )
        return dsn

    try:
        subprocess.run(["psql", "-d", "postgres", "-c", f"CREATE DATABASE contacts_db"], check=False)
        subprocess.run(
            [
                "psql",
                "-d",
                "postgres",
                "-c",
                "CREATE USER contacts_user WITH PASSWORD 'contacts_pass'",
            ],
            check=False,
        )
        subprocess.run(
            [
                "psql",
                "-d",
                "postgres",
                "-c",
                "GRANT ALL PRIVILEGES ON DATABASE contacts_db TO contacts_user",
            ],
            check=False,
        )
    except Exception as exc:
        print(f"[WARN] Could not initialize PostgreSQL: {exc}")
    return dsn

# --- Compile Go binary ---
def build_go_backend():
    print("[INFO] Building Go backend...")
    result = subprocess.run(
        ["go", "build", "-o", BIN_PATH, os.path.join(SRC_DIR, "main.go")]
    )
    if result.returncode != 0:
        print("[ERROR] go build failed")
        sys.exit(1)

# --- Run backend ---
def start_backend():
    print("[INFO] Launching backend...")
    return subprocess.Popen([BIN_PATH])

if __name__ == "__main__":
    print("Checking for existing process on port 8081...")
    kill_process_on_port(8081)
    setup_gcc_path()
    dsn = ensure_postgres()
    os.environ.setdefault("POSTGRES_DSN", dsn)

    try:
        import psycopg2  # type: ignore
    except Exception:
        subprocess.run([sys.executable, "-m", "pip", "install", "psycopg2-binary"], check=False)

    build_go_backend()
    try:
        p = start_backend()
        print(f"Go backend started with PID {p.pid}")
        p.wait()
    except KeyboardInterrupt:
        print("Shutting down backend...")
        pass
