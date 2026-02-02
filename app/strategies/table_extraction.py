"""Strategy: extraction of tables from PDF. Different algorithms can be swapped."""

import io
from abc import ABC, abstractmethod

import pdfplumber

# Type: list of pages, each page = list of tables, each table = list of rows, each row = list of cells
TablesOnPage = list[list[list[str | None]]]
TablesByPageNumber = list[tuple[int, TablesOnPage]]


class TableExtractorStrategy(ABC):
    """Abstract strategy for extracting tables from PDF content."""

    @abstractmethod
    def get_page_count(self, content: bytes) -> int:
        """Return number of pages (for validation without full extraction)."""
        ...

    @abstractmethod
    def extract_tables(self, content: bytes, pages: list[int] | None = None) -> TablesByPageNumber:
        """Extract tables from PDF bytes. Returns (page_number, tables) tuples."""
        ...


class PdfplumberTableExtractor(TableExtractorStrategy):
    """Extract tables using pdfplumber (line-based / structured PDFs)."""

    def get_page_count(self, content: bytes) -> int:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return len(pdf.pages)

    def extract_tables(self, content: bytes, pages: list[int] | None = None) -> TablesByPageNumber:
        result: TablesByPageNumber = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            if pages:
                for page_num in pages:
                    page = pdf.pages[page_num - 1]
                    tables = page.extract_tables()
                    result.append((page_num, tables or []))
            else:
                for page_num, page in enumerate(pdf.pages, start=1):
                    tables = page.extract_tables()
                    result.append((page_num, tables or []))
        return result
