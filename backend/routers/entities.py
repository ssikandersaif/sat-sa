from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Entity, DimensionScore, Finding

router = APIRouter(prefix='/api/entities', tags=['entities'])

@router.get('')
def list_entities(db: Session = Depends(get_db)):
    return [{'id': e.id, 'name': e.name, 'sector': e.sector, 'region': e.region, 'risk_score': e.risk_score, 'risk_level': e.risk_level} for e in db.query(Entity).order_by(Entity.risk_score.asc()).all()]

@router.get('/{entity_id}')
def entity_detail(entity_id: str, db: Session = Depends(get_db)):
    entity = db.get(Entity, entity_id)
    if not entity:
        raise HTTPException(404, 'Entity not found')
    scores = db.query(DimensionScore).filter_by(entity_id=entity_id).all()
    findings = db.query(Finding).filter_by(entity_id=entity_id).all()
    return {'entity': {'id': entity.id, 'name': entity.name, 'sector': entity.sector, 'region': entity.region, 'risk_score': entity.risk_score, 'risk_level': entity.risk_level}, 'dimensions': [{'dimension': s.dimension, 'score': s.score, 'weight': s.weight, 'contribution': s.contribution, 'rationale': s.rationale} for s in scores], 'findings': [finding_json(f) for f in findings]}

def finding_json(f):
    import json
    try: evidence = json.loads(f.evidence)
    except json.JSONDecodeError: evidence = f.evidence
    def decode(value, fallback):
        try: return json.loads(value)
        except (TypeError, json.JSONDecodeError): return fallback
    return {'id': f.id, 'entity_id': f.entity_id, 'detector': f.detector, 'finding_type': f.finding_type, 'title': f.title, 'severity': f.severity, 'priority': f.priority, 'confidence': f.confidence, 'description': f.description, 'detection_method': f.detection_method, 'affected_assets': decode(f.affected_assets, []), 'affected_cases': decode(f.affected_cases, []), 'evidence_ids': decode(f.evidence_ids, []), 'metrics': decode(f.metrics, {}), 'evidence': evidence, 'explanation': f.explanation, 'recommendation': f.recommendation, 'notice': f.notice, 'ai_generated': f.ai_generated}
