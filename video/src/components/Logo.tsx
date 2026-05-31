import React from "react";
import { Img, staticFile } from "remotion";

type Props = {
  brandName: string;
  tagline?: string;
  primaryColor: string;
  accentColor: string;
  size?: number;
  mono?: boolean;
  logoUrl?: string;
};

export const Logo: React.FC<Props> = ({
  brandName,
  tagline,
  primaryColor,
  accentColor,
  size = 88,
  mono = false,
  logoUrl,
}) => {
  const gradId = `logo-grad-${mono ? "m" : "c"}`;
  const c1 = mono ? "#fff" : primaryColor;
  const c2 = mono ? "#fff" : accentColor;

  const words = brandName.split(/(?=[A-Z])/);
  const firstWord = words[0] ?? brandName;
  const rest = words.slice(1).join("");

  const logoGlyph = logoUrl ? (
    <Img
      src={staticFile(logoUrl)}
      style={{ width: size, height: size, objectFit: "contain" }}
    />
  ) : (
    <svg width={size} height={size} viewBox="0 0 100 100">
      <defs>
        <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={c1} />
          <stop offset="100%" stopColor={c2} />
        </linearGradient>
      </defs>
      <path
        d="M 50 8 L 92 50 L 50 92 L 8 50 Z"
        fill="none"
        stroke={`url(#${gradId})`}
        strokeWidth={4}
      />
      <path
        d="M 50 30 L 70 50 L 50 70 L 30 50 Z"
        fill={`url(#${gradId})`}
        opacity={0.9}
      />
    </svg>
  );

  return (
    <div style={{ display: "flex", alignItems: "center", gap: size * 0.18 }}>
      {logoGlyph}
      <div style={{ display: "flex", flexDirection: "column", lineHeight: 1 }}>
        <div
          style={{
            color: "#fff",
            fontSize: size * 0.32,
            fontWeight: 800,
            letterSpacing: -0.5,
          }}
        >
          {firstWord}
          {rest && <span style={{ opacity: 0.55 }}>{rest}</span>}
        </div>
        {tagline && (
          <div
            style={{
              color: "rgba(255,255,255,0.45)",
              fontSize: size * 0.2,
              fontWeight: 400,
              letterSpacing: 1.5,
              textTransform: "uppercase",
              marginTop: 2,
            }}
          >
            {tagline}
          </div>
        )}
      </div>
    </div>
  );
};
