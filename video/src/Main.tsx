import React from "react";
import { AbsoluteFill, Sequence, staticFile } from "remotion";
import { Audio } from "@remotion/media";
import { colors } from "./theme";
import { SCENES } from "./lib/timeline";
import { SceneFrame } from "./SceneFrame";

import { Scene01 } from "./scenes/Scene01";
import { Scene02 } from "./scenes/Scene02";
import { Scene03 } from "./scenes/Scene03";
import { Scene04 } from "./scenes/Scene04";
import { Scene05 } from "./scenes/Scene05";
import { Scene06 } from "./scenes/Scene06";
import { Scene07 } from "./scenes/Scene07";
import { Scene08 } from "./scenes/Scene08";
import { Scene09 } from "./scenes/Scene09";
import { Scene10 } from "./scenes/Scene10";
import { Scene11 } from "./scenes/Scene11";

const REGISTRY: Record<number, React.FC<{ df: number }>> = {
  1: Scene01,
  2: Scene02,
  3: Scene03,
  4: Scene04,
  5: Scene05,
  6: Scene06,
  7: Scene07,
  8: Scene08,
  9: Scene09,
  10: Scene10,
  11: Scene11,
};

export const Main: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: colors.bg }}>
      {SCENES.map((s) => {
        const Comp = REGISTRY[s.index];
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
      {/* music bed, looped, low under VO */}
      <Audio src={staticFile("audio/music.mp3")} volume={0.14} loop />
    </AbsoluteFill>
  );
};
