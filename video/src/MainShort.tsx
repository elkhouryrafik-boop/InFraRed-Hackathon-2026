// MainShort.tsx — assembles the condensed "CoolSpendShort" cut. Same structure
// as Main.tsx (walk SHORT_SCENES → place each in a Sequence at its offset, wrap
// in SceneFrame, add per-scene VO + a music bed) but it only uses a subset of
// the scenes, keyed by name via `s.comp` rather than numeric index.
import React from "react";
import { AbsoluteFill, Sequence, staticFile } from "remotion";
import { Audio } from "@remotion/media";
import { colors } from "./theme";
import { SHORT_SCENES } from "./lib/timeline_short";
import { SceneFrame } from "./SceneFrame";

import { Scene01 } from "./scenes/Scene01";
import { Scene05 } from "./scenes/Scene05";
import { Scene08 } from "./scenes/Scene08";
import { Scene09 } from "./scenes/Scene09";
import { Scene10 } from "./scenes/Scene10";
import { Scene11 } from "./scenes/Scene11";

const REGISTRY: Record<string, React.FC<{ df: number }>> = {
  Scene01,
  Scene05,
  Scene08,
  Scene09,
  Scene10,
  Scene11,
};

export const MainShort: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: colors.bg }}>
      {SHORT_SCENES.map((s) => {
        const Comp = REGISTRY[s.comp];
        return (
          <Sequence key={s.id} from={s.offset} durationInFrames={s.df} layout="none">
            <SceneFrame df={s.df} cues={s.cues}>
              <Comp df={s.df} />
            </SceneFrame>
            <Sequence from={s.voStartF} layout="none">
              <Audio src={staticFile(s.voFile)} volume={1} />
            </Sequence>
          </Sequence>
        );
      })}
      <Audio src={staticFile("audio/music.mp3")} volume={0.14} loop />
    </AbsoluteFill>
  );
};
