from __future__ import annotations

import io
import re

import pandas as pd
import pdfplumber

from app.core.logging import get_logger

logger = get_logger(__name__)


class FinancialTableExtractor:
    """
    Extracts tabular data from spreadsheets (Excel, CSV) and PDFs.
    """

    @classmethod
    def extract_from_excel(cls, file_bytes: bytes) -> list[dict]:
        """
        Parses all sheets in an Excel workbook using pandas.
        Returns a list of structured table dictionaries.
        """
        tables = []
        try:
            excel_file = io.BytesIO(file_bytes)
            # Read all sheets
            dict_dfs = pd.read_excel(excel_file, sheet_name=None, header=None)

            for sheet_name, df in dict_dfs.items():
                # Drop fully empty rows/columns
                df = df.dropna(how="all").dropna(axis=1, how="all")
                if df.empty:
                    continue

                # Convert to list of lists representing raw rows
                raw_rows = df.values.tolist()
                tables.append({
                    "source": f"excel_sheet_{sheet_name}",
                    "headers": [str(h) for h in raw_rows[0]] if raw_rows else [],
                    "rows": [[str(cell) if pd.notna(cell) else "" for cell in row] for row in raw_rows],
                })
        except Exception as e:
            logger.error("excel_table_extraction_failed", error=str(e))
        return tables

    @classmethod
    def extract_from_csv(cls, file_bytes: bytes) -> list[dict]:
        """Parses CSV content into table format."""
        tables = []
        try:
            csv_file = io.BytesIO(file_bytes)
            df = pd.read_csv(csv_file, header=None)
            df = df.dropna(how="all").dropna(axis=1, how="all")
            raw_rows = df.values.tolist()
            tables.append({
                "source": "csv_file",
                "headers": [str(h) for h in raw_rows[0]] if raw_rows else [],
                "rows": [[str(cell) if pd.notna(cell) else "" for cell in row] for row in raw_rows],
            })
        except Exception as e:
            logger.error("csv_table_extraction_failed", error=str(e))
        return tables

    @classmethod
    def extract_from_pdf(cls, file_path: str) -> list[dict]:
        """
        Brings out native tables from digital PDFs using pdfplumber's heuristics.
        """
        tables = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for idx, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    for t_idx, table in enumerate(page_tables):
                        # Filter out empty or useless tables
                        valid_rows = [
                            row for row in table
                            if any(cell and cell.strip() for cell in row)
                        ]
                        if not valid_rows:
                            continue

                        tables.append({
                            "source": f"pdf_page_{idx+1}_table_{t_idx+1}",
                            "headers": [str(h).strip() if h else "" for h in valid_rows[0]],
                            "rows": [[str(cell).strip() if cell else "" for cell in row] for row in valid_rows],
                        })
        except Exception as e:
            logger.error("pdf_table_extraction_failed", error=str(e))

        return tables

    @classmethod
    def extract_from_ocr_text(cls, ocr_text: str) -> list[dict]:
        """
        Heuristic fallback: Reconstructs tables from OCR text lines
        when native table structures are lost.

        Looks for rows matching: [Text Label] [Number] [Number]
        """
        tables = []
        lines = ocr_text.split("\n")
        current_table_rows = []

        # Pattern: match lines starting with words followed by numbers (positive/negative/empty)
        # Example: "Doanh thu ban hang    15.000.000   12.000.000"
        row_regex = re.compile(
            r"^([A-Za-zÀ-ỹ\s&()\-.,]+)\s+([\d.,()\-]+(?:\s+[\d.,()\-]+)*)$"
        )

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            match = row_regex.match(line_str)
            if match:
                label = match.group(1).strip()
                numbers_str = match.group(2).strip()
                # Split numbers by whitespace/tab
                numbers = re.split(r"\s+", numbers_str)
                current_table_rows.append([label] + numbers)
            else:
                # If a line breaks the sequence, finalize current table
                if len(current_table_rows) > 2:
                    tables.append({
                        "source": "ocr_text_heuristic",
                        "headers": ["Label"] + [f"Value_{i}" for i in range(len(current_table_rows[0]) - 1)],
                        "rows": current_table_rows,
                    })
                    current_table_rows = []

        if len(current_table_rows) > 2:
            tables.append({
                "source": "ocr_text_heuristic",
                "headers": ["Label"] + [f"Value_{i}" for i in range(len(current_table_rows[0]) - 1)],
                "rows": current_table_rows,
            })

        return tables
