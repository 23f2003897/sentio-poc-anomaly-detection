"""
anomaly_detection.py
Sentio Mind · Project 5 · Behavioral Anomaly & Early Distress Detection

Copy this file to solution.py and fill in every TODO block.
Do not rename any function. No OpenCV needed — pure data analysis.
Run: python solution.py
"""

import json
import html
import numpy as np
from pathlib import Path
from datetime import datetime, date
from collections import defaultdict, Counter


import base64

def encode_image_to_base64(image_path):
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return ""

# ---------------------------------------------------------------------------
# CONFIG — adjust thresholds here, nowhere else
# ---------------------------------------------------------------------------
DATA_DIR   = Path("sample_data")
REPORT_OUT = Path("alert_digest.html")
FEED_OUT   = Path("alert_feed.json")
SCHOOL     = "Demo School"

THRESHOLDS = {
    "sudden_drop_delta":           20,   # baseline - today >= this → SUDDEN_DROP
    "sudden_drop_high_std_delta":  30,   # used when baseline_std > 15
    "sustained_low_score":         45,   # below this = low
    "sustained_low_days":           3,   # consecutive days below threshold
    "social_withdrawal_delta":     25,   # social_engagement drop
    "hyperactivity_delta":         40,   # combined energy spike
    "regression_recover_days":      3,   # days improving before regression counts
    "regression_drop":             15,   # drop after recovery
    "gaze_avoidance_days":          3,   # consecutive days no eye contact
    "absence_days":                 2,   # days not detected
    "baseline_window":              3,   # days used for baseline
    "high_std_baseline":           15,   # if std above this, use relaxed threshold
}

'''
→ Sudden drops in wellbeing vs personal baseline
→ Sustained low scores for 3+ consecutive days
→ Social withdrawal (low engagement + downward gaze together)
→ Hyperactivity spikes in combined energy
→ Regression after a recovery streak
→ Gaze avoidance over multiple days
→ Absence flags for welfare checks
Bonus: Peer outlier detection vs same-day school stats
Each alert includes severity, category, description, and recommended action.
'''

# ---------------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------------

def load_daily_data(folder: Path) -> dict:
    daily = {}

    for fp in sorted(folder.glob("*.json")):
        print("Reading:", fp)

        try:
            with open(fp, "r") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Skipping {fp} due to error:", e)
            continue

        date_str = data.get("date") or fp.stem

        persons = {}

        for person in data.get("persons", []):
            pid = person.get("person_id")

            if not pid:
                continue

            persons[pid] = {
                "wellbeing": person.get("wellbeing_score", 0),
                "social_engagement": person.get("social_engagement", 0),
                "physical_energy": person.get("physical_energy", 0),
                "movement_energy": person.get("movement_energy", 0),
                "gaze_direction": person.get("gaze_direction", "forward"),
                "eye_contact": person.get("eye_contact", True),
                "person_info": {
                    "name": person.get("name", pid),
                    "profile_image_b64": encode_image_to_base64(person.get("image_path", ""))
                }
            }

        daily[date_str] = persons

    return daily

daily_data = load_daily_data(Path("sample_data"))

print("Days:", daily_data.keys())

first_day = list(daily_data.keys())[0]
print("Sample student:", list(daily_data[first_day].items())[0])


# ---------------------------------------------------------------------------
# BASELINE
# ---------------------------------------------------------------------------

def compute_baseline(history: list) -> dict:
    """
    history: list of daily dicts (oldest first), each has at minimum:
      { wellbeing: int, traits: {}, gaze_direction: str }

    Use first THRESHOLDS['baseline_window'] days.
    Return:
      { wellbeing_mean, wellbeing_std, trait_means: {}, avg_gaze: str }

    """
    window = history[:THRESHOLDS["baseline_window"]]

    wellbeing_vals = [d["wellbeing"] for d in window]
    wellbeing_mean = np.mean(wellbeing_vals)
    wellbeing_std = np.std(wellbeing_vals)

    trait_means = {
        "social_engagement": np.mean([d["social_engagement"] for d in window]),
        "physical_energy": np.mean([d["physical_energy"] for d in window]),
        "movement_energy": np.mean([d["movement_energy"] for d in window]),
    }

    gaze_counts = Counter(d.get("gaze_direction", "forward") for d in window)
    avg_gaze = gaze_counts.most_common(1)[0][0]

    return {
        "wellbeing_mean": wellbeing_mean,
        "wellbeing_std": wellbeing_std,
        "trait_means": trait_means,
        "avg_gaze": avg_gaze,
    }


# ---------------------------------------------------------------------------
# ANOMALY DETECTORS  — each returns an alert dict or None
# ---------------------------------------------------------------------------

'''
→ Sudden drops in wellbeing vs personal baseline
→ Sustained low scores for 3+ consecutive days
→ Social withdrawal (low engagement + downward gaze together)
→ Hyperactivity spikes in combined energy
→ Regression after a recovery streak
→ Gaze avoidance over multiple days
→ Absence flags for welfare checks
Bonus: Peer outlier detection vs same-day school stats
Each alert includes severity, category, description, and recommended action.
'''

def detect_sudden_drop(today: dict, baseline: dict) -> dict | None:
    baseline_mean = baseline["wellbeing_mean"]
    today_score = today["wellbeing"]
    drop = baseline_mean - today_score

    threshold = (
        THRESHOLDS["sudden_drop_high_std_delta"]
        if baseline["wellbeing_std"] > THRESHOLDS["high_std_baseline"]
        else THRESHOLDS["sudden_drop_delta"]
    )

    if drop < threshold:
        return None

    traits = {
        "social_engagement": today["social_engagement"],
        "physical_energy": today["physical_energy"],
        "movement_energy": today["movement_energy"],
    }

    lowest_trait, lowest_trait_value = min(traits.items(), key=lambda item: item[1])

    percentage_drop = (drop / baseline_mean) * 100 if baseline_mean else 0
    # Pro-tip: Explicitly log when the safety threshold is triggered
    if baseline["wellbeing_std"] > THRESHOLDS["high_std_baseline"]:
        threshold = THRESHOLDS["sudden_drop_high_std_delta"]
        # Add a note to the description so the counsellor knows why the threshold moved
        description_suffix = " (High baseline volatility detected; using 30pt threshold)"

    return {
        "severity": "urgent" if drop > 35 else "monitor",
        "category": "SUDDEN_DROP",
        "description": (
            f"Wellbeing dropped from {round(baseline_mean)} to {today_score} "
            f"({round(drop)} pts, {percentage_drop:.1f}%). "
            f"Lowest trait: {lowest_trait} ({lowest_trait_value}). "
            f"Gaze: {today.get('gaze_direction', 'forward')}."
        ),
        "baseline_wellbeing": round(baseline_mean),
        "today_wellbeing": today_score,
        "delta": round(drop),
        "lowest_trait": lowest_trait,
        "lowest_trait_value": lowest_trait_value,
        "recommended_action": "Schedule pastoral check-in today",
    }



def detect_sustained_low(history: list) -> dict | None:
    """
    Check the last sustained_low_days entries in history.
    If all have wellbeing < sustained_low_score → alert.
    Severity: urgent.
    """
    days = THRESHOLDS["sustained_low_days"]
    low_score = THRESHOLDS["sustained_low_score"]

    if len(history) < days:
        return None

    recent = history[-days:]
    wellbeing_scores = [day.get("wellbeing", 0) for day in recent]

    if any(score >= low_score for score in wellbeing_scores):
        return None

    avg_score = round(float(np.mean(wellbeing_scores)))
    min_score = min(wellbeing_scores)

    return {
        "severity": "urgent",
        "category": "SUSTAINED_LOW",
        "description": (
            f"Wellbeing stayed below {low_score} for {days} consecutive days. "
            f"Recent scores: {wellbeing_scores}. Lowest score: {min_score}."
        ),
        "recent_scores": wellbeing_scores,
        "average_wellbeing": avg_score,
        "lowest_wellbeing": min_score,
        "recommended_action": "Escalate to counselor for immediate follow-up",
    }


def detect_social_withdrawal(today: dict, baseline: dict) -> dict | None:
    """
    social_engagement dropped >= social_withdrawal_delta AND
    today's gaze_direction is "down" or "side".
    Severity: monitor.
    """
    baseline_social = baseline["trait_means"]["social_engagement"]
    today_social = today["social_engagement"]
    drop = baseline_social - today_social
    gaze_direction = today.get("gaze_direction", "forward")

    if drop < THRESHOLDS["social_withdrawal_delta"] or gaze_direction not in {"down", "side"}:
        return None

    return {
        "severity": "monitor",
        "category": "SOCIAL_WITHDRAWAL",
        "description": (
            f"Social engagement dropped from {round(baseline_social)} to {today_social} "
            f"({round(drop)} pts) with gaze direction '{gaze_direction}'."
        ),
        "baseline_social_engagement": round(baseline_social),
        "today_social_engagement": today_social,
        "delta": round(drop),
        "gaze_direction": gaze_direction,
        "recommended_action": "Monitor social interaction and check in with student",
    }


def detect_hyperactivity_spike(today: dict, baseline: dict) -> dict | None:
    """
    (today.physical_energy + today.movement_energy) minus
    (baseline.physical_energy_mean + baseline.movement_energy_mean) >= hyperactivity_delta.
    Severity: monitor.
    """
    baseline_energy = (
        baseline["trait_means"]["physical_energy"] +
        baseline["trait_means"]["movement_energy"]
    )
    today_energy = today["physical_energy"] + today["movement_energy"]
    delta = today_energy - baseline_energy

    if delta < THRESHOLDS["hyperactivity_delta"]:
        return None

    return {
        "severity": "monitor",
        "category": "HYPERACTIVITY_SPIKE",
        "description": (
            f"Combined energy rose from {round(baseline_energy)} to {today_energy} "
            f"({round(delta)} pts). Physical: {today['physical_energy']}, "
            f"Movement: {today['movement_energy']}."
        ),
        "baseline_combined_energy": round(baseline_energy),
        "today_combined_energy": today_energy,
        "delta": round(delta),
        "physical_energy": today["physical_energy"],
        "movement_energy": today["movement_energy"],
        "recommended_action": "Monitor activity levels and classroom regulation needs",
    }


def detect_regression(history: list) -> dict | None:
    """
    Find if the last regression_recover_days entries were all improving (each > previous),
    then today dropped > regression_drop.
    Severity: monitor.
    """
    recover_days = THRESHOLDS["regression_recover_days"]
    drop_threshold = THRESHOLDS["regression_drop"]

    if len(history) < recover_days + 1:
        return None

    recovery_window = history[-(recover_days + 1):-1]
    today_score = history[-1].get("wellbeing", 0)

    previous_score = recovery_window[0].get("wellbeing", 0)
    for day in recovery_window[1:]:
        current_score = day.get("wellbeing", 0)
        if current_score <= previous_score:
            return None
        previous_score = current_score

    drop = previous_score - today_score
    if drop <= drop_threshold:
        return None

    recovery_scores = [day.get("wellbeing", 0) for day in recovery_window]

    return {
        "severity": "monitor",
        "category": "REGRESSION",
        "description": (
            f"Wellbeing improved over {recover_days} days {recovery_scores} "
            f"before dropping from {previous_score} to {today_score} ({drop} pts)."
        ),
        "recovery_scores": recovery_scores,
        "pre_drop_wellbeing": previous_score,
        "today_wellbeing": today_score,
        "delta": drop,
        "recommended_action": "Monitor for signs of setback and check in with student",
    }


def detect_gaze_avoidance(history: list) -> dict | None:
    """
    Last gaze_avoidance_days entries all have eye_contact == False (or missing).
    Severity: monitor.
    """
    days = THRESHOLDS["gaze_avoidance_days"]

    if len(history) < days:
        return None

    recent = history[-days:]
    if any(day.get("eye_contact", False) for day in recent):
        return None

    gaze_directions = [day.get("gaze_direction", "unknown") for day in recent]

    return {
        "severity": "monitor",
        "category": "GAZE_AVOIDANCE",
        "description": (
            f"No eye contact observed for {days} consecutive days. "
            f"Recent gaze directions: {gaze_directions}."
        ),
        "days_without_eye_contact": days,
        "recent_gaze_directions": gaze_directions,
        "recommended_action": "Monitor engagement and gently check in with student",
    }


def detect_peer_outlier(student_score: int, daily_mean: float, daily_std: float) -> dict | None:
    """
    Trigger when a student's wellbeing is more than 2 standard deviations
    below the same-day school mean.
    """
    if daily_std <= 0:
        return None

    threshold = daily_mean - (2 * daily_std)
    if student_score >= threshold:
        return None

    return {
        "severity": "monitor",
        "category": "PEER_OUTLIER",
        "description": (
            f"Wellbeing is significantly lower than the school average "
            f"(Current: {student_score}, School Avg: {daily_mean:.1f}, Threshold: {threshold:.1f})."
        ),
        "today_wellbeing": student_score,
        "school_daily_mean": round(float(daily_mean), 1),
        "school_daily_std": round(float(daily_std), 2),
        "peer_outlier_threshold": round(float(threshold), 1),
        "recommended_action": "Prioritize for peer-group support or social integration check.",
    }


# ---------------------------------------------------------------------------
# ANALYSE ONE PERSON
# ---------------------------------------------------------------------------

def analyse_person(person_id: str, sorted_days: dict, info: dict) -> list:
    """
    sorted_days: { "YYYY-MM-DD": person_data_dict } — keys in date order
    info: { name, profile_image_b64, ... }

    Build history list, compute baseline, run all detectors.
    Return list of alert dicts. Each alert must include person_id, person_name, date,
    and all fields from anomaly_detection.json schema.
    """
    alerts = []
    history = []

    for date_str, data in sorted_days.items():
        history.append(data)
        if len(history) < 2:
            continue

        baseline = compute_baseline(history)
        day_alerts = (
            detect_sudden_drop(data, baseline),
            detect_sustained_low(history),
            detect_social_withdrawal(data, baseline),
            detect_hyperactivity_spike(data, baseline),
            detect_regression(history),
            detect_gaze_avoidance(history),
        )

        for alert in day_alerts:
            if not alert:
                continue
            alert.update({
                "person_id": person_id,
                "person_name": info.get("name", person_id),
                "date": date_str,
                "profile_image_b64": info.get("profile_image_b64", "")
            })
            alerts.append(alert)

    return alerts



# ---------------------------------------------------------------------------
# HTML REPORT
# ---------------------------------------------------------------------------

def generate_alert_digest(alerts: list, absence_flags: list,
                           school_summary: dict, output_path: Path):
    """
    Single-file executive dashboard for offline HTML output.
    """
    # Bonus detector: compare each student's wellbeing against same-day peer stats.
    for date_str in all_dates:
        day_people = daily_data.get(date_str, {})
        day_scores = [pdata.get("wellbeing", 0) for pdata in day_people.values()]
        if not day_scores:
            continue

        daily_mean = float(np.mean(day_scores))
        daily_std = float(np.std(day_scores))

        for pid, pdata in day_people.items():
            peer_alert = detect_peer_outlier(pdata.get("wellbeing", 0), daily_mean, daily_std)
            if not peer_alert:
                continue
            peer_alert.update({
                "person_id": pid,
                "person_name": person_info.get(pid, {}).get("name", pid),
                "date": date_str,
                "profile_image_b64": person_info.get(pid, {}).get("profile_image_b64", ""),
            })
            all_alerts.append(peer_alert)

    sev_order = {"urgent": 0, "monitor": 1, "informational": 2}

    def esc(value):
        return html.escape(str(value))

    def alert_dates(alert_group):
        dates = sorted({a.get("date") for a in alert_group if a.get("date")})
        return dates

    def consecutive_streak(dates):
        if not dates:
            return 0
        parsed = sorted(datetime.strptime(d, "%Y-%m-%d").date() for d in dates)
        best = current = 1
        for prev, cur in zip(parsed, parsed[1:]):
            if (cur - prev).days == 1:
                current += 1
                best = max(best, current)
            else:
                current = 1
        return best

    def spark_values(alert):
        values = []
        if isinstance(alert.get("recent_scores"), list):
            values.extend(alert["recent_scores"][-5:])
        if isinstance(alert.get("recovery_scores"), list):
            values.extend(alert["recovery_scores"][-5:])
        baseline = alert.get("baseline_wellbeing")
        if baseline is not None:
            values.append(int(baseline))
        today = alert.get("today_wellbeing")
        if today is not None:
            values.append(int(today))
        if not values:
            values = [0]
        values = values[-5:]
        if len(values) < 5:
            values = [values[0]] * (5 - len(values)) + values
        return values

    def spark_html(values):
        clean = [int(v) for v in values]
        low = min(clean)
        high = max(clean)
        span = max(high - low, 1)
        trend_stroke = "#EF4444" if clean[-1] <= clean[0] - 20 else "#94A3B8"
        points = []
        markers = []
        for idx, value in enumerate(clean):
            x = 10 + idx * 30
            y = 42 - ((value - low) / span) * 24
            points.append(f"{x:.1f},{y:.1f}")
            markers.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='2.6' fill='{trend_stroke}'></circle>")
        return (
            "<svg class='sparkline' viewBox='0 0 140 52' aria-label='5-day trend' role='img'>"
            "<polyline fill='none' stroke='#CBD5E1' stroke-width='1' points='10,42 130,42'></polyline>"
            f"<polyline fill='none' stroke='{trend_stroke}' stroke-width='2.2' stroke-linecap='round' "
            f"stroke-linejoin='round' points='{' '.join(points)}'></polyline>"
            f"{''.join(markers)}"
            "</svg>"
        )

    def avatar_label(alert):
        person_name = str(alert.get("person_name", "")).strip()
        person_id = str(alert.get("person_id", "")).strip()
        if person_name:
            parts = [part for part in person_name.replace("-", " ").split() if part]
            if len(parts) >= 2:
                return (parts[0][0] + parts[1][0]).upper()
            if len(parts) == 1:
                token = parts[0]
                if len(token) <= 4:
                    return token.upper()
                return token[:2].upper()
        return person_id.upper() or "NA"

    today_str = max((a.get("date") for a in alerts if a.get("date")), default=str(date.today()))
    todays_alerts = sorted(
        [a for a in alerts if a.get("date") == today_str],
        key=lambda a: (sev_order.get(a.get("severity", "informational"), 3), a.get("person_name", "")),
    )

    per_person = defaultdict(list)
    for alert in alerts:
        per_person[(alert.get("person_id", ""), alert.get("person_name", "Unknown"))].append(alert)

    flagged_streaks = []
    for (person_id, person_name), person_alerts in per_person.items():
        dates = alert_dates(person_alerts)
        streak = consecutive_streak(dates)
        if streak >= 3:
            categories = Counter(a.get("category", "UNKNOWN") for a in person_alerts)
            flagged_streaks.append({
                "person_id": person_id,
                "person_name": person_name,
                "streak": streak,
                "last_date": dates[-1],
                "top_category": categories.most_common(1)[0][0] if categories else "UNKNOWN",
            })
    flagged_streaks.sort(key=lambda item: (-item["streak"], item["person_name"]))

    category_styles = {
        "SUDDEN_DROP": ("drop", "#FEE2E2", "#991B1B"),
        "SUSTAINED_LOW": ("sustained", "#F3E8FF", "#6B21A8"),
        "SOCIAL_WITHDRAWAL": ("social", "#DBEAFE", "#1D4ED8"),
        "HYPERACTIVITY_SPIKE": ("energy", "#FEF3C7", "#92400E"),
        "REGRESSION": ("regression", "#E2E8F0", "#334155"),
        "GAZE_AVOIDANCE": ("gaze", "#DCFCE7", "#166534"),
        "PEER_OUTLIER": ("peer", "#F3E8FF", "#6D28D9"),
    }

    table_rows = []
    for alert in todays_alerts:
        severity = alert.get("severity", "informational")
        category = alert.get("category", "UNKNOWN")
        category_class, category_bg, category_fg = category_styles.get(
            category,
            ("generic", "#E2E8F0", "#475569"),
        )
        profile = str(alert.get("profile_image_b64", "")).strip()
        has_profile = bool(profile) and profile.lower() != "no image"
        severity_dot = f"<span class='severity-dot severity-dot-{esc(severity)}' aria-hidden='true'></span>"
        avatar = (
            "<div class='avatar-wrap'>"
            f"<img class='avatar' src='data:image/jpeg;base64,{profile}' alt='{esc(alert.get('person_name', ''))}'>"
            f"{severity_dot}"
            "</div>"
            if has_profile else
            f"<div class='avatar-wrap'><div class='avatar avatar-fallback'>{esc(avatar_label(alert))}</div>{severity_dot}</div>"
        )
        table_rows.append(
            f"<article class='alert-row severity-{esc(severity)}'>"
            "<div class='table-student'>"
            f"{avatar}"
            "<div class='student-meta'>"
            f"<strong>{esc(alert.get('person_name', 'Unknown'))}</strong>"
            f"<span>{esc(alert.get('date', ''))}</span>"
            f"<span class='sev-pill sev-pill-{esc(severity)}'>{esc(severity)}</span>"
            "</div>"
            "</div>"
            "<div class='table-anomaly'>"
            f"<span class='anomaly-badge anomaly-{category_class}' "
            f"style='background:{category_bg};color:{category_fg};'>{esc(category)}</span>"
            "</div>"
            f"<div class='table-description'>{esc(alert.get('description', ''))}</div>"
            f"<div class='table-trend'>{spark_html(spark_values(alert))}</div>"
            "</article>"
        )

    kpi_items = [
        ("Total Tracked", school_summary.get("total_persons_tracked", "N/A")),
        ("Flagged Today", school_summary.get("persons_flagged_today", "N/A")),
        ("Avg Wellbeing", school_summary.get("school_avg_wellbeing_today", "N/A")),
        ("Active Absences", len(absence_flags)),
    ]
    kpi_row = []
    for label, value in kpi_items:
        kpi_row.append(
            "<div class='kpi'>"
            f"<span>{esc(label)}</span>"
            f"<strong>{esc(value)}</strong>"
            "</div>"
        )

    streak_items = []
    for item in flagged_streaks:
        streak_items.append(
            "<li class='mini-list-item'>"
            f"<strong>{esc(item['person_name'])}</strong> flagged for {item['streak']} consecutive days "
            f"(latest: {esc(item['last_date'])}; common: {esc(item['top_category'])})."
            "</li>"
        )
    if not streak_items:
        streak_items.append("<li class='mini-list-item'>No one has been flagged for 3 or more consecutive days.</li>")

    absence_items = []
    for item in absence_flags:
        absence_items.append(
            "<li class='mini-list-item'>"
            f"<strong>{esc(item.get('person_name', 'Unknown'))}</strong> "
            f"last seen {esc(item.get('last_seen_date', 'unknown'))}, "
            f"absent {esc(item.get('days_absent', 0))} day(s). "
            f"{esc(item.get('recommended_action', 'Follow up.'))}"
            "</li>"
        )
    if not absence_items:
        absence_items.append("<li class='mini-list-item'>No active absence flags.</li>")

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sentio Mind - {esc(SCHOOL)} Alert Digest</title>
  <style>
    :root {{
      --bg: #F8FAFC;
      --panel: #FFFFFF;
      --line: #E2E8F0;
      --ink: #0F172A;
      --muted: #475569;
      --soft: #F1F5F9;
      --soft-strong: #E8EEF7;
      --brand: #0F766E;
      --brand-deep: #134E4A;
      --brand-soft: #DFF7F3;
      --stone: #CBD5E1;
      --glow: rgba(15, 118, 110, 0.12);
      --urgent: #DC2626;
      --monitor: #D97706;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter , "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.10), transparent 30%),
        radial-gradient(circle at top right, rgba(148, 163, 184, 0.16), transparent 28%),
        linear-gradient(180deg, #F8FAFC 0%, #F1F5F9 100%);
      color: var(--ink);
    }}
    .page {{
      width: 11in;
      min-height: 8.5in;
      margin: 0 auto;
      padding: 0.45in 0.5in;
      background: var(--bg);
    }}
    .wrap {{ width: 100%; margin: 0 auto; }}
    h1, h2, h3, p {{ margin: 0; }}
    h1 {{ font-size: 34px; letter-spacing: -0.03em; }}
    h2 {{ font-size: 14px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); }}
    h3 {{ font-size: 16px; letter-spacing: 0.04em; text-transform: uppercase; color: var(--muted); }}
    .muted {{ color: var(--muted); }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 16px;
      margin-bottom: 14px;
      padding: 14px 16px;
      border: 1px solid rgba(226, 232, 240, 0.8);
      border-radius: 18px;
      background:
        linear-gradient(135deg, rgba(255,255,255,0.92) 0%, rgba(239,246,255,0.96) 100%);
      box-shadow: 0 18px 50px rgba(15, 23, 42, 0.05);
    }}
    .eyebrow {{
      display: inline-block;
      margin-bottom: 8px;
      padding: 6px 10px;
      border-radius: 999px;
      background: var(--brand-soft);
      color: var(--brand-deep);
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }}
    .title p {{
      margin-top: 4px;
      font-size: 15px;
    }}
    .title h1 {{
      color: #0B132B;
    }}
    .dashboard {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      box-shadow: 0 24px 60px rgba(15, 23, 42, 0.06);
    }}
    .kpi-row {{
      display: flex;
      margin-bottom: 14px;
      border: 1px solid var(--line);
      border-radius: 16px;
      overflow: hidden;
      background: linear-gradient(180deg, #F8FBFC 0%, #EFF6F9 100%);
    }}
    .kpi {{
      flex: 1 1 0;
      padding: 16px 18px 15px;
      min-width: 0;
      position: relative;
      background: transparent;
    }}
    .kpi + .kpi {{
      border-left: 1px solid var(--line);
    }}
    .kpi::before {{
      content: "";
      position: absolute;
      left: 14px;
      top: 10px;
      width: 28px;
      height: 3px;
      border-radius: 999px;
      background: linear-gradient(90deg, var(--brand) 0%, #38BDF8 100%);
    }}
    .kpi span {{
      display: block;
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.14em;
      margin-top: 8px;
    }}
    .kpi strong {{
      display: block;
      margin-top: 5px;
      font-size: 30px;
      font-weight: 700;
      letter-spacing: -0.03em;
      color: var(--brand-deep);
    }}
    .cards-wrap {{
      display: block;
      border: 1px solid var(--line);
      border-radius: 18px;
      overflow: hidden;
      background: #FFFFFF;
    }}
    .table-head {{
      display: grid;
      grid-template-columns: 220px 160px 1fr 170px;
      align-items: center;
      gap: 12px;
      padding: 14px 18px;
      background: linear-gradient(90deg, #115E59 0%, #1E293B 100%);
      color: #F8FAFC;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }}
    .alert-row {{
      display: grid;
      grid-template-columns: 220px 160px 1fr 170px;
      align-items: center;
      gap: 12px;
      padding: 14px 16px;
      border: 0;
      border-bottom: 1px solid var(--line);
      border-left: 4px solid transparent;
      border-radius: 0;
      background: linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(248,250,252,0.88) 100%);
      box-shadow: none;
    }}
    .alert-row:last-child {{
      border-bottom: 0;
    }}
    .severity-urgent {{ border-left-color: var(--urgent); }}
    .severity-monitor {{ border-left-color: var(--monitor); }}
    .severity-informational {{ border-left-color: #94A3B8; }}
    .table-student {{
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
      justify-content: flex-start;
      padding-right: 0;
      text-align: left;
    }}
    .avatar-wrap {{
      position: relative;
      width: 42px;
      height: 42px;
      flex: 0 0 42px;
    }}
    .student-meta {{ min-width: 0; flex: 1 1 auto; }}
    .student-meta strong {{
      display: block;
      font-size: 17px;
      line-height: 1.2;
      color: #0B132B;
    }}
    .student-meta span {{
      display: block;
      margin-top: 3px;
      font-size: 11px;
      font-weight: 500;
      color: #94A3B8;
    }}
    .sev-pill {{
      display: inline-block;
      margin-top: 5px;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.10em;
      text-transform: uppercase;
    }}
    .sev-pill-urgent {{
      background: #FEE2E2;
      color: #991B1B;
      border: 1px solid #FCA5A5;
    }}
    .sev-pill-monitor {{
      background: #FEF3C7;
      color: #92400E;
      border: 1px solid #FCD34D;
    }}
    .sev-pill-informational {{
      background: #F1F5F9;
      color: #475569;
      border: 1px solid #CBD5E1;
    }}
    .table-anomaly {{
      display: flex;
      align-items: center;
      justify-content: flex-start;
      min-width: 0;
      padding-right: 0;
      text-align: left;
    }}
    .table-description {{
      font-size: 15px;
      line-height: 1.5;
      color: #1E293B;
      min-width: 0;
    }}
    .table-trend {{
      display: flex;
      align-items: center;
      justify-content: flex-end;
      width: 170px;
      min-height: 56px;
    }}
    .anomaly-badge {{
      display: inline-block;
      width: fit-content;
      padding: 5px 8px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      white-space: nowrap;
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.45);
    }}
    .avatar, .avatar-fallback {{
      width: 42px;
      height: 42px;
      border-radius: 12px;
      object-fit: cover;
      border: 1px solid var(--line);
      background: linear-gradient(180deg, #F8FAFC 0%, #E2E8F0 100%);
      box-shadow: 0 8px 16px rgba(15, 23, 42, 0.08);
    }}
    .avatar-fallback {{
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.06em;
      color: #64748B;
      background: #F1F5F9;
      padding: 4px;
    }}
    .severity-dot {{
      position: absolute;
      top: -2px;
      right: -2px;
      width: 10px;
      height: 10px;
      border-radius: 999px;
      border: 2px solid #FFFFFF;
      box-shadow: 0 2px 8px rgba(15, 23, 42, 0.14);
    }}
    .severity-dot-urgent {{ background: var(--urgent); }}
    .severity-dot-monitor {{ background: var(--monitor); }}
    .severity-dot-informational {{ background: #94A3B8; }}
    .sparkline {{
      width: 156px;
      height: 52px;
      display: block;
    }}
    .footer-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-top: 12px;
    }}
    .mini-panel {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
      background:
        linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(248,250,252,0.92) 100%);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);
    }}
    .mini-panel h3 {{
      color: var(--brand-deep);
    }}
    .mini-list {{
      margin: 10px 0 0;
      padding-left: 16px;
    }}
    .mini-list-item {{
      font-size: 13px;
      line-height: 1.5;
      color: #1E293B;
      margin-bottom: 6px;
    }}
    .empty {{
      padding: 22px 14px;
      text-align: center;
      color: var(--muted);
      font-size: 14px;
    }}
    @page {{
      size: Letter landscape;
      margin: 0.45in 0.5in;
    }}
    @media print {{
      body, .page {{
        background: #FFFFFF;
      }}
      .header {{
        box-shadow: none !important;
        background: #FFFFFF !important;
      }}
      .dashboard, .mini-panel, .kpi {{
        box-shadow: none !important;
        background: #FFFFFF !important;
      }}
      .alert-row, .mini-panel, .kpi {{
        break-inside: avoid;
      }}
    }}
    @media (max-width: 1200px) {{
      .page {{
        width: auto;
        min-height: auto;
        padding: 16px;
      }}
    }}
    @media (max-width: 980px) {{
      .header {{
        flex-direction: column;
        align-items: flex-start;
      }}
      .kpi-row {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        overflow: visible;
        border: 0;
        background: transparent;
        gap: 12px;
      }}
      .kpi {{
        border: 1px solid var(--line);
        border-radius: 16px;
        background: linear-gradient(180deg, #F8FBFC 0%, #EFF6F9 100%);
      }}
      .kpi + .kpi {{
        border-left: 1px solid var(--line);
      }}
      .table-head {{
        display: none;
      }}
      .alert-row {{
        grid-template-columns: 1fr;
        align-items: start;
      }}
      .footer-grid {{
        grid-template-columns: 1fr;
      }}
    }}
    @media (max-width: 560px) {{
      .kpi-row {{
        grid-template-columns: 1fr;
      }}
      .page {{
        padding: 12px;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <div class="wrap">
      <div class="header">
        <div class="title">
          <div class="eyebrow">Sentio Mind Executive Dashboard</div>
          <h1>{esc(SCHOOL)} Behavioral Alert Digest</h1>
          <p class="muted">Generated {esc(datetime.now().strftime("%Y-%m-%d %H:%M"))} - Latest alert date: {esc(today_str)}</p>
        </div>
      </div>

      <section class="dashboard">
        <div class="kpi-row">
          {''.join(kpi_row)}
        </div>

        <div class="cards-wrap">
          <div class="table-head">
            <div>Student</div>
            <div>Anomaly</div>
            <div>Alert Description</div>
            <div style="text-align:right;">5-Day Trend</div>
          </div>
          {''.join(table_rows) if table_rows else "<div class='empty'>No alerts for the latest day in the dataset.</div>"}
        </div>

        <div class="footer-grid">
          <section class="mini-panel">
            <h3>Consecutive Flags</h3>
            <ul class="mini-list">{''.join(streak_items)}</ul>
          </section>
          <section class="mini-panel">
            <h3>Active Absences</h3>
            <ul class="mini-list">{''.join(absence_items)}</ul>
          </section>
        </div>
      </section>
    </div>
  </div>
</body>
</html>
"""

    output_path.write_text(html_doc, encoding="utf-8")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    daily_data = load_daily_data(DATA_DIR)
    all_dates  = sorted(daily_data.keys())
    print(f"Loaded {len(daily_data)} days: {all_dates}")

    # Build per-person history
    person_days = defaultdict(dict)
    person_info = {}
    for d, persons in daily_data.items():
        for pid, pdata in persons.items():
            person_days[pid][d] = pdata
            if pid not in person_info:
                person_info[pid] = pdata.get("person_info", {"name": pid, "profile_image_b64": ""})

    all_alerts    = []
    absence_flags = []

    for pid, days in person_days.items():
        sorted_days   = dict(sorted(days.items()))
        person_alerts = analyse_person(pid, sorted_days, person_info.get(pid, {}))
        all_alerts.extend(person_alerts)

        # Check absence
        present   = set(days.keys())
        absent    = 0
        for d in reversed(all_dates):
            if d not in present:
                absent += 1
            else:
                break
        if absent >= THRESHOLDS["absence_days"]:
            last_seen = sorted(present)[-1] if present else "unknown"
            absence_flags.append({
                "person_id":        pid,
                "person_name":      person_info.get(pid, {}).get("name", pid),
                "last_seen_date":   last_seen,
                "days_absent":      absent,
                "recommended_action": "Welfare check — contact family if absent again tomorrow",
            })

    sev_order = {"urgent": 0, "monitor": 1, "informational": 2}
    all_alerts.sort(key=lambda a: sev_order.get(a.get("severity", "informational"), 3))

    latest_date = all_dates[-1] if all_dates else str(date.today())
    previous_date = all_dates[-2] if len(all_dates) > 1 else None
    flagged_today = len({a.get("person_id") for a in all_alerts if a.get("date") == latest_date})
    flagged_yesterday = len({a.get("person_id") for a in all_alerts if a.get("date") == previous_date}) if previous_date else 0
    cat_counter   = Counter(a.get("category") for a in all_alerts)
    top_category  = cat_counter.most_common(1)[0][0] if cat_counter else "none"
    today_wellbeings = [p["wellbeing"] for p in daily_data[latest_date].values()] if all_dates else []
    avg_wellbeing_today = round(float(np.mean(today_wellbeings)), 1) if today_wellbeings else 0

    school_summary = {
        "total_persons_tracked":       len(person_days),
        "persons_flagged_today":       flagged_today,
        "persons_flagged_yesterday":   flagged_yesterday,
        "most_common_anomaly_this_week": top_category,
        "school_avg_wellbeing_today":  avg_wellbeing_today,
    }

    feed = {
        "source":        "p5_anomaly_detection",
        "generated_at":  datetime.now().isoformat(),
        "school":        SCHOOL,
        "alert_summary": {
            "total_alerts":  len(all_alerts),
            "urgent":        sum(1 for a in all_alerts if a.get("severity") == "urgent"),
            "monitor":       sum(1 for a in all_alerts if a.get("severity") == "monitor"),
            "informational": sum(1 for a in all_alerts if a.get("severity") == "informational"),
        },
        "alerts":        all_alerts,
        "absence_flags": absence_flags,
        "school_summary": school_summary,
    }

    with open(FEED_OUT, "w") as f:
        json.dump(feed, f, indent=2)

    generate_alert_digest(all_alerts, absence_flags, school_summary, REPORT_OUT)

    print()
    print("=" * 50)
    print(f"  Alerts:  {feed['alert_summary']['total_alerts']} total  "
          f"({feed['alert_summary']['urgent']} urgent, {feed['alert_summary']['monitor']} monitor)")
    print(f"  Absence flags: {len(absence_flags)}")
    print(f"  Report -> {REPORT_OUT}")
    print(f"  JSON   -> {FEED_OUT}")
    print("=" * 50)


# direct the user to open the report in their web browser after generation  
import webbrowser
webbrowser.open(str(REPORT_OUT.resolve()))