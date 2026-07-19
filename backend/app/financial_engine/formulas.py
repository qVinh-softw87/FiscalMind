from __future__ import annotations


class FinancialFormulas:
    """
    Pure mathematical formulas for financial ratios.

    All methods handle division-by-zero or missing data gracefully
    by returning None instead of throwing runtime errors.
    """

    @staticmethod
    def ratio(numerator: float | None, denominator: float | None) -> float | None:
        """Helper to safely divide two numbers."""
        if numerator is None or denominator is None or denominator == 0:
            return None
        return round(numerator / denominator, 4)

    @classmethod
    def gross_margin(cls, gross_profit: float | None, revenue: float | None) -> float | None:
        """Lợi nhuận gộp / Doanh thu thuần"""
        return cls.ratio(gross_profit, revenue)

    @classmethod
    def net_margin(cls, net_profit: float | None, revenue: float | None) -> float | None:
        """Lợi nhuận ròng / Doanh thu thuần"""
        return cls.ratio(net_profit, revenue)

    @classmethod
    def operating_margin(
        self, operating_profit: float | None, revenue: float | None
    ) -> float | None:
        """Lợi nhuận hoạt động / Doanh thu thuần"""
        return self.ratio(operating_profit, revenue)

    @classmethod
    def roe(cls, net_profit: float | None, equity: float | None) -> float | None:
        """Lợi nhuận ròng / Vốn chủ sở hữu"""
        return cls.ratio(net_profit, equity)

    @classmethod
    def roa(cls, net_profit: float | None, total_assets: float | None) -> float | None:
        """Lợi nhuận ròng / Tổng tài sản"""
        return cls.ratio(net_profit, total_assets)

    @classmethod
    def current_ratio(
        cls, current_assets: float | None, current_liabilities: float | None
    ) -> float | None:
        """Tài sản ngắn hạn / Nợ ngắn hạn"""
        return cls.ratio(current_assets, current_liabilities)

    @classmethod
    def quick_ratio(
        cls,
        current_assets: float | None,
        inventory: float | None,
        current_liabilities: float | None,
    ) -> float | None:
        """(Tài sản ngắn hạn - Hàng tồn kho) / Nợ ngắn hạn"""
        if current_assets is None or current_liabilities is None:
            return None
        inv = inventory or 0.0
        return cls.ratio(current_assets - inv, current_liabilities)

    @classmethod
    def debt_ratio(cls, total_liabilities: float | None, total_assets: float | None) -> float | None:
        """Tổng nợ phải trả / Tổng tài sản"""
        return cls.ratio(total_liabilities, total_assets)

    @classmethod
    def debt_to_equity(cls, total_liabilities: float | None, equity: float | None) -> float | None:
        """Tổng nợ phải trả / Vốn chủ sở hữu"""
        return cls.ratio(total_liabilities, equity)

    @classmethod
    def ebitda(
        cls,
        net_profit: float | None,
        tax: float | None,
        interest: float | None,
        depreciation: float | None,
    ) -> float | None:
        """Lợi nhuận + Thuế + Chi phí lãi vay + Khấu hao"""
        if net_profit is None:
            return None
        t = tax or 0.0
        i = interest or 0.0
        d = depreciation or 0.0
        return round(net_profit + t + i + d, 2)
