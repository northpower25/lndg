import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import '../i18n.js'
import { fetchCockpit } from '../api/cockpit.js'
import {
  RoutingActivityTile,
  LiquidityTile,
  FeePositioningTile,
  IssuesTile,
} from './CockpitTiles.jsx'
import { NextActionTile } from './NextAction.jsx'

/**
 * Main cockpit dashboard component.
 * Renders the five information tiles and fetches data from /api/v2/cockpit/.
 */
export default function Dashboard() {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const json = await fetchCockpit()
      setData(json)
    } catch (err) {
      setError(err.message || t('error_loading'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    load()
  }, [load])

  if (loading) {
    return (
      <div style={{ padding: 16, textAlign: 'center' }}>
        {t('loading')}
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: 16 }} className="w3-text-red">
        {t('error_loading')}: {error}
        <br />
        <button
          className="w3-button w3-blue w3-round"
          style={{ marginTop: 8, minHeight: 44 }}
          onClick={load}
        >
          {t('refresh')}
        </button>
      </div>
    )
  }

  return (
    <div>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 8,
          marginTop: 8,
        }}
      >
        <RoutingActivityTile data={data} />
        <LiquidityTile data={data} />
        <FeePositioningTile data={data} />
        <IssuesTile data={data} />
        <NextActionTile data={data} />
      </div>
      <div style={{ textAlign: 'right', marginTop: 8 }}>
        <button
          className="w3-button w3-small w3-light-grey w3-round"
          style={{ minHeight: 44 }}
          onClick={load}
          aria-label={t('refresh')}
        >
          ↺ {t('refresh')}
        </button>
      </div>
    </div>
  )
}
