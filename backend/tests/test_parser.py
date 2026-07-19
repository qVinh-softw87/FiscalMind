from __future__ import annotations

import pytest

from app.financial_engine.detector import StatementDetector
from app.financial_engine.normalizer import FinancialDataNormalizer
from app.models.document import DocumentType


class TestDetector:
    def test_detect_balance_sheet(self):
        text = "đây là bảng cân đối kế toán của công ty với các tài sản ngắn hạn"
        assert StatementDetector.detect_type(text) == DocumentType.BALANCE_SHEET

    def test_detect_income_statement(self):
        text = "báo cáo kết quả hoạt động kinh doanh có doanh thu thuần và giá vốn"
        assert StatementDetector.detect_type(text) == DocumentType.INCOME_STATEMENT

    def test_detect_cash_flow(self):
        text = "báo cáo lưu chuyển tiền tệ tiền và các khoản tương đương tiền cuối kỳ"
        assert StatementDetector.detect_type(text) == DocumentType.CASH_FLOW

    def test_detect_other(self):
        text = "chỉ có một số thông tin giới thiệu chung chung không chứa báo cáo"
        assert StatementDetector.detect_type(text) == DocumentType.OTHER


class TestNormalizer:
    def test_parse_number_vietnamese(self):
        assert FinancialDataNormalizer.parse_number("1.500.000") == 1500000.0
        assert FinancialDataNormalizer.parse_number("1.234,56") == 1234.56

    def test_parse_number_negative(self):
        assert FinancialDataNormalizer.parse_number("(5.000)") == -5000.0
        assert FinancialDataNormalizer.parse_number("-150") == -150.0

    def test_parse_number_empty(self):
        assert FinancialDataNormalizer.parse_number("-") is None
        assert FinancialDataNormalizer.parse_number("—") is None
        assert FinancialDataNormalizer.parse_number("n/a") is None

    def test_normalize_table(self):
        headers = ["Label", "2024"]
        rows = [
            ["Doanh thu thuần", "150.000"],
            ["Lợi nhuận gộp", "50.000"],
            ["Tổng tài sản", "500.000"],
        ]
        result = FinancialDataNormalizer.normalize_table(headers, rows)
        assert result["net_revenue"] == 150000.0
        assert result["gross_profit"] == 50000.0
        assert result["total_assets"] == 500000.0
