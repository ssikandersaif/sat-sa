from fastapi.testclient import TestClient
from backend.main import app


def test_detector_and_risk_contract():
    client = TestClient(app)
    findings = client.get('/api/findings').json()
    expected = {'fast_closure', 'missing_escalation', 'repeated_no_remediation', 'investigation_similarity', 'monitoring_gap', 'peer_anomaly', 'metric_gaming'}
    assert expected.issubset({finding['detector'] for finding in findings})
    required = {'id', 'entity_id', 'priority', 'confidence', 'finding_type', 'description', 'detection_method', 'affected_assets', 'affected_cases', 'evidence_ids', 'metrics', 'recommendation'}
    assert all(required.issubset(finding) for finding in findings)
    detail = client.get('/api/entities/ent-001').json()
    assert round(sum(item['weight'] for item in detail['dimensions']), 5) == 1.0
    assert detail['entity']['risk_level'] in {'Critical', 'High', 'Medium', 'Low', 'Healthy'}


def test_ai_routes_are_human_review_labeled_when_offline():
    client = TestClient(app)
    finding = client.get('/api/findings').json()[0]
    result = client.post(f"/api/findings/{finding['id']}/ai/notice")
    assert result.status_code == 200
    assert 'human review' in result.json()['content'].lower()
