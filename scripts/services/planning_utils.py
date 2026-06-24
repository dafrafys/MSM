# app/scripts/services/planning_utils.py

from datetime import date

REF_DAY = date(2025, 1, 8)
SHIFT_CYCLE   = ["M", "M", "A", "A", "N", "N", "R", "R", "R", "R"]
TEAM_OFFSETS  = {"A": 0, "D": 2, "B": 4, "E": 6, "C": 8}

def shift_for(team: str, the_day: date) -> str:
    """Retourne 'M', 'A', 'N' ou 'R' selon l'équipe et la date."""
    delta = (the_day - REF_DAY).days
    idx   = (TEAM_OFFSETS[team.upper()] + delta) % 10
    return SHIFT_CYCLE[idx]
