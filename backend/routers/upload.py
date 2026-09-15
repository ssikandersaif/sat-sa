import csv
import io
import json
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..engine.analyzer import run_analysis
from ..models import Alert, Asset, Case, Entity

router = APIRouter(prefix='/api/ingest', tags=['ingest'])

REQUIRED_COLUMNS = {
    'entities.csv': {'id', 'name', 'sector', 'region'},
    'assets.csv': {'id', 'entity_id', 'name', 'asset_type', 'criticality', 'telemetry_enabled'},
    'alerts.csv': {'id', 'entity_id', 'asset_id', 'severity', 'status', 'opened_at', 'closed_at', 'escalation_level', 'closure_reason'},
    'cases.csv': {'id', 'alert_id', 'entity_id', 'investigator', 'narrative', 'investigation_depth', 'sla_hours'},
}

def parse_csv(filename, content):
    if filename not in REQUIRED_COLUMNS:
        raise HTTPException(400, f'Expected one of: {", ".join(REQUIRED_COLUMNS)}')
    try:
        rows = list(csv.DictReader(io.StringIO(content.decode('utf-8-sig'))))
    except (UnicodeDecodeError, csv.Error) as error:
        raise HTTPException(400, f'{filename} is not valid UTF-8 CSV: {error}') from error
    columns = set(rows[0]) if rows else set()
    missing = REQUIRED_COLUMNS[filename] - columns
    if missing:
        raise HTTPException(400, f'{filename} is missing columns: {", ".join(sorted(missing))}')
    if not rows:
        raise HTTPException(400, f'{filename} has no data rows')
    ids = [row.get('id', '') for row in rows]
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        raise HTTPException(400, f'{filename} contains duplicate or empty id values')
    return rows

def parse_log_csv(content):
    try:
        reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig')))
        rows = list(reader)
    except (UnicodeDecodeError, csv.Error) as error:
        raise HTTPException(400, f'Log file is not valid UTF-8 CSV: {error}') from error
    if not rows or not reader.fieldnames:
        raise HTTPException(400, 'The CSV has no header or data rows')
    normalized = {name.strip().lower().replace(' ', '_'): name for name in reader.fieldnames}
    timestamp = next((normalized[key] for key in ('timestamp', 'ts', 'time', 'datetime', 'date') if key in normalized), None)
    if not timestamp:
        raise HTTPException(400, 'Could not identify a timestamp column. Expected Timestamp, ts, time, or datetime.')
    return rows, normalized, timestamp

def value(row, columns, *names):
    for name in names:
        if name in columns:
            return (row.get(columns[name]) or '').strip()
    return ''

@router.post('/single')
async def upload_single_log(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(400, 'Upload a CSV file')
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(413, 'Log file exceeds the 50 MB limit')
    rows, columns, timestamp_column = parse_log_csv(content)
    db: Session = SessionLocal()
    try:
        for model in (Case, Alert, Asset, Entity):
            db.query(model).delete()
        entity_id = 'uploaded-log'
        entity = Entity(id=entity_id, name=Path(file.filename).stem, sector='Uploaded log dataset', region='Local', risk_score=0)
        db.add(entity)
        assets = {}
        alerts = []
        cases = []
        base_time = datetime.utcnow()
        for index, row in enumerate(rows, start=1):
            source = value(row, columns, 'source_ip', 'src_ip', 'ip', 'user_account') or 'unknown-source'
            asset_id = f'log-source-{source.replace(".", "-").replace(":", "-")}'[:80]
            if asset_id not in assets:
                assets[asset_id] = Asset(id=asset_id, entity_id=entity_id, name=source, asset_type='LOG_SOURCE', criticality='high', telemetry_enabled=True)
            timestamp_value = value(row, columns, 'timestamp', 'ts', 'time', 'datetime', 'date')
            try:
                opened = datetime.fromisoformat(timestamp_value.replace('Z', '+00:00')).replace(tzinfo=None)
            except ValueError:
                opened = base_time - timedelta(seconds=index)
            status = value(row, columns, 'status', 'severity', 'level').lower()
            description = value(row, columns, 'description', 'event_description', 'event_type', 'message')
            notes = value(row, columns, 'investigation_notes', 'notes_investigation', 'notes', 'investigation')
            combined = f'{description} {notes}'.strip()
            severity = 'critical' if any(word in f'{status} {combined}'.lower() for word in ('critical', 'suspicious', 'error', 'failed', 'bypass', 'without_investigation')) else 'high' if 'warning' in status else 'medium'
            is_closed = any(word in f'{status} {combined}'.lower() for word in ('closed', 'resolved', 'remediated'))
            alert_id = f'log-alert-{index:08d}'
            closed = opened + timedelta(minutes=5) if is_closed else None
            alerts.append(Alert(id=alert_id, entity_id=entity_id, asset_id=asset_id, severity=severity, status='closed' if is_closed else 'open', opened_at=opened, closed_at=closed, escalation_level=0 if severity in ('critical', 'high') else 1, closure_reason='Imported from log status' if is_closed else ''))
            if combined:
                cases.append(Case(id=f'log-case-{index:08d}', alert_id=alert_id, entity_id=entity_id, investigator=value(row, columns, 'user_account', 'user', 'investigator') or 'imported-log', narrative=combined, investigation_depth=1 if 'without_investigation' in combined.lower() else 2, sla_hours=2 if is_closed else 24))
        db.add_all(list(assets.values()) + alerts + cases)
        db.commit()
        result = run_analysis(db)
        return {'status': 'analyzed', 'mode': 'single_log', 'filename': file.filename, 'columns': list(columns), 'rows': len(rows), **result}
    except (ValueError, KeyError) as error:
        db.rollback()
        raise HTTPException(400, f'Could not normalize this log CSV: {error}') from error
    finally:
        db.close()

@router.post('/upload')
async def upload_dataset(entities: UploadFile = File(...), assets: UploadFile = File(...), alerts: UploadFile = File(...), cases: UploadFile = File(...)):
    files = {'entities.csv': entities, 'assets.csv': assets, 'alerts.csv': alerts, 'cases.csv': cases}
    contents = {}
    for expected, file in files.items():
        if not file.filename.lower().endswith('.csv'):
            raise HTTPException(400, f'{file.filename} must be a CSV file')
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(413, f'{file.filename} exceeds the 10 MB limit')
        contents[expected] = parse_csv(expected, content)

    db: Session = SessionLocal()
    try:
        for model in (Case, Alert, Asset, Entity):
            db.query(model).delete()
        entity_rows = contents['entities.csv']
        asset_rows = contents['assets.csv']
        alert_rows = contents['alerts.csv']
        case_rows = contents['cases.csv']
        entity_ids = {row['id'] for row in entity_rows}
        asset_ids = {row['id'] for row in asset_rows}
        alert_ids = {row['id'] for row in alert_rows}
        if any(row['entity_id'] not in entity_ids for row in asset_rows + alert_rows + case_rows):
            raise HTTPException(400, 'Every asset, alert, and case must reference an entity')
        if any(row['asset_id'] not in asset_ids for row in alert_rows) or any(row['alert_id'] not in alert_ids for row in case_rows):
            raise HTTPException(400, 'Alerts and cases contain unknown references')
        db.add_all([Entity(id=r['id'], name=r['name'], sector=r['sector'], region=r['region']) for r in entity_rows])
        db.add_all([Asset(id=r['id'], entity_id=r['entity_id'], name=r['name'], asset_type=r['asset_type'], criticality=r['criticality'], telemetry_enabled=r['telemetry_enabled'].lower() == 'true') for r in asset_rows])
        db.add_all([Alert(id=r['id'], entity_id=r['entity_id'], asset_id=r['asset_id'], severity=r['severity'], status=r['status'], opened_at=datetime.fromisoformat(r['opened_at']), closed_at=datetime.fromisoformat(r['closed_at']) if r['closed_at'] else None, escalation_level=int(r['escalation_level']), closure_reason=r['closure_reason']) for r in alert_rows])
        db.add_all([Case(id=r['id'], alert_id=r['alert_id'], entity_id=r['entity_id'], investigator=r['investigator'], narrative=r['narrative'], investigation_depth=int(r['investigation_depth']), sla_hours=float(r['sla_hours'])) for r in case_rows])
        db.commit()
        result = run_analysis(db)
        return {'status': 'analyzed', 'files': list(files), **result}
    except (ValueError, KeyError) as error:
        db.rollback()
        raise HTTPException(400, f'Invalid value in uploaded CSV: {error}') from error
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
