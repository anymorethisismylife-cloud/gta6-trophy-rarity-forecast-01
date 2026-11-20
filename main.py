"""GTA VI trophy rarity forecast (make.fun gta6-trophy-rarity-forecast-01).

Forecasts, for each of the game's PlayStation 5 trophies, five quantiles of
its earn rate on Exophase at the case's target, from the reads in the case's
history. Python 3.13, standard library only, no network, deterministic.

Method
------
Work on the logit scale, against x = ln(1 + hours since the game's release
midnight, 2026-11-19T00:00:00Z).  Earn rates rise fast just after launch and
then saturate, so a line in (x, logit rate) is a reasonable local shape, and
the log-time axis keeps a 4.5-day extrapolation from 2.5 days of reads from
running away.

For each trophy the line is anchored at its last read: the forecast is the
last logit plus a slope times the distance in x to the target.  The slope is
the least-squares slope through the anchor over the reads of the last day,
shrunk toward the mean slope of the trophy's tier (platinum / gold / silver /
bronze): rare trophies have few earned players, so their own slope is noisy
and the tier's typical pace is a better prior.  With fewer than three usable
reads the slope is zero and the forecast is flat.  The extrapolated slope is
damped with distance, dividing it by (1 + |dx| / 2.5): a saturating truth
does not keep rising on a straight line, and the undamped line overshoots on
every simulated final.

The spread on the logit scale combines three honest sources of error, added
in quadrature: a random-walk term that grows with the square root of the
horizon in days, the residual scatter of the trophy's own fit, and the
uncertainty of the slope itself, which grows with the extrapolation distance.
Quantiles are the forecast logit plus the standard normal's quantile at each
level times that spread, mapped back to percent and clamped to [0.01, 99.99].

Every number is rounded half-up to 4 decimals.  There is no randomness and
no dependence on wall-clock time, so two runs write identical bytes.
"""

import json
import math
import os
import sys
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

# The grader's -P leaves this file's directory off sys.path; put it back so a
# helper module shipped beside this file can be imported.  (This entry ships
# no helper, but the line keeps the layout the kit documents.)
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z_SCORES = [-1.6448536269514722, -0.6744897501960817, 0.0,
            0.6744897501960817, 1.6448536269514722]

# --- tuning constants (chosen on simulated finals; see dev/sim.py) --------
WINDOW_HOURS = 24.0      # reads used for a trophy's slope: the last day
SHRINK_K = 6.0           # effective reads' worth of weight on the tier slope
RW_SIGMA = 0.5           # logit random-walk sigma per sqrt(day)
SPREAD_MULT = 0.8        # global multiplier on the combined spread
SPREAD_MIN = 0.05        # never claim to know a rate that precisely
SPREAD_MAX = 3.0         # never spread wider than this on the logit scale
FALLBACK_RATE = 1.0      # median percent when a trophy was never observed
DAMP_L = 2.5             # damping length in x units: the extrapolated slope
                         # is divided by (1 + |dx| / DAMP_L), because a
                         # saturating truth does not keep rising on a line


def clamp_pct(value):
    """A percent the page could print, inside the logit's domain."""
    return min(99.99, max(0.01, value))


def logit_of_pct(value):
    p = clamp_pct(value) / 100.0
    return math.log(p / (1.0 - p))


def pct_of_logit(lg):
    if lg >= 0.0:
        p = 1.0 / (1.0 + math.exp(-lg))
    else:
        e = math.exp(lg)
        p = e / (1.0 + e)
    return clamp_pct(100.0 * p)


def round4_half_up(value):
    """Round to 4 decimals, halves away from zero's neighbour up, the way a
    decimal printout rounds; whole numbers come back as ints."""
    q = Decimal(repr(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    if q == q.to_integral_value():
        return int(q)
    return float(q)


def parse_time(text):
    """An ISO 8601 timestamp; 'Z' means UTC."""
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def release_origin(case):
    """Midnight UTC of the game's release date, the origin of the log-time
    axis.  Falls back to the first read when the date is unusable."""
    raw = (case.get("game") or {}).get("release_date")
    try:
        y, m, d = (int(part) for part in str(raw).split("-"))
        return datetime(y, m, d, tzinfo=timezone.utc)
    except (TypeError, ValueError):
        first = case["history"][0]["at"]
        moment = parse_time(first)
        return moment.replace(hour=0, minute=0, second=0, microsecond=0)


def log_hours(moment, origin):
    """ln(1 + hours from the release midnight to `moment`).  Reads taken just
    before midnight give a small negative value, which is fine."""
    hours = (moment - origin).total_seconds() / 3600.0
    return math.log1p(max(-0.9, hours))


def trophy_points(reads, index):
    """(x, logit rate) pairs for one trophy, oldest first, over the reads in
    the fitting window, plus the anchor (x, logit) of its last observed rate.
    `reads` is a list of (moment, x, rates) with moments ascending.
    Returns (points, anchor) or (None, None) when nothing was observed."""
    if not reads:
        return None, None
    last_moment = reads[-1][0]
    window_start = last_moment.timestamp() - WINDOW_HOURS * 3600.0
    points = []
    anchor = None
    for moment, x, rates in reads:
        rate = rates[index]
        if rate is None:
            continue
        pair = (x, logit_of_pct(rate))
        anchor = pair  # the last observed rate wins
        if moment.timestamp() >= window_start:
            points.append(pair)
    if anchor is None:
        return None, None
    if len(points) < 3:
        # Too little inside the window: use everything observed.
        points = [(x, logit_of_pct(rates[index])) for _, x, rates in reads
                  if rates[index] is not None]
    return points, anchor


def slope_through_anchor(points, anchor):
    """Least-squares slope of the line through `anchor`, and the residual
    scatter around that line.  (0.0, 0.0) when the x values do not vary."""
    x0, y0 = anchor
    num = 0.0
    den = 0.0
    for x, y in points:
        dx = x - x0
        num += dx * (y - y0)
        den += dx * dx
    if den <= 0.0:
        return 0.0, 0.0, 0.0
    slope = num / den
    sq = 0.0
    for x, y in points:
        r = y - (y0 + slope * (x - x0))
        sq += r * r
    dof = max(1, len(points) - 1)
    resid_sd = math.sqrt(sq / dof)
    return slope, resid_sd, den


def forecast_case(case):
    """One case's forecast: {"trophies": [{"id": n, "q": [5 numbers]}]}."""
    if case.get("levels") != LEVELS:
        raise ValueError("case asks for levels %r, not %r"
                         % (case.get("levels"), LEVELS))
    trophies = case["trophies"]
    history = case.get("history") or []
    origin = release_origin(case) if history else None
    target_x = None
    if history:
        target_x = log_hours(parse_time(case["target"]), origin)
    horizon_days = case["horizon_minutes"] / 1440.0
    rw_spread = RW_SIGMA * math.sqrt(max(0.0, horizon_days))

    # Parse each read once: (moment, x, rates), oldest first.
    reads = []
    if history:
        for read in history:
            moment = parse_time(read["at"])
            reads.append((moment, log_hours(moment, origin), read["rates"]))

    # First pass: each trophy's own slope, residual scatter and anchor.
    fitted = []
    for index, trophy in enumerate(trophies):
        if not history:
            fitted.append(None)
            continue
        points, anchor = trophy_points(reads, index)
        if points is None:
            fitted.append(None)
            continue
        slope, resid_sd, den = slope_through_anchor(points, anchor)
        fitted.append({
            "tier": trophy.get("tier"),
            "n": len(points),
            "slope": slope,
            "resid": resid_sd,
            "den": den,
            "anchor": anchor,
        })

    # Tier-mean slopes, for the shrinkage prior.
    tier_slopes = {}
    for tier in ("platinum", "gold", "silver", "bronze"):
        slopes = [f["slope"] for f in fitted
                  if f is not None and f["tier"] == tier]
        if slopes:
            tier_slopes[tier] = sum(slopes) / len(slopes)

    rows = []
    for index, trophy in enumerate(trophies):
        fit = fitted[index]
        if fit is None:
            centre = logit_of_pct(FALLBACK_RATE)
            spread = 1.0
        else:
            slope = fit["slope"]
            prior = tier_slopes.get(fit["tier"])
            if prior is not None:
                w = fit["n"] / (fit["n"] + SHRINK_K)
                slope = w * slope + (1.0 - w) * prior
            x0, y0 = fit["anchor"]
            dx = target_x - x0
            # The log-time line keeps rising; a saturating truth does not.
            # Damp the extrapolated part of the slope.
            slope = slope / (1.0 + abs(dx) / DAMP_L)
            centre = y0 + slope * dx
            var = rw_spread * rw_spread
            var += fit["resid"] * fit["resid"]
            if fit["den"] > 0.0:
                var_slope = (fit["resid"] * fit["resid"]) / fit["den"]
                var += var_slope * dx * dx
            spread = math.sqrt(max(0.0, var)) * SPREAD_MULT
            spread = min(SPREAD_MAX, max(SPREAD_MIN, spread))
        rows.append({
            "id": trophy["id"],
            "q": [round4_half_up(pct_of_logit(centre + z * spread))
                  for z in Z_SCORES],
        })
    return {"trophies": rows}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case)
        text = json.dumps(forecast, separators=(",", ":")) + "\n"
        (OUTPUT_DIR / (path.stem + ".out")).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
