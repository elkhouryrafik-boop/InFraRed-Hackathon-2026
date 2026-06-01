// timeline_short.ts — same construction as lib/timeline.ts but for the condensed
// "CoolSpendShort" cut. Joins data/scenes_short.json (script + captions, each
// row naming its scene component via `comp`) with data/timings_short.json
// (measured VO durations) into SHORT_SCENES[] (consumed by MainShort.tsx) and
// SHORT_TOTAL_FRAMES (registered in Root.tsx).
import { FPS } from "../theme";
import scenes from "../data/scenes_short.json";
import timings from "../data/timings_short.json";
import type { Cue } from "../components/Captions";

const HEAD_S = 0.35; // visual settle before VO
const TAIL_S = 0.8; // breathing room after VO

type SceneJson = { id: string; comp: string; captions: { text: string }[] };

export type ShortMeta = {
  id: string;
  comp: string;
  index: number;
  df: number;
  offset: number;
  voStartF: number;
  voFile: string;
  cues: Cue[];
};

const sceneArr = scenes as SceneJson[];
const timeArr = timings as { id: string; comp: string; duration_s: number; file: string }[];
const voStartF = Math.round(HEAD_S * FPS);

let offset = 0;
export const SHORT_SCENES: ShortMeta[] = sceneArr.map((sc, i) => {
  const dur = timeArr[i]?.duration_s ?? 8;
  const df = Math.round((HEAD_S + dur + TAIL_S) * FPS);
  const spanF = Math.round(dur * FPS);
  const phrases = sc.captions.map((c) => c.text);
  const per = phrases.length > 0 ? spanF / phrases.length : spanF;
  const cues: Cue[] = phrases.map((text, j) => ({
    text,
    fromF: voStartF + Math.round(j * per),
    toF: voStartF + Math.round((j + 1) * per) - 2,
  }));
  const meta: ShortMeta = {
    id: sc.id,
    comp: sc.comp,
    index: i + 1,
    df,
    offset,
    voStartF,
    voFile: timeArr[i]?.file ?? `audio/short_${String(i + 1).padStart(2, "0")}.mp3`,
    cues,
  };
  offset += df;
  return meta;
});

export const SHORT_TOTAL_FRAMES = offset;
