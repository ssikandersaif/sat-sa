from pydantic import BaseModel, Field

class FindingOut(BaseModel):
    id: str
    entity_id: str
    detector: str
    finding_type: str
    title: str
    severity: str
    priority: str
    confidence: float
    description: str
    detection_method: str
    affected_assets: list[str]
    affected_cases: list[str]
    evidence_ids: list[str]
    metrics: dict
    evidence: str
    explanation: str
    recommendation: str
    notice: str
    ai_generated: bool
    model_config = {'from_attributes': True}

class EntityOut(BaseModel):
    id: str
    name: str
    sector: str
    region: str
    risk_score: float
    risk_level: str
    model_config = {'from_attributes': True}

class ScoreOut(BaseModel):
    dimension: str
    score: float
    weight: float
    contribution: float
    rationale: str
    model_config = {'from_attributes': True}
