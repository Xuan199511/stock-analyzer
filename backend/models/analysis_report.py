"""SQLAlchemy model for cached deep-analysis reports."""
from datetime import datetime

from sqlalchemy import Index, Integer, String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol:     Mapped[str]      = mapped_column(String(16),  index=True, nullable=False)
    market:     Mapped[str]      = mapped_column(String(4),   index=True, nullable=False)  # TW / US
    report_json: Mapped[str]     = mapped_column(Text,        nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime,    default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime,    nullable=False)

    __table_args__ = (
        Index("ix_symbol_market", "symbol", "market"),
    )
