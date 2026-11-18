import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "results" / "clean_run_log.txt"
TMP = Path(tempfile.mkdtemp(prefix="cleanenv_"))
PY = TMP / "venv" / "Scripts" / "python.exe"
NEEDED = ["sites_all.csv", "sites_pilot.csv", "sites_eval.csv", "tracker_domains.txt",
          "build_tracker_list.py", "eval_results.csv", "eval_labels_claude.csv", "eval_labels_me.csv"]

log = open(LOG, "w", encoding="utf-8")


def say(text):
    print(text, flush=True)
    log.write(text + "\n")
    log.flush()


def run(args):
    args = [str(a) for a in args]
    say("\n> " + " ".join(args))
    proc = subprocess.Popen(args, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    for line in proc.stdout:
        say(line.rstrip())
    code = proc.wait()
    if code != 0:
        say(f"FAILED with exit code {code}")
        raise SystemExit(code)


say(f"Clean run started {datetime.now().isoformat(timespec='seconds')}")
for name in NEEDED:
    hits = [p for p in ROOT.rglob(name) if ".venv" not in p.parts]
    say(f"{name}: {'found at ' + str(hits[0].relative_to(ROOT)) if hits else 'MISSING'}")

run([sys.executable, "-m", "venv", TMP / "venv"])
run([PY, "-m", "pip", "install", "-r", ROOT / "requirements.txt"])
run([PY, "-m", "pip", "install", "cryptography"])
run([PY, "-m", "playwright", "install", "chromium"])
run([PY, "-m", "pip", "freeze"])
run([PY, "-c", "import sys; sys.path.insert(0, 'src/stage2_banner'); import pipeline; "
     "print('pipeline imported, tracker domains loaded:', len(pipeline.KNOWN_TRACKERS))"])
run([PY, ROOT / "src" / "stage2_banner" / "evaluate_eval.py"])
run([PY, ROOT / "tests" / "run_all.py"])
say("\nClean run finished")