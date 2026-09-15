from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Finding
from .entities import finding_json

router = APIRouter(prefix='/api/findings', tags=['findings'])

@router.get('')
def list_findings(severity: str | None = None, entity_id: str | None = None, detector: str | None = None, priority: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Finding)
    if severity:
        query = query.filter(Finding.severity == severity)
    if entity_id:
        query = query.filter(Finding.entity_id == entity_id)
    if detector:
        query = query.filter(Finding.detector == detector)
    if priority:
        query = query.filter(Finding.priority == priority)
    return [finding_json(f) for f in query.order_by(Finding.severity.desc()).all()]
