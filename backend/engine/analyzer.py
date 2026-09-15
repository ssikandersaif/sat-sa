from collections import Counter, defaultdict
from datetime import datetime
from difflib import SequenceMatcher
import json
from math import sqrt
from sqlalchemy.orm import Session
from ..models import Alert, Asset, Case, Entity, Finding, DimensionScore

DIMENSION_WEIGHTS = {
    'Detection': 0.20,
    'Investigation': 0.20,
    'Escalation': 0.15,
    'Monitoring': 0.15,
    'Operations': 0.15,
    'Governance': 0.15,
}
RISK_LEVELS = [(20, 'Critical'), (40, 'High'), (60, 'Medium'), (80, 'Low'), (100, 'Healthy')]

def risk_level(score):
    for ceiling, label in RISK_LEVELS:
        if score <= ceiling:
            return label
    return 'Healthy'

def _json(value):
    return json.dumps(value, default=str)

def _finding(entity_id, detector, title, severity, priority, confidence, description, method, evidence, assets=None, cases=None, metrics=None, recommendation=''):
    evidence_ids = evidence.get('alert_ids', []) + evidence.get('case_ids', []) + evidence.get('asset_ids', [])
    return Finding(
        id=f'{entity_id}-{detector}', entity_id=entity_id, detector=detector, finding_type=detector,
        title=title, severity=severity, priority=priority, confidence=confidence,
        description=description, detection_method=method, affected_assets=_json(assets or evidence.get('asset_ids', [])),
        affected_cases=_json(cases or evidence.get('case_ids', [])), evidence_ids=_json(evidence_ids),
        metrics=_json(metrics or {}), evidence=_json(evidence), recommendation=recommendation,
        explanation='Evidence-backed finding awaiting an AI explanation.', notice='', ai_generated=False,
    )

def _similarity(left, right):
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        vectors = TfidfVectorizer(stop_words='english').fit_transform([left, right])
        return float(cosine_similarity(vectors[0:1], vectors[1:2])[0][0])
    except ImportError:
        return SequenceMatcher(None, left, right).ratio()

def _peer_outliers(kpis):
    if len(kpis) < 4:
        return set()
    try:
        from sklearn.ensemble import IsolationForest
        matrix = [[row[key] for key in ('closure_time', 'critical_closure_rate', 'escalation_rate', 'investigation_depth', 'remediation_rate', 'monitoring_coverage')] for row in kpis]
        predictions = IsolationForest(random_state=42, contamination='auto', n_estimators=100).fit_predict(matrix)
        return {row['entity_id'] for row, prediction in zip(kpis, predictions) if prediction == -1}
    except ImportError:
        scores = []
        for key in ('closure_time', 'critical_closure_rate', 'escalation_rate', 'investigation_depth', 'remediation_rate', 'monitoring_coverage'):
            values = [row[key] for row in kpis]
            mean = sum(values) / len(values)
            deviation = sqrt(sum((value - mean) ** 2 for value in values) / len(values)) or 1
            scores.append([(row['entity_id'], abs(row[key] - mean) / deviation) for row in kpis])
        return {entity_id for values in scores for entity_id, deviation in values if deviation >= 2.0}

def _entity_kpis(entity, alerts, cases, assets):
    entity_alerts = [alert for alert in alerts if alert.entity_id == entity.id]
    entity_cases = [case for case in cases if case.entity_id == entity.id]
    entity_assets = [asset for asset in assets if asset.entity_id == entity.id]
    closed = [alert for alert in entity_alerts if alert.closed_at]
    closure_hours = [max(0, (alert.closed_at - alert.opened_at).total_seconds() / 3600) for alert in closed]
    critical = [alert for alert in entity_alerts if alert.severity == 'critical']
    critical_closed = [alert for alert in critical if alert.closed_at]
    remediated = [alert for alert in closed if alert.closure_reason and 'duplicate' not in alert.closure_reason.lower()]
    return {
        'entity_id': entity.id, 'alert_count': len(entity_alerts), 'case_count': len(entity_cases),
        'closure_time': sum(closure_hours) / len(closure_hours) if closure_hours else 0,
        'critical_closure_rate': len(critical_closed) / len(critical) if critical else 0,
        'escalation_rate': sum(alert.escalation_level > 0 for alert in entity_alerts) / len(entity_alerts) if entity_alerts else 0,
        'investigation_depth': sum(case.investigation_depth for case in entity_cases) / len(entity_cases) if entity_cases else 0,
        'remediation_rate': len(remediated) / len(closed) if closed else 0,
        'monitoring_coverage': sum(asset.telemetry_enabled for asset in entity_assets) / len(entity_assets) if entity_assets else 0,
        'evidence_attachment_rate': 0.0,
    }

def run_analysis(db: Session):
    db.query(Finding).delete()
    db.query(DimensionScore).delete()
    entities, assets = db.query(Entity).all(), db.query(Asset).all()
    alerts, cases = db.query(Alert).all(), db.query(Case).all()
    kpis = [_entity_kpis(entity, alerts, cases, assets) for entity in entities]
    outliers = _peer_outliers(kpis)
    for entity, kpi in zip(entities, kpis):
        entity_alerts = [alert for alert in alerts if alert.entity_id == entity.id]
        entity_cases = [case for case in cases if case.entity_id == entity.id]
        entity_assets = [asset for asset in assets if asset.entity_id == entity.id]
        findings = []
        closed_fast = [alert for alert in entity_alerts if alert.closed_at and (alert.closed_at - alert.opened_at).total_seconds() < 4 * 3600 and alert.severity in ('critical', 'high')]
        if closed_fast:
            findings.append(_finding(entity.id, 'fast_closure', 'High-severity alerts closed unusually quickly', 'critical', 'P1', .96, 'Critical or high alerts were closed below the four-hour review threshold.', 'Closed-at minus opened-at duration grouped by severity.', {'alert_ids': [a.id for a in closed_fast], 'count': len(closed_fast)}, metrics={'fast_closure_rate': round(len(closed_fast) / max(1, len(entity_alerts)), 4)}, recommendation='Require documented triage evidence and supervisory approval before closing high-impact alerts.'))
        missing = [alert for alert in entity_alerts if alert.severity in ('critical', 'high') and alert.escalation_level == 0]
        if missing:
            findings.append(_finding(entity.id, 'missing_escalation', 'High-impact alerts have no escalation record', 'high', 'P1', .93, 'High-impact alerts lack a recorded escalation level.', 'Severity filter followed by escalation_level == 0.', {'alert_ids': [a.id for a in missing]}, metrics={'missing_escalation_count': len(missing)}, recommendation='Define escalation ownership and require an escalation decision for every critical or high alert.'))
        repeated_assets = [asset_id for asset_id, count in Counter(a.asset_id for a in entity_alerts).items() if count >= 3]
        if repeated_assets:
            matching_alerts = [a.id for a in entity_alerts if a.asset_id in repeated_assets]
            findings.append(_finding(entity.id, 'repeated_no_remediation', 'Assets generate repeated alerts without durable remediation', 'high', 'P1', .90, 'The same assets recur in alert records without sufficient remediation evidence.', 'Group alerts by asset and flag assets with at least three alerts.', {'alert_ids': matching_alerts, 'asset_ids': repeated_assets}, assets=repeated_assets, metrics={'repeated_asset_count': len(repeated_assets)}, recommendation='Create an asset-level remediation case and verify closure evidence before suppressing recurrence.'))
        buckets = defaultdict(list)
        for case in entity_cases:
            buckets[' '.join(case.narrative.lower().split())].append(case)
        copied = []
        for bucket in buckets.values():
            for left, right in zip(bucket, bucket[1:]):
                if left.investigator == right.investigator:
                    similarity = _similarity(left.narrative, right.narrative)
                    if similarity >= .85:
                        copied.append({'case_a': left.id, 'case_b': right.id, 'similarity': round(similarity, 3), 'text_a': left.narrative, 'text_b': right.narrative})
        if copied:
            findings.append(_finding(entity.id, 'investigation_similarity', 'Investigation narratives contain suspiciously copied language', 'critical', 'P1', .98, 'Multiple investigations by the same investigator contain near-identical narrative text.', 'TF-IDF cosine similarity with normalized narrative bucketing.', {'matches': copied}, cases=[item for pair in copied for item in (pair['case_a'], pair['case_b'])], metrics={'maximum_similarity': max(pair['similarity'] for pair in copied), 'match_count': len(copied)}, recommendation='Re-perform the affected investigations and require case-specific evidence, timelines, and reviewer sign-off.'))
        gaps = [asset.id for asset in entity_assets if asset.criticality == 'critical' and not asset.telemetry_enabled]
        if gaps:
            findings.append(_finding(entity.id, 'monitoring_gap', 'Critical assets lack expected telemetry coverage', 'high', 'P1', .94, 'Critical assets are marked as having telemetry disabled.', 'Filter critical assets where telemetry_enabled is false.', {'asset_ids': gaps}, assets=gaps, metrics={'unmonitored_critical_assets': len(gaps)}, recommendation='Restore telemetry or document an approved compensating control with an expiry date.'))
        shallow = [case for case in entity_cases if case.investigation_depth <= 1 and case.sla_hours <= 4]
        if shallow:
            findings.append(_finding(entity.id, 'metric_gaming', 'Fast SLA performance is not matched by investigation depth', 'medium', 'P2', .86, 'Cases meet a short SLA while recording minimal investigation depth.', 'Compare SLA hours and investigation_depth for each case.', {'case_ids': [case.id for case in shallow]}, cases=[case.id for case in shallow], metrics={'shallow_fast_case_count': len(shallow)}, recommendation='Balance SLA reporting with minimum investigation-quality controls and sample-based review.'))
        if entity.id in outliers:
            findings.append(_finding(entity.id, 'peer_anomaly', 'Entity KPIs are statistically unusual for the peer population', 'high', 'P2', .78, 'The entity profile is an IsolationForest outlier against peer operational KPIs.', 'IsolationForest over closure, escalation, investigation, remediation, and monitoring KPIs.', {'entity_id': entity.id, 'kpis': kpi}, metrics=kpi, recommendation='Review the entity against sector peers and validate whether the operating model or reporting process explains the anomaly.'))
        dimensions = {
            'Detection': max(0, min(100, 100 - len([f for f in findings if f.detector in ('monitoring_gap', 'peer_anomaly')]) * 20)),
            'Investigation': max(0, min(100, 100 - len([f for f in findings if f.detector in ('investigation_similarity', 'metric_gaming')]) * 35)),
            'Escalation': round(kpi['escalation_rate'] * 100),
            'Monitoring': round(kpi['monitoring_coverage'] * 100),
            'Operations': max(0, min(100, 100 - len([f for f in findings if f.detector in ('fast_closure', 'repeated_no_remediation')]) * 30)),
            'Governance': max(0, min(100, 100 - len([f for f in findings if f.detector in ('missing_escalation', 'metric_gaming')]) * 30)),
        }
        entity.risk_score = round(sum(dimensions[name] * DIMENSION_WEIGHTS[name] for name in dimensions), 1)
        entity.risk_level = risk_level(entity.risk_score)
        for name, score in dimensions.items():
            weight = DIMENSION_WEIGHTS[name]
            db.add(DimensionScore(entity_id=entity.id, dimension=name, score=score, weight=weight, contribution=round(score * weight, 2), rationale=f'{name} score is traceable to uploaded operational metrics for {kpi["alert_count"]} alerts and {kpi["case_count"]} cases.'))
        db.add_all(findings)
    db.commit()
    return {'entities': len(entities), 'findings': db.query(Finding).count(), 'weights_total': sum(DIMENSION_WEIGHTS.values()) * 100}
