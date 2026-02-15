# Fuzzy product name matching stub for RetailStack POS Agent
# Replace with real catalog/API integration later

import re
import logging
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)

# Stub catalog: normalized name -> (product_id, canonical_name)
STUB_CATALOG: Dict[str, Tuple[str, str]] = {
    "cola": ("SKU001", "Cola 500ml"),
    "water": ("SKU002", "Bottled Water"),
    "bread": ("SKU003", "White Bread"),
    "milk": ("SKU004", "Milk 1L"),
}


def _normalize(name: str) -> str:
    """Normalize for matching: lowercase, collapse spaces, remove punctuation."""
    if not name:
        return ""
    s = re.sub(r"[^\w\s]", "", name.lower())
    return " ".join(s.split())


def _token_set_ratio(a: str, b: str) -> float:
    """Simple Jaccard-like token overlap ratio (stub; replace with rapidfuzz/Levenshtein if needed)."""
    ta, tb = set(_normalize(a).split()), set(_normalize(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta), len(tb))


def match_product(receipt_name: str, threshold: float = 0.5) -> Optional[Dict[str, str]]:
    """
    Fuzzy match receipt line item name to a product.
    Returns {'product_id': str, 'matched_name': str} or None if no match.
    Stub implementation using a small in-memory catalog.
    """
    if not (receipt_name or "").strip():
        return None
    normalized = _normalize(receipt_name)
    if not normalized:
        return None
    best_ratio = 0.0
    best_id, best_name = None, None
    for catalog_key, (product_id, canonical_name) in STUB_CATALOG.items():
        ratio = _token_set_ratio(receipt_name, canonical_name)
        if ratio >= threshold and ratio > best_ratio:
            best_ratio = ratio
            best_id, best_name = product_id, canonical_name
    if best_id is not None:
        logger.debug("Matched '%s' -> %s (%s)", receipt_name, best_name, best_id)
        return {"product_id": best_id, "matched_name": best_name}
    return None


def match_items(line_items: List[Dict]) -> List[Dict]:
    """
    Apply fuzzy match to a list of items (each with 'name' key).
    Adds optional 'product_id' and 'matched_name' when match found.
    """
    result = []
    for item in line_items:
        row = dict(item)
        name = item.get("name") or ""
        match = match_product(name)
        if match:
            row["product_id"] = match["product_id"]
            row["matched_name"] = match["matched_name"]
        result.append(row)
    return result
