from statistics import median
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Entity

router = APIRouter(prefix='/api/peers', tags=['peers'])

@router.get('/summary')
def peer_summary(db: Session = Depends(get_db)):
    entities = db.query(Entity).all()
    sectors = {}
    for entity in entities: sectors.setdefault(entity.sector, []).append(entity.risk_score)
    return [{'entity_id': e.id, 'name': e.name, 'sector': e.sector, 'risk_score': e.risk_score, 'sector_median': round(median(sectors[e.sector]), 1)} for e in entities]
