from __future__ import annotations

import re
from app.models.document import DocumentType


class StatementDetector:
    """
    Analyzes document text to detect its Financial Statement Type.

    Uses keyword/phrase frequency heuristics in Vietnamese and English.
    """

    # ── Keywords maps ─────────────────────────────────────────────────────────
    # Normalized lowercase regex matches
    KEYWORDS = {
        DocumentType.BALANCE_SHEET: [
            r"bảng cân đối kế toán",
            r"tài sản ngắn hạn",
            r"tài sản dài hạn",
            r"nợ phải trả",
            r"vốn chủ sở hữu",
            r"balance sheet",
            r"assets and liabilities",
        ],
        DocumentType.INCOME_STATEMENT: [
            r"báo cáo kết quả hoạt động kinh doanh",
            r"báo cáo kết quả kinh doanh",
            r"doanh thu thuần",
            r"lợi nhuận gộp",
            r"lợi nhuận sau thuế",
            r"giá vốn hàng bán",
            r"income statement",
            r"profit & loss",
            r"revenue and expenses",
        ],
        DocumentType.CASH_FLOW: [
            r"báo cáo lưu chuyển tiền tệ",
            r"lưu chuyển tiền từ hoạt động",
            r"lưu chuyển tiền thuần",
            r"tiền và (các khoản )?tương đương tiền",
            r"cash flow statement",
            r"cash flows from operating",
        ],
        DocumentType.NOTES: [
            r"bản thuyết minh báo cáo tài chính",
            r"thuyết minh báo cáo tài chính",
            r"notes to the financial statements",
            r"thuyết minh số",
        ]
    }

    @classmethod
    def detect_type(cls, text: str) -> DocumentType:
        """
        Scans text and returns matching DocumentType.
        If multiple statements match, returns the one with the highest hit count.
        Defaults to DocumentType.OTHER if no strong match.
        """
        if not text:
            return DocumentType.UNKNOWN

        text_lower = text.lower()
        counts: dict[DocumentType, int] = {k: 0 for k in cls.KEYWORDS}

        for doc_type, pattern_list in cls.KEYWORDS.items():
            for pattern in pattern_list:
                # Count matches
                matches = re.findall(pattern, text_lower)
                counts[doc_type] += len(matches)

        # Get match with highest count
        best_match, max_count = max(counts.items(), key=lambda item: item[1])

        # Require a minimum of 2 keyword occurrences to classify
        if max_count >= 2:
            return best_match

        return DocumentType.OTHER
