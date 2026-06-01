/**
 * align-scenes.ts — starter-kit helper that derives scene durations + per-line
 * reveal frames by matching a VO transcript (Whisper word timings) against the
 * script. (This film's timings come from gen_vo.py/ffprobe → timings.json; this
 * is the alternative Whisper-alignment path.)
 *
 * Parses Whisper word-level timestamp JSON and computes scene timing values
 * for theme.ts and per-scene Reveal startFrame constants.
 *
 * Usage:
 *   npx tsx scripts/align-scenes.ts \
 *     --whisper out/vo-transcript/vo.json \
 *     --script scripts/vo-script.txt \
 *     --fps 30 \
 *     > out/scene-timing.json
 *
 * Output JSON:
 *   {
 *     "sceneDurations": { "s1": 210, "s2": 450, ... },
 *     "sceneReveals": {
 *       "s1": [{ "element": "hero", "startFrame": 0 }, ...],
 *       ...
 *     }
 *   }
 *
 * Algorithm:
 *   1. Read whisper JSON → array of {word, start, end}
 *   2. Read VO script → split by double-newline into scene paragraphs
 *   3. For each paragraph, find matching word range in whisper output
 *   4. sceneDuration = (last_word_end - first_word_start) * FPS
 *   5. Within each scene, major text elements map to their sentence's first word time
 */

import * as fs from "fs";

// — Whisper JSON structures —

interface WhisperWord {
  word: string;
  start: number;
  end: number;
  probability: number;
}

interface WhisperSegment {
  id: number;
  seek: number;
  start: number;
  end: number;
  text: string;
  tokens: number[];
  temperature: number;
  avg_logprob: number;
  compression_ratio: number;
  no_speech_prob: number;
  words: WhisperWord[];
}

interface WhisperOutput {
  text: string;
  segments: WhisperSegment[];
  language: string;
}

interface Args {
  whisperPath: string;
  scriptPath: string;
  fps: number;
}

function parseArgs(): Args {
  const args = process.argv.slice(2);
  const parsed: Record<string, string> = {};
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i].replace(/^--/, "");
    parsed[key] = args[i + 1] ?? "";
  }
  if (!parsed.whisper) throw new Error("--whisper is required");
  if (!parsed.script) throw new Error("--script is required");
  return {
    whisperPath: parsed.whisper,
    scriptPath: parsed.script,
    fps: parseInt(parsed.fps ?? "30", 10),
  };
}

// Normalize text for matching: lowercase, strip punctuation, collapse whitespace
function normalize(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^\w\s]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

// Find the word range in flattened whisper words that best matches a paragraph of text
function findWordRange(
  words: WhisperWord[],
  paragraphNormalized: string,
): { start: number; end: number } | null {
  const paraWords = paragraphNormalized.split(" ");
  if (paraWords.length === 0) return null;

  // Sliding window over whisper words
  const windowSize = Math.max(paraWords.length, 3);
  let bestMatch = { idx: -1, score: 0 };

  for (let i = 0; i <= words.length - Math.max(3, Math.floor(paraWords.length / 2)); i++) {
    const windowWords = words.slice(i, i + windowSize).map((w) => normalize(w.word));
    let score = 0;
    for (let j = 0; j < paraWords.length && j < windowWords.length; j++) {
      if (windowWords[j] === paraWords[j]) score++;
    }
    if (score > bestMatch.score) {
      bestMatch = { idx: i, score };
    }
  }

  if (bestMatch.score < 2) return null; // too weak

  const endIdx = Math.min(bestMatch.idx + paraWords.length + 2, words.length - 1);
  return {
    start: words[bestMatch.idx].start,
    end: words[endIdx].end,
  };
}

function main(): void {
  const args = parseArgs();

  // Load whisper output
  const whisperRaw = fs.readFileSync(args.whisperPath, "utf-8");
  const whisper: WhisperOutput = JSON.parse(whisperRaw);

  // Flatten all words
  const allWords: WhisperWord[] = [];
  for (const seg of whisper.segments) {
    if (seg.words) allWords.push(...seg.words);
  }
  if (allWords.length === 0) {
    throw new Error("No word-level timestamps found in whisper output. Use --word_timestamps True");
  }

  // Load VO script and split into scene paragraphs
  const scriptText = fs.readFileSync(args.scriptPath, "utf-8");
  const paragraphs = scriptText
    .split(/\n\n+/)
    .map((p) => p.trim())
    .filter(Boolean);

  // Map each paragraph to a word range
  const sceneRanges: { start: number; end: number }[] = [];
  for (const para of paragraphs) {
    const range = findWordRange(allWords, normalize(para));
    if (range) {
      sceneRanges.push(range);
    } else {
      console.error(`WARNING: Could not match paragraph to whisper output: "${para.slice(0, 80)}..."`);
      // Fallback: use average word timing if we have scenes
      if (sceneRanges.length > 0) {
        const prev = sceneRanges[sceneRanges.length - 1];
        sceneRanges.push({ start: prev.end + 0.5, end: prev.end + 5 });
      } else {
        sceneRanges.push({ start: 0, end: 7 });
      }
    }
  }

  // Compute scene durations in frames
  const sceneDurations: Record<string, number> = {};
  for (let i = 0; i < sceneRanges.length; i++) {
    const dur = Math.round((sceneRanges[i].end - sceneRanges[i].start) * args.fps);
    sceneDurations[`s${i + 1}`] = Math.max(dur, 30); // minimum 1 second
  }

  // Build reveal timing suggestions per scene
  // Each scene paragraph's sentences map to major reveal points
  const sceneReveals: Record<string, { element: string; startFrame: number }[]> = {};
  for (let i = 0; i < paragraphs.length; i++) {
    const sceneKey = `s${i + 1}`;
    const sceneStart = sceneRanges[i]?.start ?? 0;
    const sentences = paragraphs[i].split(/(?<=[.!?])\s+/).filter(Boolean);
    const reveals: { element: string; startFrame: number }[] = [];

    for (let j = 0; j < sentences.length; j++) {
      const sentWords = normalize(sentences[j]);
      const range = findWordRange(allWords, sentWords);
      const startFrame = range
        ? Math.round((range.start - sceneStart) * args.fps)
        : j * 40; // fallback: stagger by ~1.3s
      reveals.push({
        element: `line${j + 1}`,
        startFrame: Math.max(0, startFrame),
      });
    }
    sceneReveals[sceneKey] = reveals;
  }

  const output = {
    sceneDurations,
    sceneReveals,
    totalFrames: Object.values(sceneDurations).reduce((a, b) => a + b, 0),
    totalSeconds: Object.values(sceneDurations).reduce((a, b) => a + b, 0) / args.fps,
    fps: args.fps,
  };

  process.stdout.write(JSON.stringify(output, null, 2) + "\n");
}

main();
