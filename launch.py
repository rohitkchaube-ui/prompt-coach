"""One-step launcher for Prompt Coach.

Run it with `python launch.py` (or double-click run.bat / run ./run.sh). It will:
  1. check your Python version
  2. create a private virtual environment in .venv and install dependencies
  3. ask for your Claude API key the first time and save it to .env
  4. start the app and open it in your browser

Uses only the standard library, so it works before anything is installed.
"""

import getpass
import os
import socket
import subprocess
import sys
import time
import urllib.request
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
ENV_FILE = ROOT / ".env"
REQUIREMENTS = ROOT / "requirements.txt"
STAMP = VENV / ".requirements-installed"
MIN_PYTHON = (3, 10)
KEY_NAME = "ANTHROPIC_API_KEY"


def say(msg: str) -> None:
    print(f"[Prompt Coach] {msg}", flush=True)


def fail(msg: str) -> None:
    say(f"ERROR: {msg}")
    sys.exit(1)


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def ensure_python_version() -> None:
    if sys.version_info < MIN_PYTHON:
        fail(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer is required "
            f"(you have {sys.version.split()[0]}). Get it from https://www.python.org/downloads/"
        )


def ensure_dependencies() -> None:
    if not venv_python().exists():
        say("First run: creating a virtual environment in .venv ...")
        venv.EnvBuilder(with_pip=True).create(VENV)

    # Reinstall only when requirements.txt has changed since the last install.
    wanted = REQUIREMENTS.read_text(encoding="utf-8")
    if STAMP.exists() and STAMP.read_text(encoding="utf-8") == wanted:
        return
    say("Installing dependencies (this takes a minute the first time) ...")
    result = subprocess.run(
        [str(venv_python()), "-m", "pip", "install", "--quiet",
         "--disable-pip-version-check", "-r", str(REQUIREMENTS)]
    )
    if result.returncode != 0:
        fail("Installing dependencies failed. Check your internet connection and try again.")
    STAMP.write_text(wanted, encoding="utf-8")


def read_key() -> str:
    if os.environ.get(KEY_NAME):
        return os.environ[KEY_NAME]
    if not ENV_FILE.exists():
        return ""
    for line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        name, sep, value = line.partition("=")
        if sep and name.strip() == KEY_NAME:
            value = value.strip().strip('"').strip("'")
            if value and "your-key" not in value:
                return value
    return ""


def ensure_api_key() -> None:
    if read_key():
        return
    print()
    say("You need a Claude API key. Create one at https://console.anthropic.com/settings/keys")
    say("(Your key is saved only on this computer, in the .env file.)")
    while True:
        # getpass hides the key while you paste it.
        key = getpass.getpass("Paste your API key and press Enter (it won't be shown): ").strip()
        if key.startswith("sk-ant-"):
            break
        say("That doesn't look like a Claude API key (they start with 'sk-ant-'). Try again.")
    ENV_FILE.write_text(f"{KEY_NAME}={key}\n", encoding="utf-8")
    say("Saved to .env")


def free_port(preferred: int = 8000) -> int:
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    fail("Could not find a free port between 8000 and 8019.")


def wait_until_up(url: str, proc: subprocess.Popen, timeout: float = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except OSError:
            time.sleep(0.5)
    return False


def main() -> None:
    os.chdir(ROOT)
    ensure_python_version()
    ensure_dependencies()
    ensure_api_key()

    port = free_port()
    url = f"http://localhost:{port}"
    say(f"Starting at {url} ...")
    proc = subprocess.Popen(
        [str(venv_python()), "-m", "uvicorn", "backend.main:app", "--port", str(port)]
    )
    try:
        if not wait_until_up(f"{url}/api/models", proc):
            fail("The server didn't start. See the messages above.")
        if "--no-browser" not in sys.argv:
            webbrowser.open(url)
        say(f"Running at {url}  -  press Ctrl+C in this window to stop.")
        proc.wait()
    except KeyboardInterrupt:
        say("Stopping ...")
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)


if __name__ == "__main__":
    main()
