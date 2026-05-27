"""Final character-level normalization for corrected footnote text.

Run AFTER all semantic fixes (bracket types, Ibid, abbreviations, etc.).
Handles spacing, punctuation, and character normalization only.
"""

from __future__ import annotations

import regex


def normalize_footnote_text(text: str) -> str:
    """Final character-level cleanup for a corrected footnote.

    Run this AFTER all semantic fixes (bracket types, Ibid, abbreviations, etc.).
    This handles spacing, punctuation, and character normalization only.
    """
    if not text or not text.strip():
        return text

    # === STEP 1: Character normalization ===
    # Remove zero-width characters
    text = regex.sub(r'[​‌‍﻿]', '', text)
    # Replace non-breaking spaces with regular spaces
    text = text.replace(' ', ' ')
    # Replace fullwidth brackets with normal
    text = text.replace('（', '(').replace('）', ')')
    text = text.replace('［', '[').replace('］', ']')

    # === STEP 2: Whitespace normalization ===
    # Collapse multiple spaces to single
    text = regex.sub(r' {2,}', ' ', text)
    # Strip leading/trailing
    text = text.strip()

    # === STEP 3: Spacing around "v" in case names ===
    # Ensure exactly one space on each side of " v " (but not inside words)
    text = regex.sub(r'(?<=\p{L})\s{2,}v\s+(?=\p{L})', ' v ', text)
    text = regex.sub(r'(?<=\p{L})\s+v\s{2,}(?=\p{L})', ' v ', text)

    # === STEP 4: Comma fixes ===
    # Remove space before comma: " , " -> ", "
    text = regex.sub(r'\s+,', ',', text)
    # Ensure space after comma when followed by a letter
    text = regex.sub(r',(?=[A-Za-z])', ', ', text)
    # Ensure space after comma when followed by a digit (but NOT inside numbers like "1,000")
    # Only add space if the comma is NOT part of a thousands-separator pattern
    # (i.e. not followed by exactly 3 digits then a non-digit or end)
    text = regex.sub(r',(?=\d)(?!\d{3}(?:\D|$))', ', ', text)
    # Remove double commas
    text = regex.sub(r',{2,}', ',', text)

    # === STEP 5: Semicolon fixes ===
    # Ensure space after semicolon
    text = regex.sub(r';(?=\S)', '; ', text)
    # Remove space before semicolon
    text = regex.sub(r'\s+;', ';', text)

    # === STEP 6: Bracket spacing ===
    # Remove spaces inside round brackets: "( X )" -> "(X)"
    text = regex.sub(r'\(\s+', '(', text)
    text = regex.sub(r'\s+\)', ')', text)
    # Remove spaces inside square brackets: "[ X ]" -> "[X]"
    text = regex.sub(r'\[\s+', '[', text)
    text = regex.sub(r'\s+\]', ']', text)

    # === STEP 7: Dash normalization ===
    # Number ranges: replace hyphen or em-dash between digits with en-dash
    text = regex.sub(r'(\d)\s*[-—]\s*(\d)', r'\1–\2', text)

    # === STEP 8: Quote normalization ===
    # Convert straight double quotes around text to smart single quotes
    text = regex.sub(r'"([^"]*)"', '‘\\1’', text)
    # Convert smart double quotes to smart single quotes
    text = regex.sub(r'“([^”]*)”', '‘\\1’', text)
    # Convert straight single quotes to smart (context-dependent),
    # but ONLY for straight/typewriter apostrophes (U+0027), NOT already-smart quotes
    # Opening: after space or start of string, before non-space
    text = regex.sub(r"(?<=\s)'(?=\S)", '‘', text)
    text = regex.sub(r"^'(?=\S)", '‘', text)
    # Closing: after non-space, before space/punctuation/end
    text = regex.sub(r"(?<=\S)'(?=[\s.,;:\)]|$)", '’', text)

    # === STEP 9: Section spacing ===
    # Ensure space after section abbreviation: "s14" -> "s 14"
    text = regex.sub(
        r'\b(s|ss|reg|regs|r|rr|cl|cls|pt|pts|div|divs|sch|schs)(\d)',
        r'\1 \2',
        text,
    )

    # === STEP 10: Full stop ===
    # Remove trailing whitespace
    text = text.rstrip()
    # Remove space(s) before a trailing full stop: "42 ." -> "42."
    text = regex.sub(r'\s+\.$', '.', text)
    # Deduplicate trailing full stops
    text = regex.sub(r'\.{2,}$', '.', text)
    # Add full stop if missing (but not if empty)
    if text and not text.endswith('.'):
        text += '.'

    # === STEP 11: Final whitespace pass ===
    text = regex.sub(r' {2,}', ' ', text)
    text = text.strip()

    return text
