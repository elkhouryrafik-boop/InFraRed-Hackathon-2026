// Root.tsx — Remotion composition registry. Declares the two films the project
// can render: "CoolSpend" (the full ~11-min explainer, assembled by Main) and
// "CoolSpendShort" (a condensed cut, assembled by MainShort). Each composition's
// total length comes from its timeline module (the single source of truth for
// scene durations); canvas size/fps come from theme.ts.
import "./index.css";
import { Composition } from "remotion";
import { Main } from "./Main";
import { MainShort } from "./MainShort";
import { FPS, WIDTH, HEIGHT } from "./theme";
import { TOTAL_FRAMES } from "./lib/timeline";
import { SHORT_TOTAL_FRAMES } from "./lib/timeline_short";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="CoolSpend"
        component={Main}
        durationInFrames={TOTAL_FRAMES}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
      <Composition
        id="CoolSpendShort"
        component={MainShort}
        durationInFrames={SHORT_TOTAL_FRAMES}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
    </>
  );
};
