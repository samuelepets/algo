"""Shared constants for e0030 strategy parameter experiments."""

# Walk-forward windows: (IS_start_year, IS_end_year, OOS_start_year, OOS_end_year)
# IS period is [IS_start, IS_end+1), OOS period is [OOS_start, OOS_end+1).
WALK_FORWARD_WINDOWS: list[tuple[int, int, int, int]] = [
    (2003, 2014, 2015, 2018),
    (2003, 2016, 2017, 2020),
    (2003, 2018, 2019, 2022),
    (2003, 2020, 2021, 2025),
]

MIN_TRADES: int = 50
