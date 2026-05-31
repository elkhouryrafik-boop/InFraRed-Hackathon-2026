import { FPS } from "../theme";
import scenes from "../data/scenes.json";
import timings from "../data/timings.json";
import type { Cue } from "../components/Captions";

const HEAD_S = 0.4; // visual settle before VO
const TAIL_S = 1.0; // breathing room after VO

type SceneJson = {
  id: string;
  title: string;
  captions: { text: string }[];
};

export type SceneMeta = {
  id: string;
  title: string;
  index: number; // 1-based
  df: number; // total frames
  offset: number; // cumulative start frame
  voStartF: number; // frame the VO begins
  voFile: string;
  cues: Cue[];
};

const sceneArr = scenes as SceneJson[];
const timeArr = timings as { id: string; duration_s: number; file: string }[];

const voStartF = Math.round(HEAD_S * FPS);

let offset = 0;
export const SCENES: SceneMeta[] = sceneArr.map((sc, i) => {
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
  const meta: SceneMeta = {
    id: sc.id,
    title: sc.title,
    index: i + 1,
    df,
    offset,
    voStartF,
    voFile: timeArr[i]?.file ?? `audio/vo_${String(i + 1).padStart(2, "0")}.mp3`,
    cues,
  };
  offset += df;
  return meta;
});

export const TOTAL_FRAMES = offset;
