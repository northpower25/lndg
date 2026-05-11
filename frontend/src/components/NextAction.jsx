import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Tile } from './Tile.jsx'

const RISK_COLORS = {
  low: '#4CAF50',
  medium: '#FF9800',
  high: '#f44336',
}

/**
 * Expandable "Why?" panel showing the recommendation rationale.
 */
function WhyPanel({ rationale }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  if (!rationale) return null
  const reasons = rationale.reasons || []
  const netCtx = rationale.network_context

  return (
    <div style={{ marginTop: 4 }}>
      <button
        className="w3-button w3-tiny w3-light-grey w3-round"
        style={{ padding: '2px 8px', minHeight: 44, minWidth: 44 }}
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        aria-label={t('why')}
      >
        {t('why')} {open ? '▲' : '▼'}
      </button>
      {open && (
        <div className="w3-small w3-light-grey w3-round" style={{ marginTop: 4, padding: 8 }}>
          {reasons.map((r, i) => (
            <div key={i} style={{ marginBottom: 2 }}>
              <span className="w3-text-grey" style={{ marginRight: 4 }}>{r.rank}.</span>
              <strong>{r.signal}</strong>: {r.value}
            </div>
          ))}
          {netCtx && (
            <div style={{ marginTop: 6, borderTop: '1px solid #ccc', paddingTop: 4 }}>
              <em className="w3-text-grey">{t('network_context')}</em>
              <div>{t('peer_channels')}: {netCtx.channel_count ?? '—'}</div>
              <div>{t('peer_capacity')}: {(netCtx.total_capacity_sat ?? 0).toLocaleString()} sats</div>
              <div>{t('peer_avg_fee')}: {netCtx.avg_fee_rate_ppm ?? '—'} ppm</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * A single recommendation card.
 */
function ActionCard({ item }) {
  const { t } = useTranslation()
  const riskColor = RISK_COLORS[item.risk] || '#666'
  const pct = Math.round((item.confidence || 0) * 100)

  return (
    <div
      className="w3-round"
      style={{ border: `1px solid ${riskColor}`, padding: 6, marginBottom: 4 }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <strong style={{ fontSize: 13 }}>{item.title}</strong>
        <span
          className="w3-tiny w3-round w3-padding-small"
          style={{ background: riskColor, color: '#fff', minHeight: 44, display: 'inline-flex', alignItems: 'center' }}
        >
          {t('risk')}: {item.risk}
        </span>
      </div>
      <div className="w3-tiny w3-text-grey">
        {t('confidence')}: {pct}% · {item.confidence_label}
      </div>
      {item.reason && <div className="w3-small" style={{ marginTop: 2 }}>{item.reason}</div>}
      <WhyPanel rationale={item.rationale} />
    </div>
  )
}

/**
 * Tile 5: Next Best Action (R-GUI-4: every metric has expandable "Why?" panel).
 */
export function NextActionTile({ data }) {
  const { t } = useTranslation()
  const actions = data?.next_actions || []

  return (
    <Tile icon="🎯" title={t('next_action')} tooltip={t('tooltip_next_action')}>
      {actions.length === 0 ? (
        <span className="w3-text-grey">{t('no_recommendations')}</span>
      ) : (
        actions.map((item, i) => <ActionCard key={item.id ?? i} item={item} />)
      )}
    </Tile>
  )
}
