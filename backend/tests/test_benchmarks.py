from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.financial_engine.benchmarks.base import DirectionEnum, ThresholdRange
from app.financial_engine.benchmarks.resolver import BenchmarkResolver
from app.models.benchmark import CustomBenchmark
from app.models.document import Document, DocumentStatus
from app.models.user import User


class TestBenchmarkEngine:
    async def test_industry_benchmarks_resolution(self, db_session: AsyncSession):
        fake_user_id = uuid.uuid4()
        resolver = BenchmarkResolver(db_session)

        # ── Test 1: Technology sector ROE ──
        # Technology industry average is 18%
        # Thresholds: healthy_boundary=20%, warning_boundary=10%
        # A value of 15% should be classified as WARNING
        tech_roe = await resolver.resolve_thresholds(
            metric="roe", sector="technology", user_id=fake_user_id
        )
        assert tech_roe.source == "INDUSTRY"
        assert tech_roe.industry_average == 0.18
        assert tech_roe.evaluate(0.15) == "WARNING"
        assert tech_roe.evaluate(0.22) == "HEALTHY"
        assert tech_roe.evaluate(0.05) == "CRITICAL"

        # ── Test 2: Real Estate sector Debt Ratio (DOWN direction) ──
        # Real estate average is 65% (0.65)
        # Thresholds: healthy_boundary=0.6, warning_boundary=0.75
        # A value of 0.70 should be WARNING
        re_debt = await resolver.resolve_thresholds(
            metric="debt_ratio", sector="real_estate", user_id=fake_user_id
        )
        assert re_debt.source == "INDUSTRY"
        assert re_debt.direction == DirectionEnum.DOWN
        assert re_debt.evaluate(0.50) == "HEALTHY"  # <= 0.6
        assert re_debt.evaluate(0.70) == "WARNING"  # <= 0.75
        assert re_debt.evaluate(0.80) == "CRITICAL" # > 0.75

    async def test_user_priority_override(self, db_session: AsyncSession):
        fake_user_id = uuid.uuid4()
        resolver = BenchmarkResolver(db_session)

        # Before setting custom user thresholds, fallback to default (System ROE is 15%)
        pre_override = await resolver.resolve_thresholds(
            metric="roe", sector="technology", user_id=fake_user_id
        )
        # Default fallback because no user custom exist
        assert pre_override.source == "INDUSTRY"

        # Create user custom benchmark override for technology ROE -> make it super easy (10% is healthy)
        custom = CustomBenchmark(
            owner_id=fake_user_id,
            owner_type="USER",
            sector="technology",
            metric="roe",
            healthy_boundary=0.10,
            warning_boundary=0.05,
            direction="UP",
        )
        db_session.add(custom)
        await db_session.commit()

        # Resolve again
        post_override = await resolver.resolve_thresholds(
            metric="roe", sector="technology", user_id=fake_user_id
        )
        assert post_override.source == "USER"
        assert post_override.healthy_boundary == 0.10
        # A value of 12% is now HEALTHY under the user custom rule
        assert post_override.evaluate(0.12) == "HEALTHY"

    async def test_fallback_to_default(self, db_session: AsyncSession):
        fake_user_id = uuid.uuid4()
        resolver = BenchmarkResolver(db_session)

        # Call a fake sector that doesn't exist (e.g. "retail_luxury")
        # Should fallback to system defaults (General roe is 15%)
        fallback = await resolver.resolve_thresholds(
            metric="roe", sector="retail_luxury", user_id=fake_user_id
        )
        assert fallback.source == "DEFAULT"
        assert fallback.healthy_boundary == 0.15


class TestBenchmarksAPI:
    async def test_get_document_benchmarks_api(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        from sqlalchemy import select
        result = await db_session.execute(
            select(User).where(User.email == "fixture@example.com")
        )
        user = result.scalar_one()

        # Seed document in technology sector
        doc = Document(
            user_id=user.id,
            original_filename="tech_report.pdf",
            stored_filename="tech.pdf",
            file_path="uploads/tech.pdf",
            file_size=1024,
            mime_type="application/pdf",
            status=DocumentStatus.READY,
            sector="technology",
            parsed_data={
                "normalized_data": {
                    "net_revenue": 1000.0,
                    "net_profit": 250.0,
                    "equity": 1000.0,  # ROE = 25% (> 20% Healthy for Tech)
                }
            }
        )
        db_session.add(doc)
        await db_session.commit()

        # Call API
        response = await client.get(
            f"/api/v1/analysis/documents/{doc.id}/benchmark",
            headers=auth_headers,
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["sector"] == "technology"
        assert "ratios" in data
        
        # Verify ROE ratio comparison outputs
        roe_report = data["ratios"]["profitability"]["roe"]
        assert roe_report["value"] == 0.25
        assert roe_report["status"] == "HEALTHY"
        assert roe_report["source"] == "INDUSTRY"
        assert roe_report["thresholds"]["industry_average"] == 0.18
