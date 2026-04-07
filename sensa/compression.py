"""Token-efficient context compression engine."""

from __future__ import annotations

from typing import Dict, List, Tuple


def count_tokens(text: str) -> int:
    """Estimate token count using ~4 chars per token heuristic.

    This is a fast approximation that avoids importing tiktoken or
    similar heavy tokenizer libraries.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to fit within a token budget."""
    if count_tokens(text) <= max_tokens:
        return text
    max_chars = max_tokens * 4
    truncated = text[:max_chars]
    # Try to break at a word boundary
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.7:
        truncated = truncated[:last_space]
    return truncated + "…"


def compress_context(
    channel_outputs: Dict[str, str],
    channel_order: List[str],
    token_weights: Dict[str, float],
    max_tokens: int,
    header: str = "",
    staleness_warnings: str = "",
) -> str:
    """Compress all channel outputs into a single token-efficient string.

    Args:
        channel_outputs: Mapping of channel name -> raw output string.
        channel_order: Order in which to display channels.
        token_weights: Priority weights per channel (should sum to ~1.0).
        max_tokens: Total token budget.
        header: Pre-formatted header line (e.g. [SENSA — ...]).
        staleness_warnings: Pre-formatted staleness warning lines.

    Returns:
        A single compressed context string fitting within the budget.
    """
    # Reserve tokens for header and staleness
    header_tokens = count_tokens(header) if header else 0
    stale_tokens = count_tokens(staleness_warnings) if staleness_warnings else 0
    available = max_tokens - header_tokens - stale_tokens

    if available <= 0:
        # Just return header if we're already over budget
        return header

    # Calculate per-channel budgets based on weights
    active_channels = [ch for ch in channel_order if ch in channel_outputs]
    total_weight = sum(token_weights.get(ch, 0.25) for ch in active_channels)
    if total_weight == 0:
        total_weight = 1.0

    budgets: Dict[str, int] = {}
    for ch in active_channels:
        w = token_weights.get(ch, 0.25)
        budgets[ch] = max(5, int(available * (w / total_weight)))

    # Build output lines
    lines: List[str] = []
    if header:
        lines.append(header)

    for ch in active_channels:
        raw = channel_outputs[ch]
        compressed = truncate_to_tokens(raw, budgets.get(ch, 20))
        if compressed:
            lines.append(compressed)

    if staleness_warnings:
        lines.append(staleness_warnings)

    result = "\n".join(lines)

    # Final check — hard-truncate if still over
    if count_tokens(result) > max_tokens:
        result = truncate_to_tokens(result, max_tokens)

    return result
