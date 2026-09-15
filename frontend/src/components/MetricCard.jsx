export default function MetricCard({ label, value, detail, accent = '' }) { return <div className={`metric-card ${accent}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small></div> }
