/**
 * generate-theme.ts
 *
 * Reads Dembrandt JSON output (or Brand Guardian JSON) from stdin and writes
 * src/theme.ts to stdout. Substitutes {{PLACEHOLDER}} tokens in
 * template/src/theme.ts.template with extracted brand values.
 *
 * Usage:
 *   npx tsx scripts/generate-theme.ts < brand-audit.json > src/theme.ts
 *
 * Input JSON shape (from Step 2 — Brand Audit):
 *   {
 *     "colors": { "primary": "#HEX", "secondary": "#HEX", "accent": "#HEX", "bg": "#HEX", "bgSoft": "#HEX" },
 *     "fonts": { "display": "Font Name", "body": "Font Name", "mono": "JetBrains Mono" },
 *     "tone": ["Adj1", "Adj2", "Adj3"],
 *     "motionLanguage": "cinematic | minimal | energetic | editorial",
 *     "sceneDurations": { "s1": 7, "s2": 15, ... }
 *   }
 */

import * as fs from "fs";
import * as path from "path";

// — Parse Dembrandt JSON from stdin —
function readStdinSync(): string {
  return fs.readFileSync(0, "utf-8"); // fd 0 = stdin
}

interface BrandAudit {
  colors: {
    primary: string;
    secondary: string;
    accent: string;
    bg: string;
    bgSoft: string;
  };
  fonts: {
    display: string;
    body: string;
    mono?: string;
  };
  tone: string[];
  motionLanguage: string;
  sceneDurations: Record<string, number>;
}

function validateHex(hex: string, label: string): void {
  if (!/^#[0-9a-fA-F]{6}$/.test(hex)) {
    throw new Error(`Invalid color for ${label}: "${hex}". Must be 6-char hex like #FF8800`);
  }
}

function lighten(hex: string, pct: number): string {
  const num = parseInt(hex.slice(1), 16);
  const r = Math.min(255, (num >> 16) + Math.round(255 * pct));
  const g = Math.min(255, ((num >> 8) & 0xff) + Math.round(255 * pct));
  const b = Math.min(255, (num & 0xff) + Math.round(255 * pct));
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, "0")}`;
}

function rgba(hex: string, alpha: number): string {
  const num = parseInt(hex.slice(1), 16);
  const r = (num >> 16) & 0xff;
  const g = (num >> 8) & 0xff;
  const b = num & 0xff;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function main(): void {
  const templatePath = path.resolve(__dirname, "..", "src", "theme.ts.template");
  if (!fs.existsSync(templatePath)) {
    throw new Error(`Template not found: ${templatePath}`);
  }
  let template = fs.readFileSync(templatePath, "utf-8");

  const raw = readStdinSync();
  let audit: BrandAudit;
  try {
    audit = JSON.parse(raw);
  } catch {
    throw new Error("Failed to parse Brand Audit JSON from stdin. Ensure it's valid JSON.");
  }

  // Validate all colors
  for (const [key, hex] of Object.entries(audit.colors)) {
    validateHex(hex, key);
  }

  const { colors: c, fonts: f, sceneDurations: sd } = audit;
  const mono = f.mono ?? "JetBrainsMono";

  // Derive intermediate tokens
  const border = lighten(c.bg, 0.15);
  const hairline = lighten(c.bg, 0.08);
  const primaryGlow = rgba(c.primary, 0.35);
  const accentGlow = rgba(c.accent, 0.35);
  const bridgeGradient = `linear-gradient(90deg, ${c.primary} 0%, ${c.secondary} 50%, ${c.accent} 100%)`;

  const replacements: Record<string, string> = {
    "{{BG}}": c.bg,
    "{{BG_SOFT}}": c.bgSoft,
    "{{SURFACE}}": c.bgSoft,
    "{{BORDER}}": border,
    "{{HAIRLINE}}": hairline,
    "{{PRIMARY}}": c.primary,
    "{{PRIMARY_ALT}}": c.secondary,
    "{{ACCENT}}": c.accent,
    "{{BRIDGE_GRADIENT}}": bridgeGradient,
    "{{TEXT}}": "#FAFAFA",
    "{{TEXT_DIM}}": "rgba(250, 250, 250, 0.62)",
    "{{TEXT_MUTED}}": "rgba(250, 250, 250, 0.38)",
    "{{PRIMARY_GLOW}}": primaryGlow,
    "{{ACCENT_GLOW}}": accentGlow,
    "{{DISPLAY_FONT}}": f.display.replace(/ /g, ""),
    "{{MONO_FONT}}": mono.replace(/ /g, ""),
  };

  for (const [key, val] of Object.entries(replacements)) {
    template = template.replaceAll(key, val);
  }

  // Scene durations
  const durationMap: Record<string, string> = {};
  const FPS = 30;
  for (const [k, seconds] of Object.entries(sd)) {
    durationMap[`{{${k.toUpperCase()}_FRAMES}}`] = String(Math.round(seconds * FPS));
  }

  for (const [key, val] of Object.entries(durationMap)) {
    template = template.replaceAll(key, val);
  }

  // Verify no unreplaced placeholders remain
  const remaining = template.match(/\{\{[A-Z_]+\}\}/g);
  if (remaining) {
    const uniq = [...new Set(remaining)];
    console.error("WARNING: Unreplaced placeholders remain:", uniq.join(", "));
  }

  process.stdout.write(template);
}

main();
