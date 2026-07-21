from __future__ import annotations

import pytest

from app.financial_engine.formulas import FinancialFormulas
from app.financial_engine.ratios import FinancialRatioCalculator


class TestFinancialFormulas:
    def test_basic_safe_division(self):
        assert FinancialFormulas.ratio(10, 2) == 5.0
        assert FinancialFormulas.ratio(10, 0) is None
        assert FinancialFormulas.ratio(None, 5) is None

    def test_gross_margin(self):
        assert FinancialFormulas.gross_margin(40, 100) == 0.40
        assert FinancialFormulas.gross_margin(None, 100) is None

    def test_quick_ratio(self):
        # (current_assets - inventory) / current_liabilities
        # (100 - 20) / 40 = 2.0
        assert FinancialFormulas.quick_ratio(100, 20, 40) == 2.0
        # If inventory is missing, fallback to 0 -> 100 / 40 = 2.5
        assert FinancialFormulas.quick_ratio(100, None, 40) == 2.5


class TestFinancialRatioCalculator:
    @pytest.mark.asyncio
    async def test_calculation_threshold_matching(self, db_session):
        normalized_data = {
            "net_revenue": 1000.0,
            "gross_profit": 400.0,
            "net_profit": 200.0,
            "total_assets": 2000.0,
            "short_term_assets": 800.0,
            "total_liabilities": 600.0,
            "short_term_liabilities": 400.0,
            "equity": 1000.0,
        }

        import uuid
        user_id = uuid.uuid4()
        ratios = await FinancialRatioCalculator.calculate_ratios(normalized_data, db_session, user_id)

        # 1. Profitability ROE check
        # ROE = 200 / 1000 = 20% (> 15% Healthy)
        assert ratios["profitability"]["roe"]["value"] == 0.20
        assert ratios["profitability"]["roe"]["status"] == "HEALTHY"

        # 2. Solvency Debt Ratio check
        # Debt ratio = 600 / 2000 = 30% (< 50% Healthy)
        assert ratios["solvency"]["debt_ratio"]["value"] == 0.30
        assert ratios["solvency"]["debt_ratio"]["status"] == "HEALTHY"

        # 3. Liquidity Current Ratio check
        # Current ratio = 800 / 400 = 2.0 (> 1.5 Healthy)
        assert ratios["liquidity"]["current_ratio"]["value"] == 2.0
        assert ratios["liquidity"]["current_ratio"]["status"] == "HEALTHY"

    @pytest.mark.asyncio
    async def test_critical_threshold_matching(self, db_session):
        normalized_data = {
            "net_revenue": 1000.0,
            "gross_profit": 100.0,
            "net_profit": 10.0,
            "total_assets": 2000.0,
            "short_term_assets": 200.0,
            "total_liabilities": 1800.0,
            "short_term_liabilities": 800.0,
            "equity": 200.0,
        }

        import uuid
        user_id = uuid.uuid4()
        ratios = await FinancialRatioCalculator.calculate_ratios(normalized_data, db_session, user_id)

        # 1. ROE = 10 / 200 = 5% (>= 5% -> Warning, < 5% Critical)
        assert ratios["profitability"]["roe"]["value"] == 0.05
        assert ratios["profitability"]["roe"]["status"] == "WARNING"

        # 2. Debt ratio = 1800 / 2000 = 90% (> 70% Critical)
        assert ratios["solvency"]["debt_ratio"]["value"] == 0.90
        assert ratios["solvency"]["debt_ratio"]["status"] == "CRITICAL"

        # 3. Current ratio = 200 / 800 = 0.25 (< 1.0 Critical)
        assert ratios["liquidity"]["current_ratio"]["value"] == 0.25
        assert ratios["liquidity"]["current_ratio"]["status"] == "CRITICAL"
