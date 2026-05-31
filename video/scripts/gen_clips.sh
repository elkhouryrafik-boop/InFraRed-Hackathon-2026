#!/usr/bin/env bash
# Generate cinematic Higgsfield Seedance 2.0 b-roll for the CoolSpend explainer.
# Each clip: 1080p, 16:9, std quality, 5s. Downloads to public/clips/<name>.mp4
set -u
cd "$(dirname "$0")/.." || exit 1
mkdir -p public/clips
OUT=public/clips

gen () {
  local name="$1"; shift
  local prompt="$1"; shift
  echo "=== GEN $name ==="
  local json
  json="$(higgsfield generate create seedance_2_0 \
    --prompt "$prompt" \
    --aspect_ratio 16:9 --resolution 1080p --mode std --duration 5 \
    --wait --wait-timeout 20m --json 2>&1)"
  echo "$json" | tail -c 600
  # extract first mp4 url
  local url
  url="$(printf '%s' "$json" | grep -oE 'https?://[^" ]+\.mp4[^" ]*' | head -1)"
  if [ -z "$url" ]; then
    echo "!! no mp4 url for $name"; return 1
  fi
  echo "downloading $name <- $url"
  curl -sL -o "$OUT/$name.mp4" "$url"
  ls -la "$OUT/$name.mp4" | awk '{print $5, $9}'
}

gen clip01_heat_aerial "Cinematic climate-documentary aerial drift over a dense Mediterranean city at the peak of a summer afternoon, Barcelona-like grid of tight blocks and bare paved plazas shimmering in heat haze, asphalt and stone radiating warmth, almost no trees, a few green pockets standing out as cool oases; slow descending push toward one sun-blasted treeless plaza where heat distortion ripples off the pavement; harsh high overhead sun, oppressive stillness; cool teal-green grade in the shaded corners against hot bleached concrete, restrained and serious, shallow depth, subtle volumetric haze; no people in focus, no on-screen text, no logos, no maps."

gen clip11_dusk_pit "Cinematic climate-documentary aerial drifting slowly over a hot sealed Barcelona block at golden dusk; long tree shadows stretch north across pale paving stones, a few mature canopies casting cool green pools onto bright concrete; one open de-paved soil pit sits empty and waiting beside a sidewalk; slow descending crane move settling toward street level as warm light cools to dusk blue; haze of heat shimmer easing; cool teal-and-green palette, soft volumetric light, shallow depth of field, no people in focus, no on-screen text, no logos, quiet measured reflective mood."

gen clip_shimmer "Extreme close cinematic shot of heat shimmer rising off sun-baked grey pavement and stone at midday, air distortion rippling, hard light, bleached concrete; a soft cool green shadow slowly creeps across the frame from the edge, the shimmer calming where the shade lands; shallow macro depth of field, documentary realism, cool teal-green vs hot white grade, no people, no text, no logos."

gen clip_canopy "Looking up through the dense canopy of a large Mediterranean street tree, dappled golden sunlight filtering through layered green leaves swaying gently, soft bokeh, lens flare, calm and hopeful; slow upward tilt; cinematic shallow depth of field, cool green and warm gold palette, documentary realism, no people, no text, no logos."

gen clip_allee "Cinematic low slow dolly down a Barcelona street lined with mature street trees forming a continuous green canopy overhead, dappled shade falling across the pavement in the late afternoon, calm and restorative, a vision of a cooled city; warm golden light cooling into green shade, shallow depth of field, documentary realism, no people in focus, no text, no logos."

echo "=== CLIPS DONE ==="
ls -la "$OUT"/*.mp4 2>/dev/null | awk '{print $5, $9}'
