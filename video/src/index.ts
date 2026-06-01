// index.ts — Remotion bundle entry point. Registers the root component so the
// CLI / Studio / render pipeline can discover this project's compositions.
import { registerRoot } from "remotion";
import { RemotionRoot } from "./Root";

registerRoot(RemotionRoot);
