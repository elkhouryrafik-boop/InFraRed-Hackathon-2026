// TreeInspect — side panel showing one clicked tree: identity, shade it
// provides, and its ecological profile (an "ecosystem", not just a dot).

import type { TreeProperties, TreeEcology } from '../lib/types'
import './TreeInspect.css'

interface TreeInspectProps {
  tree: TreeProperties | null
  onClose: () => void
}

/** 0–1 score → a labelled meter. `invert` flips the color (penalty metrics). */
function Meter({
  label,
  value,
  invert = false,
  hint,
}: {
  label: string
  value: number | undefined
  invert?: boolean
  hint?: string
}) {
  if (value == null || !Number.isFinite(value)) return null
  const pct = Math.max(0, Math.min(1, value)) * 100
  // For benefit metrics: high = green. For penalty metrics (invert): high = red.
  const good = invert ? 1 - value : value
  const hue = Math.round(good * 130) // 0=red → 130=green
  return (
    <div className="tin__meter" title={hint}>
      <div className="tin__meter-row">
        <span className="tin__meter-label">{label}</span>
        <span className="tin__meter-val">{Math.round(pct)}</span>
      </div>
      <div className="tin__meter-track">
        <div
          className="tin__meter-fill"
          style={{ width: `${pct}%`, background: `hsl(${hue} 70% 45%)` }}
        />
      </div>
    </div>
  )
}

function EcologyBlock({ eco }: { eco: TreeEcology }) {
  return (
    <div className="tin__section">
      <div className="tin__section-title">Ecosystem profile</div>

      {eco.ecosystem_score != null && (
        <Meter
          label="Ecosystem health (composite)"
          value={eco.ecosystem_score}
          hint="Weighted blend of the dimensions below"
        />
      )}

      {eco.native_status && (
        <div className="tin__kv">
          <span>Origin</span>
          <strong
            className={
              /invasive/i.test(eco.native_status)
                ? 'is-bad'
                : /native/i.test(eco.native_status)
                  ? 'is-good'
                  : ''
            }
          >
            {eco.native_status}
          </strong>
        </div>
      )}

      <Meter label="Drought / heat tolerance" value={eco.drought_heat_tolerance} />
      <Meter label="Biodiversity value" value={eco.biodiversity_value} />
      <Meter label="Pollinator value" value={eco.pollinator_value} />
      <Meter label="Carbon sequestration" value={eco.carbon_sequestration} />
      <Meter
        label="Allergenicity (pollen)"
        value={eco.allergenicity}
        invert
        hint="Higher = worse allergy burden"
      />
      <Meter
        label="Pest / disease risk"
        value={eco.pest_disease_risk}
        invert
        hint="Higher = more vulnerable"
      />

      <div className="tin__chips">
        {eco.longevity_years != null && (
          <span className="tin__chip">~{eco.longevity_years} yr lifespan</span>
        )}
        {eco.growth_rate && <span className="tin__chip">{eco.growth_rate} growth</span>}
        {eco.water_demand && <span className="tin__chip">{eco.water_demand} water</span>}
        {eco.maintenance_burden && (
          <span className="tin__chip">{eco.maintenance_burden} upkeep</span>
        )}
        {eco.mycorrhizal_type && (
          <span className="tin__chip">{eco.mycorrhizal_type} mycorrhizae</span>
        )}
      </div>

      {eco.notes && <div className="tin__notes">{eco.notes}</div>}
    </div>
  )
}

export function TreeInspect({ tree, onClose }: TreeInspectProps) {
  if (!tree) return null
  const isProposed = tree.kind === 'proposed'
  const shade = tree.crown_area_m2

  return (
    <div className="tin">
      <button className="tin__close" onClick={onClose} aria-label="Close">
        ×
      </button>

      <div className="tin__kind">
        {isProposed ? '🌱 Proposed planting' : '🌳 Existing tree'}
        {tree.known === false && <span className="tin__unknown"> · not in palette</span>}
      </div>
      <div className="tin__common">{tree.common || tree.species || 'Unknown'}</div>
      {tree.species && tree.common && tree.species !== tree.common && (
        <div className="tin__sci">{tree.species}</div>
      )}

      <div className="tin__stats">
        {tree.height_m != null && (
          <div className="tin__stat">
            <strong>{tree.height_m} m</strong>
            <span>height</span>
          </div>
        )}
        {tree.crown_diameter_m != null && (
          <div className="tin__stat">
            <strong>{tree.crown_diameter_m} m</strong>
            <span>crown Ø</span>
          </div>
        )}
        {shade != null && (
          <div className="tin__stat">
            <strong>{Math.round(shade)} m²</strong>
            <span>shade footprint</span>
          </div>
        )}
      </div>

      <div className="tin__tags">
        {tree.leaf_cycle && <span className="tin__chip">{tree.leaf_cycle}</span>}
        {tree.shade_density && (
          <span className="tin__chip">{tree.shade_density} shade</span>
        )}
        {tree.cooling_score != null && (
          <span className="tin__chip tin__chip--cool">
            cooling {Math.round(tree.cooling_score * 100)}/100
          </span>
        )}
      </div>

      {tree.ecology ? (
        <EcologyBlock eco={tree.ecology} />
      ) : (
        <div className="tin__notes">Ecological profile not available for this species.</div>
      )}
    </div>
  )
}
