from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Entity, Finding, DimensionScore
from reports.pdf_generator import build_report

router = APIRouter(prefix='/api/reports', tags=['reports'])
@router.get('/{entity_id}.pdf')
def report(entity_id: str, db: Session = Depends(get_db)):
    entity = db.get(Entity, entity_id)
    if not entity: raise HTTPException(404, 'Entity not found')
    stream = build_report(entity, db.query(Finding).filter_by(entity_id=entity_id).all(), db.query(DimensionScore).filter_by(entity_id=entity_id).all())
    return StreamingResponse(stream, media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename={entity_id}-supervisory-report.pdf'})
