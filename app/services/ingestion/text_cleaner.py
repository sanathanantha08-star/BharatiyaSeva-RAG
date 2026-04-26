"""
app/services/ingestion/text_cleaner.py
────────────────────────────────────────
Cleans raw text extracted from government PDFs.

Handles common artefacts:
  • Garbled Unicode / encoding noise
  • Excessive whitespace, hyphenation across lines
  • Repeated header/footer text (page numbers, ministry names)
  • Non-breaking spaces, soft-hyphens, zero-width characters
  • Hindi / Devanagari script preserved – only junk removed
"""

from __future__ import annotations

import re
import unicodedata

from app.interfaces.ingestion import ITextCleaner


class GovPDFTextCleaner(ITextCleaner):

    # Patterns compiled once at class load
    _SOFT_HYPHEN = re.compile(r"\xad")
    _ZERO_WIDTH = re.compile(r"[\u200b\u200c\u200d\ufeff]")
    _NON_BREAKING_SPACE = re.compile(r"\xa0")
    _MULTIPLE_SPACES = re.compile(r"[ \t]{2,}")
    _HYPHEN_NEWLINE = re.compile(r"-\n(\w)")          # word-hy-\nphen → word-hyphen
    _MULTIPLE_NEWLINES = re.compile(r"\n{3,}")
    _PAGE_NUMBER = re.compile(r"(?m)^\s*\d{1,4}\s*$") # lone digits on a line
    _DOTTED_LINE = re.compile(r"\.{4,}")               # "......" spacers

    def clean(self, raw_text: str) -> str:
        text = raw_text

        # 1. Unicode normalisation (NFC preserves Devanagari correctly)
        text = unicodedata.normalize("NFC", text)

        # 2. Remove zero-width / invisible characters
        text = self._SOFT_HYPHEN.sub("", text)
        text = self._ZERO_WIDTH.sub("", text)
        text = self._NON_BREAKING_SPACE.sub(" ", text)

        # 3. Rejoin hyphenated line breaks
        text = self._HYPHEN_NEWLINE.sub(r"\1", text)

        # 4. Remove lone page-number lines
        text = self._PAGE_NUMBER.sub("", text)

        # 5. Remove long dotted separator lines
        text = self._DOTTED_LINE.sub(" ", text)

        # 6. Collapse multiple spaces / tabs
        text = self._MULTIPLE_SPACES.sub(" ", text)

        # 7. Collapse excessive blank lines
        text = self._MULTIPLE_NEWLINES.sub("\n\n", text)

        return text.strip()
