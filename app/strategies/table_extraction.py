"""Strategy: extraction of tables from PDF. Different algorithms can be swapped."""

import io
from abc import ABC, abstractmethod

import pdfplumber

# Type: list of pages, each page = list of tables, each table = list of rows, each row = list of cells
TablesByPage = list[list[list[list[str | None]]]]


class TableExtractorStrategy(ABC):
    """Abstract strategy for extracting tables from PDF content."""

    @abstractmethod
    def get_page_count(self, content: bytes) -> int:
        """Return number of pages (for validation without full extraction)."""
        ...

    @abstractmethod
    def extract_tables(self, content: bytes) -> TablesByPage:
        """Extract tables from PDF bytes. Returns one list per page, each with list of tables (rows of cells)."""
        ...


class PdfplumberTableExtractor(TableExtractorStrategy):
    """Extract tables using pdfplumber (line-based / structured PDFs)."""

    def get_page_count(self, content: bytes) -> int:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return len(pdf.pages)

    def extract_tables(self, content: bytes) -> TablesByPage:
        result: TablesByPage = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                result.append(tables or [])
        return result
