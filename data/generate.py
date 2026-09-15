import csv
import random
from datetime import datetime, timedelta, UTC
from pathlib import Path
ROOT = Path(__file__).parent
random.seed(42)

def write(name, fields, rows):
    with (ROOT / name).open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)

entities = [
    {'id': f'ent-{index:03d}', 'name': f'{sector} Operator {index:02d}', 'sector': sector, 'region': region}
    for index, (sector, region) in enumerate([
        ('Energy', 'North'), ('Financial Services', 'West'), ('Water', 'South'), ('Transport', 'East'),
        ('Telecommunications', 'Central'), ('Healthcare', 'North'), ('Defence', 'West'), ('Manufacturing', 'South'),
        ('Energy', 'East'), ('Water', 'Central'), ('Transport', 'North'), ('Telecommunications', 'South'),
    ], start=1)
]
write('entities.csv', ['id','name','sector','region'], entities)

assets = []
for entity in entities:
    for asset_number in range(1, 9):
        assets.append({
            'id': f"asset-{len(assets) + 1:05d}", 'entity_id': entity['id'],
            'name': f"{entity['name']} asset {asset_number:02d}",
            'asset_type': 'OT' if asset_number % 2 else 'IT',
            'criticality': 'critical' if asset_number <= 2 else 'high',
            'telemetry_enabled': 'false' if entity['id'] in {'ent-003', 'ent-010'} and asset_number <= 2 else 'true',
        })
write('assets.csv', ['id','entity_id','name','asset_type','criticality','telemetry_enabled'], assets)

now = datetime.now(UTC).replace(tzinfo=None)
alerts = []
cases = []
narratives = [
    'Reviewed alert source and confirmed normal operations. No customer impact observed.',
    'Correlated telemetry with endpoint logs, reviewed operator actions, and confirmed containment.',
    'Validated the indicator against historical activity and documented the affected service boundary.',
    'Checked source integrity, confirmed the event was isolated, and recorded remediation evidence.',
]
for alert_number in range(1, 25001):
    entity = entities[(alert_number - 1) % len(entities)]
    entity_assets = [asset for asset in assets if asset['entity_id'] == entity['id']]
    asset = entity_assets[(alert_number // len(entities)) % len(entity_assets)]
    suspicious = alert_number % 17 == 0 or entity['id'] in {'ent-003', 'ent-010'} and alert_number % 5 == 0
    severity = 'critical' if alert_number % 13 == 0 else 'high' if alert_number % 3 else 'medium'
    opened = now - timedelta(minutes=alert_number * 7)
    closed = opened + timedelta(minutes=45 if suspicious else 13 * 60) if alert_number % 4 else None
    status = 'closed' if closed else 'open'
    escalation = 0 if suspicious or severity == 'critical' else 1
    alert_id = f'al-{alert_number:06d}'
    alerts.append({'id': alert_id, 'entity_id': entity['id'], 'asset_id': asset['id'], 'severity': severity, 'status': status, 'opened_at': opened.isoformat(), 'closed_at': closed.isoformat() if closed else '', 'escalation_level': str(escalation), 'closure_reason': 'Duplicate alert' if suspicious else 'Remediated' if closed else ''})
    if alert_number % 2 == 0 or suspicious:
        copied = suspicious and alert_number % 2 == 0
        cases.append({'id': f'case-{len(cases) + 1:06d}', 'alert_id': alert_id, 'entity_id': entity['id'], 'investigator': f'analyst-{(alert_number % 24) + 1:02d}', 'narrative': narratives[0] if copied else narratives[alert_number % len(narratives)], 'investigation_depth': '1' if suspicious else str(2 + alert_number % 4), 'sla_hours': '2' if suspicious else str(8 + alert_number % 24)})

write('alerts.csv', ['id','entity_id','asset_id','severity','status','opened_at','closed_at','escalation_level','closure_reason'], alerts)
write('cases.csv', ['id','alert_id','entity_id','investigator','narrative','investigation_depth','sla_hours'], cases)
print(f'Generated {len(entities)} entities, {len(assets)} assets, {len(alerts)} alerts, and {len(cases)} cases.')
