// Client-side species dimensions + foliage colour, mirroring coolspend/bcn_species.py
// (crown diameter + height, from the Barcelona arbrat-viari size bands). Used to
// draw the citywide plan's per-site trees (citywide_plan.json carries only
// {lon,lat,species}) as real canopy disks rather than abstract pins.

export interface SpeciesDims {
  crown_m: number
  height_m: number
}

// scientific name → mature crown Ø (m) / height (m). Values match SPECIES_TABLE.
export const SPECIES_DIMS: Record<string, SpeciesDims> = {
  'Platanus x acerifolia': { crown_m: 10, height_m: 18 },
  'Celtis australis': { crown_m: 7, height_m: 18 },
  'Styphnolobium japonicum': { crown_m: 7, height_m: 10 },
  'Tipuana tipu': { crown_m: 10, height_m: 18 },
  'Melia azedarach': { crown_m: 7, height_m: 10 },
  'Brachychiton populneus': { crown_m: 5, height_m: 10 },
  'Jacaranda mimosifolia': { crown_m: 7, height_m: 10 },
  'Cercis siliquastrum': { crown_m: 5, height_m: 4 },
  'Magnolia grandiflora': { crown_m: 5, height_m: 10 },
}

export function speciesDims(scientific: string): SpeciesDims {
  return SPECIES_DIMS[scientific] ?? { crown_m: 6, height_m: 10 }
}

// Natural foliage greens, slightly varied per species so a mixed planting reads
// as a real canopy (not one flat colour). Teal/mint is reserved for UI accents —
// trees must read as GREEN leaves. Returned as 0–255 RGB.
const FOLIAGE: Record<string, [number, number, number]> = {
  'Tipuana tipu': [86, 168, 74], // bright spring green
  'Celtis australis': [64, 142, 86], // deeper green
  'Styphnolobium japonicum': [110, 176, 84], // yellow-green
  'Jacaranda mimosifolia': [72, 158, 120], // blue-green
  'Melia azedarach': [96, 162, 78],
  'Brachychiton populneus': [120, 168, 96],
  'Cercis siliquastrum': [104, 150, 70],
  'Magnolia grandiflora': [58, 124, 78], // dark glossy
}

export function foliageColor(scientific: string): [number, number, number] {
  return FOLIAGE[scientific] ?? [86, 160, 86]
}
