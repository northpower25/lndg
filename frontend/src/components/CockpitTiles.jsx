import { useTranslation } from 'react-i18next'
import { Tile } from './Tile.jsx'

function fmt(n) {
  if (n == null) return '—'
  return Number(n).toLocaleString()
}

/**
 * Tile 1: Routing Activity (7d / 30d forwarding events + fees)
 */
export function RoutingActivityTile({ data }) {
  const { t } = useTranslation()
  const r7 = data?.routing?.['7d'] || {}
  const r30 = data?.routing?.['30d'] || {}

  return (
    <Tile icon="⚡" title={t('routing_activity')} tooltip={t('tooltip_routing')}>
      <div>7d: <strong>{fmt(r7.count)}</strong> {t('events')},&nbsp;<strong>{fmt(r7.fees_sat)}</strong> {t('sats_fees')}</div>
      <div>30d: <strong>{fmt(r30.count)}</strong> {t('events')},&nbsp;<strong>{fmt(r30.fees_sat)}</strong> {t('sats_fees')}</div>
    </Tile>
  )
}

/**
 * Tile 2: Liquidity Balance
 */
export function LiquidityTile({ data }) {
  const { t } = useTranslation()
  const liq = data?.liquidity || {}
  const outPct = liq.outbound_pct ?? 50
  const inPct = 100 - outPct

  return (
    <Tile icon="💧" title={t('liquidity_balance')} tooltip={t('tooltip_liquidity')}>
      <div>{t('outbound')}: <strong>{fmt(outPct)}%</strong></div>
      <div
        className="w3-round w3-grey"
        style={{ height: 6, margin: '4px 0' }}
        role="progressbar"
        aria-valuenow={outPct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <span
          className="w3-round w3-blue"
          style={{ display: 'block', height: 6, width: `${outPct}%` }}
        />
      </div>
      <div className="w3-tiny w3-text-grey">
        {t('inbound')}: {fmt(inPct)}% &nbsp;|&nbsp; {t('of_capacity')}: {fmt(liq.total_capacity_sat)} sats
      </div>
    </Tile>
  )
}

/**
 * Tile 3: Fee Positioning
 */
export function FeePositioningTile({ data }) {
  const { t } = useTranslation()
  const fees = data?.fees || {}

  return (
    <Tile icon="💰" title={t('fee_positioning')} tooltip={t('tooltip_fee')}>
      <div>{t('avg_fee_rate')}: <strong>{fmt(fees.avg_fee_rate)} {t('ppm')}</strong></div>
      <div className="w3-tiny w3-text-grey">
        ↓ {fmt(fees.channels_below_median)} {t('channels_below_median')} &nbsp;|&nbsp;
        ↑ {fmt(fees.channels_above_median)} {t('channels_above_median')}
      </div>
    </Tile>
  )
}

/**
 * Tile 4: Issues
 */
export function IssuesTile({ data }) {
  const { t } = useTranslation()
  const issues = data?.issues || {}
  const disabled = issues.disabled_channels ?? 0
  const failed = issues.failed_htlc_24h ?? 0
  const allGood = disabled === 0 && failed === 0

  return (
    <Tile icon="⚠️" title={t('issues')} tooltip={t('tooltip_issues')}>
      {allGood ? (
        <span className="w3-text-green">{t('all_good')}</span>
      ) : (
        <>
          {disabled > 0 && <div className="w3-text-orange">{disabled} {t('disabled_channels')}</div>}
          {failed > 0 && <div className="w3-text-red">{failed} {t('failed_htlcs_24h')}</div>}
        </>
      )}
    </Tile>
  )
}
