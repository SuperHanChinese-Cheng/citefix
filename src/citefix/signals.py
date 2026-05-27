"""Introductory signal detection and stripping (AGLC4 Rule 1.2).

AGLC4 footnotes may begin with an introductory signal that indicates the
relationship between the cited source and the proposition in the body text.
Common signals include 'See', 'See also', 'See eg', 'See especially',
'See generally', 'But see', and 'Cf'.

These signals must be stripped before parsing so they are not mistakenly
included in the citation fields (e.g. party names, author names).
"""

from __future__ import annotations

import regex

# AGLC4 Rule 1.2 introductory signals.
# Ordered longest-first within the alternation to prevent partial matches.
SIGNAL_PATTERN = regex.compile(
    r"""
    ^\s*
    (?P<signal>
        See\s+especially   |
        See\s+generally    |
        See\s+also         |
        But\s+see          |
        See,?\s+eg,?       |
        See\b              |
        Cf\b
    )
    \s+                        # at least one space between signal and citation
    """,
    regex.VERBOSE | regex.UNICODE | regex.IGNORECASE,
)


def strip_introductory_signal(text: str) -> tuple[str, str]:
    """Strip an AGLC4 introductory signal from the start of footnote text.

    Args:
        text: Raw footnote text.

    Returns:
        Tuple of (signal, remaining_text).
        If no signal is found, signal is the empty string and remaining_text
        is the original text unchanged.
    """
    m = SIGNAL_PATTERN.match(text)
    if m:
        signal = m.group("signal").strip()
        remaining = text[m.end():]
        return signal, remaining
    return "", text
