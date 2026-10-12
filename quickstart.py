"""One command: python quickstart.py  -> venv, install, demo data, drafted proposal."""
import os, pathlib, subprocess, sys, urllib.request, venv
root = pathlib.Path(__file__).resolve().parent
vdir = root / ".venv"
py = vdir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
def run(*a, env=None): subprocess.run([str(x) for x in a], check=True, cwd=root, env=env)

if not py.exists():
    print("1/4 Creating virtual environment..."); venv.create(vdir, with_pip=True)
print("2/4 Installing dependencies..."); run(py, "-m", "pip", "install", "-q", "-r", "requirements.txt")
print("3/4 Loading fictional demo learner..."); run(py, "seed.py")
env = dict(os.environ)
host = env.get("OLLAMA_HOST", "http://localhost:11434")
try: urllib.request.urlopen(host + "/api/tags", timeout=1); using = f"your local model ({env.get('OLLAMA_MODEL', 'qwen2.5:7b')})"
except Exception: env["DRAFTER"] = "stub"; using = "a built-in stub (no Ollama found; install it to use a real open-weights model)"
print(f"4/4 Agent drafting wording with {using}...")
run(py, "agent.py", "L-DEMO", "--age", "13-15", env=env)
pyc = ".venv\\Scripts\\python" if os.name == "nt" else ".venv/bin/python"
