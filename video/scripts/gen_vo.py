"""Generate per-scene VO (edge-tts Ryan) + VTT word timings; emit timings.json.

This is THE VO pipeline for the full film: it reads each scene's `vo_text` from
src/data/scenes.json, synthesizes one mp3 per scene with edge-tts, probes the
real duration with ffprobe, and writes src/data/timings.json — which lib/timeline
then reads to size each scene. Re-run this whenever scene narration changes.

Run from video/ dir:  python scripts/gen_vo.py
Outputs:
  public/audio/vo_<NN>.mp3   (one per scene)
  public/audio/vo_<NN>.vtt   (word boundaries)
  src/data/timings.json      [{id, idx, file, duration_s, segs:[{start,end}]}]
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE = "en-GB-RyanNeural"
AUDIO = os.path.join(ROOT, "public", "audio")
os.makedirs(AUDIO, exist_ok=True)

scenes = json.load(open(os.path.join(ROOT, "src", "data", "scenes.json"), encoding="utf-8"))

def vtt_time(t):
    # "00:00:01.250" -> seconds
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)

def parse_vtt(path):
    segs = []
    if not os.path.exists(path):
        return segs
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        m = re.match(r"(\d\d:\d\d:\d\d\.\d+)\s*-->\s*(\d\d:\d\d:\d\d\.\d+)", line)
        if m:
            segs.append({"start": vtt_time(m.group(1)), "end": vtt_time(m.group(2))})
    return segs

def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except Exception:
        return 0.0

timings = []
for i, sc in enumerate(scenes, 1):
    nn = f"{i:02d}"
    txt = os.path.join(AUDIO, f"vo_{nn}.txt")
    mp3 = os.path.join(AUDIO, f"vo_{nn}.mp3")
    vtt = os.path.join(AUDIO, f"vo_{nn}.vtt")
    open(txt, "w", encoding="utf-8").write(sc["vo_text"].strip())
    print(f"[{nn}] edge-tts {sc['id']} ...", flush=True)
    r = subprocess.run(
        [sys.executable, "-m", "edge_tts", "--voice", VOICE,
         "--file", txt, "--write-media", mp3, "--write-subtitles", vtt],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print("  edge-tts ERROR:", r.stderr[-300:], flush=True)
    dur = probe(mp3)
    segs = parse_vtt(vtt)
    print(f"  duration={dur:.2f}s  cues={len(segs)}", flush=True)
    timings.append({
        "id": sc["id"], "idx": i, "file": f"audio/vo_{nn}.mp3",
        "duration_s": round(dur, 3),
        "first": segs[0]["start"] if segs else 0.0,
        "last": segs[-1]["end"] if segs else round(dur, 3),
        "segs": segs,
    })

json.dump(timings, open(os.path.join(ROOT, "src", "data", "timings.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
total = sum(t["duration_s"] for t in timings)
print(f"=== VO DONE === total spoken {total:.1f}s across {len(timings)} scenes")
