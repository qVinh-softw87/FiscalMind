from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.financial_engine.benchmarks.resolver import BenchmarkResolver
from app.financial_engine.formulas import FinancialFormulas


class FinancialRatioCalculator:
    """
    Financial Ratio Calculator.
    Extracts normalized variables, computes 10 core metrics, and assigns health status
    dynamically using the Benchmark Engine.
    """

    @classmethod
    async def calculate_ratios(
        cls,
        normalized_data: dict[str, Any],
        db: AsyncSession,
        user_id: uuid.UUID,
        sector: str = "general",
    ) -> dict[str, Any]:
        """
        Computes the 10 core financial ratios based on parsed document metrics.
        Evaluates health statuses using BenchmarkResolver for custom & sector thresholds.
        """
        # 1. Fetch raw variables from JSONB structure
        revenue = normalized_data.get("net_revenue") or normalized_data.get("revenue")
        gross_profit = normalized_data.get("gross_profit")
        net_profit = normalized_data.get("net_profit")
        cost_of_goods_sold = normalized_data.get("cost_of_goods_sold")
        
        total_assets = normalized_data.get("total_assets")
        short_term_assets = normalized_data.get("short_term_assets")
        inventory = normalized_data.get("inventory") or 0.0
        
        total_liabilities = normalized_data.get("total_liabilities")
        short_term_liabilities = normalized_data.get("short_term_liabilities")
        equity = normalized_data.get("equity")
        
        operating_profit = normalized_data.get("operating_profit")
        tax = normalized_data.get("tax") or 0.0
        interest = normalized_data.get("interest_expense") or 0.0
        depreciation = normalized_data.get("depreciation") or 0.0

        # Calculate Gross Profit if missing but revenue and COGS exist
        if gross_profit is None and revenue is not None and cost_of_goods_sold is not None:
            gross_profit = revenue - cost_of_goods_sold

        # ── 2. Run Computations ──
        gm = FinancialFormulas.gross_margin(gross_profit, revenue)
        nm = FinancialFormulas.net_margin(net_profit, revenue)
        op_margin = FinancialFormulas.operating_margin(operating_profit, revenue)
        roe = FinancialFormulas.roe(net_profit, equity)
        roa = FinancialFormulas.roa(net_profit, total_assets)
        
        curr_ratio = FinancialFormulas.current_ratio(short_term_assets, short_term_liabilities)
        q_ratio = FinancialFormulas.quick_ratio(short_term_assets, inventory, short_term_liabilities)
        
        debt_r = FinancialFormulas.debt_ratio(total_liabilities, total_assets)
        d_to_e = FinancialFormulas.debt_to_equity(total_liabilities, equity)
        ebitda = FinancialFormulas.ebitda(net_profit, tax, interest, depreciation)

        # ── 3. Resolve Dynamic Benchmarks ──
        resolver = BenchmarkResolver(db)

        async def _eval_ratio(metric_key: str, val: float | None) -> dict[str, Any]:
            if val is None:
                return {
                    "value": None,
                    "status": "UNKNOWN",
                    "source": "DEFAULT",
                    "thresholds": None,
                }
            threshold = await resolver.resolve_thresholds(
                metric=metric_key,
                sector=sector,
                user_id=user_id,
            )
            return {
                "value": val,
                "status": threshold.evaluate(val),
                "source": threshold.source,
                "thresholds": {
                    "healthy": threshold.healthy_boundary,
                    "warning": threshold.warning_boundary,
                    "direction": threshold.direction,
                    "industry_average": threshold.industry_average,
                }
            }

        # Compute dynamic outputs
        roe_res = await _eval_ratio("roe", roe)
        roa_res = await _eval_ratio("roa", roa)
        gm_res = await _eval_ratio("gross_margin", gm)
        nm_res = await _eval_ratio("net_margin", nm)
        op_margin_res = await _eval_ratio("operating_margin", op_margin)
        
        curr_res = await _eval_ratio("current_ratio", curr_ratio)
        quick_res = await _eval_ratio("quick_ratio", q_ratio)
        
        debt_res = await _eval_ratio("debt_ratio", debt_r)
        d_to_e_res = await _eval_ratio("debt_to_equity", d_to_e)

        # ── 4. Formulate Response Report ──
        return {
            "profitability": {
                "gross_margin": {
                    **gm_res,
                    "explanation": "Biên lợi nhuận gộp phản ánh hiệu quả sản xuất và giá vốn."
                },
                "net_margin": {
                    **nm_res,
                    "explanation": "Biên lợi nhuận ròng phản ánh tỷ lệ thu nhập thực tế trên mỗi đồng doanh thu."
                },
                "roe": {
                    **roe_res,
                    "explanation": "Hiệu suất sinh lời trên mỗi đồng vốn góp của cổ đông (ROE > 15% là tốt)."
                },
                "roa": {
                    **roa_res,
                    "explanation": "Hiệu suất sinh lời trên tổng tài sản (ROA > 6% thể hiện quản lý tài sản tốt)."
                }
            },
            "liquidity": {
                "current_ratio": {
                    **curr_res,
                    "explanation": "Khả năng chi trả nợ ngắn hạn bằng tài sản ngắn hạn (Yêu cầu > 1.0, tốt nhất > 1.5)."
                },
                "quick_ratio": {
                    **quick_res,
                    "explanation": "Khả năng thanh toán tức thời không tính hàng tồn kho (Tốt nhất > 1.0)."
                }
            },
            "solvency": {
                "debt_ratio": {
                    **debt_res,
                    "explanation": "Tỷ lệ tài sản được tài trợ bằng nợ. (> 70% biểu thị rủi ro đòn bẩy nợ cao)."
                },
                "debt_to_equity": {
                    **d_to_e_res,
                    "explanation": "Tương quan nợ phải trả trên vốn chủ sở hữu (An toàn khi tỷ lệ < 1.0)."
                }
            },
            "operations": {
                "operating_margin": {
                    **op_margin_res,
                    "explanation": "Biên lợi nhuận từ hoạt động kinh doanh cốt lõi."
                },
                "ebitda": {
                    "value": ebitda,
                    "status": "INFO",
                    "source": "DEFAULT",
                    "thresholds": None,
                    "explanation": "Lợi nhuận trước thuế, khấu hao và lãi vay (thể hiện dòng tiền hoạt động thuần)."
                }
            }
        }
