import { useTranslation } from 'react-i18next'

/**
 * Small "?" tooltip icon that shows a help text on hover.
 */
export function Tooltip({ text }) {
  return (
    <span
      title={text}
      aria-label={text}
      style={{ cursor: 'help', color: '#888', marginLeft: 4, minWidth: 44, minHeight: 44, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
    >
      ❓
    </span>
  )
}

/**
 * Generic cockpit tile card wrapper (R-GUI-5: touch targets ≥ 44px).
 */
export function Tile({ icon, title, tooltip, children }) {
  const { t } = useTranslation()
  return (
    <div
      className="w3-card w3-padding"
      style={{ flex: 1, minWidth: 160 }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <strong>
          {icon} {title}
        </strong>
        {tooltip && <Tooltip text={tooltip} />}
      </div>
      <div className="w3-small" style={{ marginTop: 4 }}>
        {children}
      </div>
    </div>
  )
}
