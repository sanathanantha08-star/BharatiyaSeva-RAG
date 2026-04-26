"""
app/services/ingestion/pdf_parser.py
──────────────────────────────────────
Async PDF parser backed by PyMuPDF (fitz).

Extracts per-page text, basic table text, and image captions.
Returns a list of ParsedPage objects that downstream stages consume.

Why PyMuPDF?
  • Handles messy government PDFs (scanned + digital mix)
  • Fast C extension – no subprocess overhead
  • Exposes blocks, images, and tables natively
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import fitz  # PyMuPDF

from app.interfaces.ingestion import IPDFParser

logger = logging.getLogger(__name__)


@dataclass
class ParsedPage:
    page_number: int            # 1-indexed
    raw_text: str               # plain text for the whole page
    table_texts: List[str] = field(default_factory=list)   # extracted table strings
    image_captions: List[str] = field(default_factory=list)  # alt-text / nearby text


class PyMuPDFParser(IPDFParser):
    """
    Concrete IPDFParser implementation using PyMuPDF.

    Runs the blocking fitz calls in a thread-pool executor so the
    async event loop is never blocked.
    """

    async def parse(self, pdf_path: Path) -> List[ParsedPage]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._parse_sync, pdf_path)

    # ── sync core (runs in thread pool) ──────────────────────────────────────

    def _parse_sync(self, pdf_path: Path) -> List[ParsedPage]:
        logger.info("Parsing PDF: %s", pdf_path.name)
        parsed_pages: List[ParsedPage] = []

        with fitz.open(str(pdf_path)) as doc:
            for page_index in range(len(doc)):
                page = doc[page_index]
                page_number = page_index + 1

                raw_text = self._extract_text(page)
                table_texts = self._extract_tables(page)
                image_captions = self._extract_image_captions(page)

                parsed_pages.append(
                    ParsedPage(
                        page_number=page_number,
                        raw_text=raw_text,
                        table_texts=table_texts,
                        image_captions=image_captions,
                    )
                )

        logger.info("Parsed %d pages from %s", len(parsed_pages), pdf_path.name)
        return parsed_pages

    def _extract_text(self, page: fitz.Page) -> str:
        """
        Extract text preserving reading order.
        'blocks' sorting gives better ordering for multi-column layouts
        common in government PDFs.
        """
        blocks = page.get_text("blocks", sort=True)   # type: ignore[arg-type]
        lines = []
        for b in blocks:
            # b = (x0, y0, x1, y1, text, block_no, block_type)
            # block_type 0 = text, 1 = image
            if b[6] == 0 and b[4].strip():
                lines.append(b[4].strip())
        return "\n".join(lines)

    def _extract_tables(self, page: fitz.Page) -> List[str]:
        """
        Use PyMuPDF's built-in table finder (available since v1.23).
        Falls back gracefully if no tables found.
        """
        table_strings: List[str] = []
        try:
            tabs = page.find_tables()
            for tab in tabs.tables:
                rows = tab.extract()
                if not rows:
                    continue
                # Flatten rows → readable string
                rendered = []
                for row in rows:
                    cells = [str(cell or "").strip() for cell in row]
                    rendered.append(" | ".join(cells))
                table_strings.append("\n".join(rendered))
        except Exception as exc:
            logger.debug("Table extraction skipped for page: %s", exc)
        return table_strings

    def _extract_image_captions(self, page: fitz.Page) -> List[str]:
        """
        Extract text immediately below images – often captions or labels.
        This is a heuristic approach sufficient for government scheme PDFs.
        """
        captions: List[str] = []
        image_list = page.get_images(full=True)
        if not image_list:
            return captions

        for img in image_list:
            # img[7] = image bbox on the page (x0,y0,x1,y1)
            try:
                rects = page.get_image_rects(img[0])
                for rect in rects:
                    # Expand rect downward by ~20 points to catch caption text
                    caption_rect = fitz.Rect(
                        rect.x0, rect.y1, rect.x1, rect.y1 + 20
                    )
                    caption_text = page.get_text("text", clip=caption_rect).strip()
                    if caption_text:
                        captions.append(caption_text)
            except Exception:
                pass
        return captions
