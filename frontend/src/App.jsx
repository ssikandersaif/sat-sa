import { useEffect, useMemo, useRef, useState } from 'react'
import { Activity, AlertTriangle, ArrowUpRight, CheckCircle2, Database, Download, FileText, FileUp, Menu, RefreshCw, Search, ShieldAlert, SlidersHorizontal, Upload, X } from 'lucide-react'
import { getEntities, getEntity, getFindings, getPeers, runAiAction, uploadDataset, uploadSingleLog } from './api/client'
import MetricCard from './components/MetricCard'
import RiskBadge from './components/RiskBadge'
import Radar from './components/Radar'
import EvidenceDiff from './components/EvidenceDiff'

const emptyData = { entities: [], findings: [], peers: [] }
const requiredFiles = ['entities.csv', 'assets.csv', 'alerts.csv', 'cases.csv']
const navItems = [{ id: 'overview', label: 'Overview', icon: Activity }, { id: 'findings', label: 'Findings', icon: ShieldAlert }, { id: 'evidence', label: 'Evidence', icon: Database }, { id: 'peers', label: 'Peer comparison', icon: ArrowUpRight }]

export default function App() {
  const [data, setData] = useState(emptyData)
  const [selected, setSelected] = useState(null)
  const [selectedFinding, setSelectedFinding] = useState(null)
  const [filters, setFilters] = useState({ search: '', severity: 'all', detector: 'all', sector: 'all' })
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const [uploading, setUploading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [aiBusy, setAiBusy] = useState('')
  const [mobileNav, setMobileNav] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState({})
  const fileInput = useRef(null)

  const refresh = async (showSpinner = false) => {
    if (showSpinner) setRefreshing(true)
    setError('')
    try {
      const [entities, findings, peers] = await Promise.all([getEntities(), getFindings(), getPeers()])
      setData({ entities, findings, peers })
      if (entities[0]) setSelected(await getEntity(entities[0].id))
      setStatus('Analysis refreshed just now')
    } catch {
      setError('The local API is unavailable. Start FastAPI on port 8000, then refresh.')
    } finally { setRefreshing(false) }
  }

  const submitFiles = async fileList => {
    const incoming = [...fileList]
    const arbitrary = incoming.find(file => !requiredFiles.includes(file.name.toLowerCase()))
    if (arbitrary) {
      setUploading(true); setError(''); setStatus(`Analyzing ${arbitrary.name} as a single log dataset...`)
      try {
        const result = await uploadSingleLog(arbitrary)
        await refresh(); setStatus(`${result.rows.toLocaleString()} log rows analyzed · ${result.findings} findings found`)
      } catch (requestError) { setError(requestError.message || 'Log CSV analysis failed.'); setStatus('Upload rejected') }
      finally { setUploading(false); setSelectedFiles({}); if (fileInput.current) fileInput.current.value = '' }
      return
    }
    const files = { ...selectedFiles, ...Object.fromEntries(incoming.map(file => [file.name.toLowerCase(), file])) }
    setSelectedFiles(files)
    const missing = requiredFiles.filter(name => !files[name])
    if (missing.length) { setError(''); setStatus(`Added ${requiredFiles.filter(name => files[name]).length}/4 files. Add: ${missing.join(', ')}`); return }
    setUploading(true); setError(''); setStatus('Validating schema, references, and evidence...')
    try {
      const result = await uploadDataset({ entities: files['entities.csv'], assets: files['assets.csv'], alerts: files['alerts.csv'], cases: files['cases.csv'] })
      await refresh(); setStatus(`${result.entities} entities analyzed · ${result.findings} findings found`)
      document.getElementById('overview')?.scrollIntoView({ behavior: 'smooth' })
    } catch (requestError) { setError(requestError.message || 'Upload validation failed.'); setStatus('Upload rejected') }
    finally { setUploading(false); setSelectedFiles({}); if (fileInput.current) fileInput.current.value = '' }
  }
  const handleDrop = event => { event.preventDefault(); submitFiles(event.dataTransfer.files) }
  const jumpTo = id => { setMobileNav(false); document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }
  const updateFilter = (key, value) => setFilters(current => ({ ...current, [key]: value }))
  const resetFilters = () => setFilters({ search: '', severity: 'all', detector: 'all', sector: 'all' })
  const runAssistant = async action => {
    if (!activeFinding) return
    setAiBusy(action); setError('')
    try {
      const result = await runAiAction(activeFinding.id, action)
      setSelectedFinding(result.finding)
      setData(current => ({ ...current, findings: current.findings.map(item => item.id === result.finding.id ? result.finding : item) }))
      setStatus(result.generated ? 'Ollama draft generated · human review required' : 'Ollama unavailable · evidence-backed fallback shown')
    } catch (requestError) { setError(requestError.message || 'AI action failed.') }
    finally { setAiBusy('') }
  }
  useEffect(() => { refresh() }, [])

  const sectors = useMemo(() => [...new Set(data.peers.map(peer => peer.sector))].sort(), [data.peers])
  const detectors = useMemo(() => [...new Set(data.findings.map(finding => finding.detector))].sort(), [data.findings])
  const filteredEntities = useMemo(() => data.entities.filter(entity => { const query = filters.search.toLowerCase(); return (!query || `${entity.name} ${entity.sector} ${entity.region}`.toLowerCase().includes(query)) && (filters.sector === 'all' || entity.sector === filters.sector) }), [data.entities, filters.search, filters.sector])
  const filteredFindings = useMemo(() => data.findings.filter(finding => (filters.severity === 'all' || finding.severity === filters.severity) && (filters.detector === 'all' || finding.detector === filters.detector) && (!filters.search || `${finding.title} ${finding.detector}`.toLowerCase().includes(filters.search.toLowerCase()))), [data.findings, filters.detector, filters.search, filters.severity])
  const critical = data.findings.filter(finding => finding.severity === 'critical').length
  const high = data.findings.filter(finding => finding.severity === 'high').length
  const average = data.entities.length ? Math.round(data.entities.reduce((sum, entity) => sum + entity.risk_score, 0) / data.entities.length) : 0
  const dimensions = selected?.dimensions || []
  const activeFinding = selectedFinding || data.findings.find(finding => finding.detector === 'investigation')

  return <div className="app-shell">
    <aside className={`sidebar ${mobileNav ? 'open' : ''}`}>
      <div className="brand"><div className="brand-mark">S</div><div><b>SAT / SA</b><span>Supervisory assurance</span></div><button className="icon-button close-nav" aria-label="Close navigation" onClick={() => setMobileNav(false)}><X size={18}/></button></div>
      <nav aria-label="Main navigation">{navItems.map(({ id, label, icon: Icon }) => <button className="nav-link" key={id} onClick={() => jumpTo(id)}><Icon size={17}/><span>{label}</span>{id === 'findings' && <em>{data.findings.length}</em>}</button>)}<button className="nav-link" onClick={() => fileInput.current?.click()}><FileText size={17}/><span>Load evidence</span></button></nav>
      <div className="sidebar-foot"><span className="dot"/> OFFLINE WORKSPACE<small>SQLite · local processing</small></div>
    </aside>

    <main className="content">
      <header className="topbar"><div className="title-block"><button className="icon-button menu-button" aria-label="Open navigation" onClick={() => setMobileNav(true)}><Menu size={20}/></button><div><p className="eyebrow">NCIIPC / CONTROL ROOM</p><h1>Evidence assurance review</h1><p className="muted">Find the signals hidden inside operational evidence.</p></div></div><div className="top-actions"><button className="button secondary" onClick={() => refresh(true)} disabled={refreshing}><RefreshCw size={16} className={refreshing ? 'spin' : ''}/><span>{refreshing ? 'Refreshing' : 'Refresh'}</span></button><input ref={fileInput} type="file" accept=".csv" multiple hidden onChange={event => submitFiles(event.target.files)}/><button className="button primary" onClick={() => fileInput.current?.click()} disabled={uploading}><Upload size={16}/><span>{uploading ? 'Analyzing' : 'Upload CSV'}</span></button></div></header>
      {error && <div className="notice error"><AlertTriangle size={17}/><span>{error}</span><button className="icon-button" aria-label="Dismiss error" onClick={() => setError('')}><X size={16}/></button></div>}
      {status && !error && <div className="notice success"><CheckCircle2 size={17}/><span>{status}</span></div>}

      <section className="upload-banner glass-panel" onDragOver={event => event.preventDefault()} onDrop={handleDrop}><div className="upload-icon"><FileUp size={23}/></div><div className="upload-copy"><p className="eyebrow">{data.entities.length ? 'DATASET ANALYZED' : 'START WITH EVIDENCE'}</p><h2>{data.entities.length ? `${data.entities.length} entities analyzed successfully` : 'Upload one log CSV or four normalized CSVs'}</h2><p>{data.entities.length ? `${data.findings.length} findings are ready. Upload another CSV to replace this dataset.` : `A single log CSV such as Timestamp, Source_IP, Event_Type, Status, Description, and Investigation_Notes works directly. The normalized four-file workflow is also supported.`} {requiredFiles.filter(name => selectedFiles[name]).length > 0 && `${requiredFiles.filter(name => selectedFiles[name]).length}/4 normalized files selected.`}</p>{requiredFiles.some(name => selectedFiles[name]) && <div className="file-chips">{requiredFiles.map(name => <span className={selectedFiles[name] ? 'file-chip ready' : 'file-chip'} key={name}>{selectedFiles[name] ? '✓' : '○'} {name}</span>)}</div>}</div><button className="button secondary" onClick={() => fileInput.current?.click()}><Upload size={16}/> Upload CSV</button></section>
      <section className="metrics" id="overview"><MetricCard label="Portfolio risk" value={data.entities.length ? `${average}/100` : '—'} detail="weighted supervisory index" accent="amber"/><MetricCard label="Critical findings" value={data.entities.length ? critical : '—'} detail="requires immediate response" accent="red"/><MetricCard label="High findings" value={data.entities.length ? high : '—'} detail="control weakness detected" accent="orange"/><MetricCard label="Entities monitored" value={data.entities.length || '—'} detail={`across ${sectors.length} sectors`}/></section>
      <section className="filter-bar glass-panel" aria-label="Evidence filters"><div className="search-field"><Search size={17}/><input aria-label="Search evidence" placeholder="Search entities or findings..." value={filters.search} onChange={event => updateFilter('search', event.target.value)}/>{filters.search && <button className="clear-search" onClick={() => updateFilter('search', '')}><X size={15}/></button>}</div><div className="filter-control"><SlidersHorizontal size={15}/><span>Filter</span></div><label><span>Severity</span><select value={filters.severity} onChange={event => updateFilter('severity', event.target.value)}><option value="all">All severities</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option></select></label><label><span>Detector</span><select value={filters.detector} onChange={event => updateFilter('detector', event.target.value)}><option value="all">All detectors</option>{detectors.map(detector => <option key={detector} value={detector}>{detector.replaceAll('_', ' ')}</option>)}</select></label><label><span>Sector</span><select value={filters.sector} onChange={event => updateFilter('sector', event.target.value)}><option value="all">All sectors</option>{sectors.map(sector => <option key={sector} value={sector}>{sector}</option>)}</select></label><button className="text-button" onClick={resetFilters}>Reset</button></section>

      <section className="workspace-grid"><div className="glass-panel entity-panel"><div className="panel-head"><div><p className="eyebrow">01 / ENTITY ASSESSMENT</p><h2>Portfolio entities</h2></div><span className="live"><span className="dot"/> live index</span></div><div className="entity-list">{filteredEntities.map(entity => <button className={`entity-row ${selected?.entity?.id === entity.id ? 'selected' : ''}`} key={entity.id} onClick={async () => setSelected(await getEntity(entity.id))}><span className="entity-code">{entity.id.replace('ent-', '#')}</span><span className="entity-name"><b>{entity.name}</b><small>{entity.sector} · {entity.region}</small></span><RiskBadge score={entity.risk_score}/><ArrowUpRight size={15}/></button>)}{!filteredEntities.length && <div className="empty">No entities match the current filters.</div>}</div></div>
        <div className="glass-panel detail-panel"><div className="panel-head"><div><p className="eyebrow">02 / DIMENSION PROFILE</p><h2>{selected?.entity?.name || 'Awaiting uploaded evidence'}</h2></div>{selected && <RiskBadge score={selected.entity.risk_score} level={selected.entity.risk_level}/>}</div>{selected ? <><div className="profile-grid"><Radar data={dimensions}/><div className="dimension-list">{dimensions.map(dimension => <div className="dimension" key={dimension.dimension}><div><span>{dimension.dimension}</span><b>{Math.round(dimension.score)}</b></div><div className="bar"><i style={{ width: `${dimension.score}%` }}/></div></div>)}</div></div><div className="detail-foot"><span>Sector median</span><b>{data.peers.find(peer => peer.entity_id === selected.entity.id)?.sector_median ?? '—'}</b><span>Variance</span><b className={selected.entity.risk_score > 35 ? 'negative' : 'positive'}>{selected.entity.risk_score > 35 ? '+' : '-'}{Math.abs(Math.round(selected.entity.risk_score - (data.peers.find(peer => peer.entity_id === selected.entity.id)?.sector_median || 0)))}</b></div></> : <div className="empty">Upload all four CSV files to calculate an assessment.</div>}</div></section>

      <section className="lower-grid"><div className="glass-panel findings-panel" id="findings"><div className="panel-head"><div><p className="eyebrow">03 / SUPERVISORY FINDINGS</p><h2>Signals requiring review</h2></div><span className="count">{filteredFindings.length} / {data.findings.length}</span></div><div className="finding-list">{filteredFindings.map(finding => <button className={`finding ${selectedFinding?.id === finding.id ? 'active' : ''}`} key={finding.id} onClick={() => { setSelectedFinding(finding); jumpTo('evidence') }}><span className={`severity ${finding.severity}`}>{finding.severity}</span><span><b>{finding.title}</b><small>{finding.detector} · {Math.round(finding.confidence * 100)}% confidence · {finding.priority}</small></span><ArrowUpRight size={15}/></button>)}{!filteredFindings.length && <div className="empty">No findings match these filters.</div>}</div></div><div className="glass-panel evidence-panel" id="evidence"><div className="panel-head"><div><p className="eyebrow">04 / EVIDENCE LENS</p><h2>Evidence → assistant → report</h2></div><span className="similarity">{activeFinding?.evidence?.matches?.[0]?.similarity || '—'}</span></div><EvidenceDiff finding={activeFinding}/>{activeFinding && <><div className="ai-actions"><button className="button secondary" onClick={() => runAssistant('explain')} disabled={!!aiBusy}><FileText size={15}/> {aiBusy === 'explain' ? 'Explaining...' : 'AI explanation'}</button><button className="button secondary" onClick={() => runAssistant('recommend')} disabled={!!aiBusy}><ShieldAlert size={15}/> {aiBusy === 'recommend' ? 'Drafting...' : 'Recommendation'}</button><button className="button secondary" onClick={() => runAssistant('notice')} disabled={!!aiBusy}><FileText size={15}/> {aiBusy === 'notice' ? 'Drafting...' : 'Show-cause draft'}</button></div><div className="assistant-output"><span>AI output / human review required</span><p>{activeFinding.notice || activeFinding.explanation || activeFinding.recommendation}</p></div><div className="evidence-actions"><button className="button secondary" onClick={() => navigator.clipboard?.writeText(activeFinding.explanation || '')}><FileText size={15}/> Copy output</button><button className="button secondary" onClick={() => window.open(`http://localhost:8000/api/reports/${activeFinding.entity_id}.pdf`, '_blank')}><Download size={15}/> Export report</button></div></>}</div></section>
      <section className="peer-strip glass-panel" id="peers"><div><p className="eyebrow">05 / PEER COMPARISON</p><h2>Entity versus sector median</h2></div><div className="peer-bars">{data.peers.slice(0, 8).map(peer => <button className="peer-bar" key={peer.entity_id} onClick={async () => { setSelected(await getEntity(peer.entity_id)); jumpTo('overview') }}><span>{peer.name}</span><i><b style={{ width: `${Math.min(peer.risk_score, 100)}%` }}/><em style={{ left: `${Math.min(peer.sector_median, 100)}%` }}/></i><strong>{Math.round(peer.risk_score)}</strong></button>)}</div></section>
      <footer><span>{status || 'Local processing only'}</span><span>SQLite workspace · no evidence leaves this machine</span></footer>
    </main>
  </div>
}
