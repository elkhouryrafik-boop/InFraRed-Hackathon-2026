"""Generate per-scene VO for the 2-min "CoolSpendShort" cut (sibling of
gen_vo.py): reads vo_text from scenes_short.json, synthesizes short_<NN>.mp3 per
scene with edge-tts, probes durations, and writes timings_short.json — consumed
by lib/timeline_short. Run with SYSTEM python (has edge_tts):
   python scripts/gen_vo_short.py
Outputs public/audio/short_<NN>.mp3 + src/data/timings_short.json
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE = "en-GB-RyanNeural"
AUDIO = os.path.join(ROOT, "public", "audio")
os.makedirs(AUDIO, exist_ok=True)
scenes = json.load(open(os.path.join(ROOT, "src", "data", "scenes_short.json"), encoding="utf-8"))

def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except Exception:
        return 0.0

timings = []
for i, sc in enumerate(scenes, 1):
    nn = f"{i:02d}"
    txt = os.path.join(AUDIO, f"short_{nn}.txt")
    mp3 = os.path.join(AUDIO, f"short_{nn}.mp3")
    open(txt, "w", encoding="utf-8").write(sc["vo_text"].strip())
    print(f"[{nn}] {sc['id']} ...", flush=True)
    r = subprocess.run([sys.executable, "-m", "edge_tts", "--voice", VOICE,
                        "--file", txt, "--write-media", mp3], capture_output=True, text=True)
    if r.returncode != 0:
        print("  ERR:", r.stderr[-200:], flush=True)
    dur = probe(mp3)
    print(f"  {dur:.1f}s", flush=True)
    timings.append({"id": sc["id"], "comp": sc["comp"], "idx": i,
                    "file": f"audio/short_{nn}.mp3", "duration_s": round(dur, 3)})

json.dump(timings, open(os.path.join(ROOT, "src", "data", "timings_short.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("TOTAL", round(sum(t["duration_s"] for t in timings), 1), "s")
