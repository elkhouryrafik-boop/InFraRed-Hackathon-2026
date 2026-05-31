import "./index.css";
import { Composition } from "remotion";
import { Main } from "./Main";
import { FPS, WIDTH, HEIGHT } from "./theme";
import { TOTAL_FRAMES } from "./lib/timeline";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="CoolSpend"
      component={Main}
      durationInFrames={TOTAL_FRAMES}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
    />
  );
};
