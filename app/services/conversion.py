"""Conversion service: PDF to Excel using Strategy (extraction) + Builder (Excel)."""

import io
import time

from app.config import settings
from app.strategies.table_extraction import TableExtractorStrategy, TablesByPageNumber
from app.builders.excel_builder import ExcelExportBuilder


class ConversionError(Exception):
    """Raised when PDF cannot be converted (no tables, corrupted, etc.)."""

    def __init__(self, message: str, code: str = "CONVERSION_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class ConversionService:
    """Orchestrates PDF validation, table extraction (Strategy), and Excel build (Builder)."""

    def __init__(self, table_extractor: TableExtractorStrategy) -> None:
        self._extractor = table_extractor

    def get_page_count(self, content: bytes) -> int:
        return self._extractor.get_page_count(content)

    def validate_pdf(
        self,
        content: bytes,
        content_type: str | None,
        max_bytes: int | None = None,
        max_pages: int | None = None,
    ) -> None:
        """Validate PDF before processing. Raises ConversionError if invalid."""
        if content_type and content_type.lower() != "application/pdf":
            raise ConversionError("Only application/pdf is accepted.", "UNSUPPORTED_MIME")
        if max_bytes is None:
            max_bytes = settings.max_pdf_bytes
        if len(content) > max_bytes:
            raise ConversionError(
                f"File too large. Maximum size is {max_bytes // (1024 * 1024)} MB.",
                "FILE_TOO_LARGE",
            )
        if not content or len(content) < 100:
            raise ConversionError("File is empty or too small to be a valid PDF.", "PDF_CORRUPTED")
        try:
            num_pages = self.get_page_count(content)
        except Exception as e:
            raise ConversionError("Unsupported or corrupted PDF.", "PDF_CORRUPTED") from e
        if max_pages is None:
            max_pages = settings.max_pdf_pages
        if num_pages > max_pages:
            raise ConversionError(
                f"Too many pages. Maximum is {max_pages}.",
                "PAGE_LIMIT_EXCEEDED",
            )

    def convert_to_excel(
        self,
        content: bytes,
        filename: str,
        content_type: str | None = "application/pdf",
        pages: list[int] | None = None,
    ) -> tuple[bytes, float]:
        """
        Validate PDF, extract tables (Strategy), build XLSX (Builder).
        Returns (xlsx_bytes, duration_seconds). Raises ConversionError on failure.
        """
        self.validate_pdf(content, content_type)
        start = time.perf_counter()
        tables_by_page: TablesByPageNumber = self._extractor.extract_tables(content, pages=pages)
        builder = ExcelExportBuilder()
        sheet_count = 0
        for page_num, tables in tables_by_page:
            if not tables:
                continue
            builder.add_sheet(f"Page {page_num}")
            for table in tables:
                if table:
                    builder.add_table(table)
            sheet_count += 1
        if sheet_count == 0:
            raise ConversionError("No table detected in PDF.", "NO_TABLE_DETECTED")
        xlsx_bytes = builder.build()
        duration = time.perf_counter() - start
        return xlsx_bytes, duration
