import os
import subprocess
import sys
import platform
import signal
import shutil

DEFAULT_DSN = "postgresql://contacts_user:CBSIX1KWPhWuZB@localhost/contacts_db?sslmode=disable"

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# --- PATH to Go binary ---
if platform.system() == "Windows":
    BIN_NAME = "go_backend.exe"
else:
    BIN_NAME = "go_backend"
BIN_PATH = os.path.join(PROJECT_ROOT, BIN_NAME)
SRC_DIR = os.path.join(PROJECT_ROOT, "go_backend")

# --- Add gcc and psql to PATH ---
def setup_tool_paths():
    if platform.system() == "Windows":
        # Add GCC
        gcc_path = os.path.join(PROJECT_ROOT, "bin", "gcc.exe")
        if os.path.exists(gcc_path):
            gcc_bin = os.path.dirname(gcc_path)
            os.environ["PATH"] = f"{gcc_bin};{os.environ['PATH']}"
            print(f"[INFO] Added {gcc_bin} to PATH for gcc.")
        else:
            print("[WARNING] gcc.exe not found in ./bin.")

        # Add PostgreSQL
        pg_path = r"C:\Program Files\PostgreSQL\17\bin"
        if os.path.exists(os.path.join(pg_path, "psql.exe")):
            os.environ["PATH"] = f"{pg_path};{os.environ['PATH']}"
            print(f"[INFO] Added {pg_path} to PATH for PostgreSQL.")
        else:
            print("[ERROR] PostgreSQL tools not found in default directory.")
            print("        Please install from https://www.postgresql.org/download/")
    else:
        print("[INFO] Assuming system has gcc and psql installed via PATH.")

# --- Kill process on port ---
def kill_process_on_port(port):
    try:
        if platform.system() == "Windows":
            cmd = f'for /f "tokens=5" %a in (\'netstat -ano ^| findstr :{port}\') do taskkill /PID %a /F'
            os.system(cmd)
        else:
            output = subprocess.check_output(f"lsof -ti tcp:{port}", shell=True, text=True).strip()
            if output:
                for pid in output.splitlines():
                    os.kill(int(pid), signal.SIGTERM)
    except Exception as e:
        print(f"[WARN] Could not kill process on port {port}: {e}")

# --- Ensure PostgreSQL and DB exist ---
def ensure_postgres():
    dsn = os.environ.get("POSTGRES_DSN", DEFAULT_DSN)
    if shutil.which("psql") is None:
        print("[ERROR] PostgreSQL not found. Please install it from https://www.postgresql.org/download/")
        return dsn

    from urllib.parse import urlparse

    parsed = urlparse(dsn)
    db_name = parsed.path.lstrip("/") or "contacts_db"
    app_user = parsed.username or "contacts_user"
    app_pass = parsed.password or ""
    host = parsed.hostname or "localhost"
    port = str(parsed.port or 5432)

    admin_user = "postgres"
    admin_pass = os.environ.get("POSTGRES_PASSWORD", app_pass)

    env = os.environ.copy()
    if admin_pass:
        env["PGPASSWORD"] = admin_pass

    try:
        subprocess.run(
            [
                "psql",
                "-h",
                host,
                "-p",
                port,
                "-U",
                admin_user,
                "-d",
                "postgres",
                "-c",
                f"CREATE DATABASE {db_name}"
            ],
            check=False,
            env=env,
        )

        if app_user != admin_user:
            subprocess.run(
                [
                    "psql",
                    "-h",
                    host,
                    "-p",
                    port,
                    "-U",
                    admin_user,
                    "-d",
                    "postgres",
                    "-c",
                    f"CREATE USER {app_user} WITH PASSWORD '{app_pass}'"
                ],
                check=False,
                env=env,
            )
            subprocess.run(
                [
                    "psql",
                    "-h",
                    host,
                    "-p",
                    port,
                    "-U",
                    admin_user,
                    "-d",
                    "postgres",
                    "-c",
                    f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {app_user}"
                ],
                check=False,
                env=env,
            )
    except Exception as exc:
        print(f"[WARN] PostgreSQL init failed: {exc}")
    return dsn

# --- Compile Go binary ---
def build_go_backend():
    print("[INFO] Building Go backend...")
    result = subprocess.run(["go", "build", "-o", BIN_PATH, os.path.join(SRC_DIR, "main.go")])
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
    setup_tool_paths()
    dsn = ensure_postgres()
    os.environ.setdefault("POSTGRES_DSN", dsn)

    try:
        import psycopg2
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "psycopg2-binary"], check=False)

    build_go_backend()
    try:
        p = start_backend()
        print(f"Go backend started with PID {p.pid}")
        p.wait()
    except KeyboardInterrupt:
        print("Shutting down backend...")
