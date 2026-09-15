import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..explainer.ollama import generate_assistant
from ..models import Finding
from .entities import finding_json

router = APIRouter(prefix='/api/findings', tags=['ai'])

@router.post('/{finding_id}/ai/{action}')
def ai_action(finding_id: str, action: str, db: Session = Depends(get_db)):
    if action not in {'explain', 'recommend', 'notice', 'summary'}:
        raise HTTPException(400, 'Unsupported AI action')
    finding = db.get(Finding, finding_id)
    if not finding:
        raise HTTPException(404, 'Finding not found')
    payload = finding_json(finding)
    result, generated = generate_assistant(action, payload)
    if action == 'explain': finding.explanation = result
    elif action == 'recommend': finding.recommendation = result
    elif action == 'notice': finding.notice = result
    finding.ai_generated = generated
    db.commit()
    return {'action': action, 'generated': generated, 'content': result, 'finding': finding_json(finding)}