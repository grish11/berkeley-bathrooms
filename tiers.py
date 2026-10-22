"""Turning ratings into an overall score, and a score into a tier.

Two rules live here and nowhere else:

  1. How the nine category ratings become one number (overall_score).
  2. Which tier that number means (tier_for_score).

Both are deliberately tiny and in one place, because both are the kind of rule
that gets changed later -- weighting Cleanliness higher, say, or moving the
Challenger cutoff. Changing it here changes it on the map, in the popup, in
the detail dialog and (Phase 7) in the Hall of Fame, with no other edits.

The browser never computes either one. map.js is handed the finished score and
tier, per docs/ARCHITECTURE.md's rule that the rules live in Python.
"""

from __future__ import annotations

import data

# Score -> tier. The index in this tuple IS the score: TIERS[0] is a score of
# 1, TIERS[9] is a score of 10. Keeping it a plain ordered tuple means the
# cutoffs cannot drift out of sync with the names.
#
# The colours are used for two things: the dot on the map, and the tier name
# written out as text. One colour for both keeps it obvious that the cyan dot
# and the word "Platinum" are the same fact.
TIERS = (
    {"score": 1,  "name": "Iron",        "color": "#7d6b58"},  # greyish brown
    {"score": 2,  "name": "Bronze",      "color": "#9c6b30"},
    {"score": 3,  "name": "Silver",      "color": "#6f7d87"},  # grey
    {"score": 4,  "name": "Gold",        "color": "#c8a02c"},
    {"score": 5,  "name": "Platinum",    "color": "#2ba8a0"},  # cyan
    {"score": 6,  "name": "Emerald",     "color": "#2e9e57"},
    {"score": 7,  "name": "Diamond",     "color": "#2a5ca8"},  # dark blue
    {"score": 8,  "name": "Master",      "color": "#7e3fae"},  # purple
    {"score": 9,  "name": "Grandmaster", "color": "#c0392b"},  # red
    # Blue and gold -- Berkeley's own pair, which is why it is the top tier.
    # `color` is the solid fallback used for text; `gradient` is what the dot
    # and the tier name actually use. Challenger is the only tier with two.
    {
        "score": 10,
        "name": "Challenger",
        "color": "#2e6fd9",
        "gradient": "linear-gradient(135deg, #2e6fd9 0%, #2e6fd9 45%, #f0c14b 55%, #f0c14b 100%)",
    },
)


def overall_score(ratings: dict | None) -> int | None:
    """Average the nine categories, rounded to the nearest whole number.

        >>> overall_score({c: 8 for c in data.RATING_CATEGORIES})
        8

    Returns None when there are no ratings yet, which is a normal state for a
    bathroom added through /add but not yet rated. Callers must handle it --
    the map shows such a bathroom without a score rather than inventing one.

    Note the rounding. Python's built-in round() uses "banker's rounding",
    where round(4.5) is 4 and round(5.5) is 6 -- it rounds halves toward the
    nearest EVEN number. That is a sensible default for statistics and a
    surprising one here, where a 4.5 average should read as a 5. int(x + 0.5)
    is the plain "round halves up" everyone expects for a score.
    """
    if not ratings:
        return None

    values = [ratings[c] for c in data.RATING_CATEGORIES if c in ratings]
    if not values:
        return None

    return int(sum(values) / len(values) + 0.5)


def tier_for_score(score: int | None) -> dict | None:
    """The tier a score falls in, or None if there is no score.

        >>> tier_for_score(8)["name"]
        'Master'

    Scores are already whole numbers from 1 to 10, so this is a direct lookup
    rather than a chain of comparisons. It still clamps, so a future change to
    the formula cannot produce an index error here.
    """
    if score is None:
        return None

    index = min(max(score, 1), 10) - 1
    return TIERS[index]


def best_tier(bathrooms: list[dict]) -> dict | None:
    """A building's tier: the tier of its BEST bathroom.

    Per the spec -- one good bathroom is a reason to walk to a building, and
    averaging it against a bad one on another floor would hide that.

    Returns None when no bathroom in the building has been rated yet.
    """
    scores = [b["score"] for b in bathrooms if b.get("score") is not None]
    if not scores:
        return None
    return tier_for_score(max(scores))
