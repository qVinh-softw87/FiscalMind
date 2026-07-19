from __future__ import annotations

import re


class FinancialDataNormalizer:
    """
    Standardizes raw, localized financial labels and numbers into a structured schema.

    E.g.
    - "Doanh thu thuần" / "Net Revenue" → "net_revenue"
    - "Lợi nhuận gộp" / "Gross Profit" → "gross_profit"
    - "1.500.000" / "(2.000)" → float values: 1500000.0 / -2000.0
    """

    # ── Map standard keys to Vietnamese & English synonym regexes ───────────────
    MAPPING_RULES = {
        "revenue": [
            r"doanh thu bán hàng",
            r"doanh thu cung cấp dịch vụ",
            r"gross revenue",
            r"total revenue",
        ],
        "net_revenue": [
            r"doanh thu thuần",
            r"net revenue",
            r"net sales",
        ],
        "cost_of_goods_sold": [
            r"giá vốn hàng bán",
            r"giá vốn",
            r"cost of goods sold",
            r"cogs",
            r"cost of sales",
        ],
        "gross_profit": [
            r"lợi nhuận gộp",
            r"gross profit",
            r"gross margin",
        ],
        "net_profit": [
            r"lợi nhuận sau thuế",
            r"lợi nhuận ròng",
            r"net profit after tax",
            r"net income",
            r"earnings after tax",
        ],
        "total_assets": [
            r"tổng cộng tài sản",
            r"tổng tài sản",
            r"total assets",
        ],
        "short_term_assets": [
            r"tài sản ngắn hạn",
            r"current assets",
            r"total current assets",
        ],
        "cash_and_equivalents": [
            r"tiền và các khoản tương đương tiền",
            r"tiền và tương đương tiền",
            r"cash and cash equivalents",
        ],
        "long_term_assets": [
            r"tài sản dài hạn",
            r"non-current assets",
            r"total non-current assets",
        ],
        "total_liabilities": [
            r"nợ phải trả",
            r"tổng nợ phải trả",
            r"total liabilities",
        ],
        "short_term_liabilities": [
            r"nợ ngắn hạn",
            r"current liabilities",
            r"total current liabilities",
        ],
        "equity": [
            r"vốn chủ sở hữu",
            r"nguồn vốn chủ sở hữu",
            r"owner's equity",
            r"total equity",
        ],
        "operating_cash_flow": [
            r"lưu chuyển tiền thuần từ hoạt động kinh doanh",
            r"lưu chuyển tiền từ hoạt động kinh doanh",
            r"net cash from operating activities",
        ]
    }

    @classmethod
    def parse_number(cls, val_str: str) -> float | None:
        """
        Parses localization quirks into a clean Python float.

        Handles:
        - Parentheses for negative numbers: "(1,500)" → -1500.0
        - Dot/Comma groupings: "1.500.000" or "1,500,000" → 1500000.0
        - Empty indicators: "-" or "n/a" → None
        """
        if not val_str:
            return None

        clean = val_str.strip()
        if clean in ("-", "—", "N/A", "n/a", ""):
            return None

        # Check negative parentheses
        is_negative = False
        if clean.startswith("(") and clean.endswith(")"):
            is_negative = True
            clean = clean[1:-1]

        # Replace dots with empty if they are thousand separators
        # e.g., "1.500.000" has dots. If there's a comma for decimal like "1.500,50", handle it.
        # Simple strategy: if commas exist and dots exist, drop dots, replace comma with dot.
        # If only dots exist and count > 1, it's thousands: "1.234.567" -> "1234567"
        if "," in clean and "." in clean:
            clean = clean.replace(".", "").replace(",", ".")
        elif "," in clean:
            # Check if comma is decimal or thousand separator
            # E.g. "1,500,000" (thousands) vs "12,34" (decimal)
            if clean.count(",") > 1:
                clean = clean.replace(",", "")
            else:
                # If followed by exactly 3 digits, it's likely thousand separator, else decimal
                parts = clean.split(",")
                if len(parts[-1]) == 3:
                    clean = clean.replace(",", "")
                else:
                    clean = clean.replace(",", ".")
        elif "." in clean:
            if clean.count(".") > 1:
                clean = clean.replace(".", "")

        try:
            val = float(clean)
            return -val if is_negative else val
        except ValueError:
            return None

    @classmethod
    def normalize_table(cls, headers: list[str], rows: list[list[str]]) -> dict[str, float]:
        """
        Extracts mapped metrics from raw table rows.
        Returns a dict of standard_key -> numeric_value.
        """
        normalized_data = {}

        for row in rows:
            if not row:
                continue

            label = str(row[0]).lower().strip()
            # Try to match the label with mapping rules
            matched_key = None
            for key, patterns in cls.MAPPING_RULES.items():
                for pattern in patterns:
                    if re.search(r"\b" + pattern + r"\b", label) or pattern == label:
                        matched_key = key
                        break
                if matched_key:
                    break

            if matched_key:
                # Find the first numerical value in the row (ignoring notes/indexes)
                for cell in row[1:]:
                    num_val = cls.parse_number(cell)
                    if num_val is not None:
                        normalized_data[matched_key] = num_val
                        break  # Take first matching column (usually latest year)

        return normalized_data
class StandardizedReport:
    """Combines normalized figures from multiple tables."""
    def __init__(self):
        self.metrics: dict[str, float] = {}

    def merge_metrics(self, new_metrics: dict[str, float]):
        for k, v in new_metrics.items():
            # If exists, keep the larger value or non-zero value
            if k in self.metrics:
                if self.metrics[k] == 0:
                    self.metrics[k] = v
            else:
                self.metrics[k] = v
