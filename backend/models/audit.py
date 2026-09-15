from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base

class Entity(Base):
    __tablename__ = 'entities'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    sector: Mapped[str] = mapped_column(String, index=True)
    region: Mapped[str] = mapped_column(String, default='India')
    risk_score: Mapped[float] = mapped_column(Float, default=0)
    risk_level: Mapped[str] = mapped_column(String, default='Critical')
    assets = relationship('Asset', back_populates='entity', cascade='all, delete-orphan')
    findings = relationship('Finding', back_populates='entity', cascade='all, delete-orphan')

class Asset(Base):
    __tablename__ = 'assets'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey('entities.id'), index=True)
    name: Mapped[str] = mapped_column(String)
    asset_type: Mapped[str] = mapped_column(String)
    criticality: Mapped[str] = mapped_column(String, default='high')
    telemetry_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    entity = relationship('Entity', back_populates='assets')

class Alert(Base):
    __tablename__ = 'alerts'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey('entities.id'), index=True)
    asset_id: Mapped[str] = mapped_column(String, index=True)
    severity: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    opened_at: Mapped[datetime] = mapped_column(DateTime)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    escalation_level: Mapped[int] = mapped_column(Integer, default=0)
    closure_reason: Mapped[str] = mapped_column(Text, default='')

class Case(Base):
    __tablename__ = 'cases'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    alert_id: Mapped[str] = mapped_column(String, index=True)
    entity_id: Mapped[str] = mapped_column(String, index=True)
    investigator: Mapped[str] = mapped_column(String)
    narrative: Mapped[str] = mapped_column(Text)
    investigation_depth: Mapped[int] = mapped_column(Integer, default=1)
    sla_hours: Mapped[float] = mapped_column(Float, default=24)

class Finding(Base):
    __tablename__ = 'findings'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey('entities.id'), index=True)
    detector: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    finding_type: Mapped[str] = mapped_column(String, default='operational_control')
    severity: Mapped[str] = mapped_column(String)
    priority: Mapped[str] = mapped_column(String, default='P2')
    confidence: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text, default='')
    detection_method: Mapped[str] = mapped_column(Text, default='')
    affected_assets: Mapped[str] = mapped_column(Text, default='[]')
    affected_cases: Mapped[str] = mapped_column(Text, default='[]')
    evidence_ids: Mapped[str] = mapped_column(Text, default='[]')
    metrics: Mapped[str] = mapped_column(Text, default='{}')
    recommendation: Mapped[str] = mapped_column(Text, default='')
    evidence: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text, default='')
    notice: Mapped[str] = mapped_column(Text, default='')
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    entity = relationship('Entity', back_populates='findings')

class DimensionScore(Base):
    __tablename__ = 'dimension_scores'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey('entities.id'), index=True)
    dimension: Mapped[str] = mapped_column(String)
    score: Mapped[float] = mapped_column(Float)
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    contribution: Mapped[float] = mapped_column(Float, default=0.0)
    rationale: Mapped[str] = mapped_column(Text, default='')
