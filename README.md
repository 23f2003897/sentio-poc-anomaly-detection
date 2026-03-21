# Sentio Mind — Behavioral Anomaly & Early Distress Detection

This project detects **early signs of distress and behavioral anomalies** in students using historical wellbeing data.

It builds **personal baselines** for each individual and identifies deviations such as sudden drops, sustained distress, social withdrawal, and absence.

---

## Problem Statement

Traditional systems only **visualize scores and trends** but do not proactively alert stakeholders.

> A student may show distress for days before anyone notices.

This project adds an **intelligent alert layer** on top of existing analytics.

---

## 🧩 Solution Overview

## System Workflow Breakdown

1. **Multi-day data loading**  
   - Iterates through sequential `analysis_DayX.json` files to build longitudinal student history  

2. **Baseline computation**  
   - Uses first 3 days to calculate:
     - Mean (μ)  
     - Standard deviation (σ)  
   - Applied to wellbeing, social engagement, and physical traits  

3. **Intelligent anomaly detection**  
   - **Intra-personal**: Detects shifts against personal baseline (e.g., SUDDEN_DROP, HYPERACTIVITY_SPIKE)  
   - **Inter-personal (bonus)**: Uses `2σ` rule to flag PEER_OUTLIER vs cohort average  
   - **Contextual logic**: Combines behavioral + physical signals (e.g., low engagement + downward gaze → SOCIAL_WITHDRAWAL)  

4. **Privacy & portability**  
   - `alert_digest.html` is fully self-contained  
   - Embeds CSS, SVG, and images as Base64  
   - Works offline, no external CDNs  

5. **Dual-output generation**  
   - `alert_feed.json`: Structured, schema-compliant for system integration , machine readable 
   - `alert_digest.html`: Executive dashboard with color-coded alerts and sparklines  

---

## 🏗️ Architecture

```mermaid
flowchart TD
    A[Daily JSON Data] --> B[Data Loader]
    B --> C[Per Student History Builder]
    C --> D[Baseline Computation]

    D --> E1[Sudden Drop Detector]
    D --> E2[Sustained Low Detector]
    D --> E3[Social Withdrawal Detector]
    D --> E4[Hyperactivity Spike Detector]
    D --> E5[Regression Detector]
    D --> E6[Gaze Avoidance Detector]

    C --> F[Absence Detection]
    C --> G[Peer Outlier Detection]

    E1 --> H[Alert Aggregator]
    E2 --> H
    E3 --> H
    E4 --> H
    E5 --> H
    E6 --> H
    F --> H
    G --> H

    H --> I[alert_feed.json]
    H --> J[alert_digest.html]
```
----
## ⚙️ Installation

```bash
pip install numpy
```
### Requirements: Python 3.9+
---
## ▶️ Run the Project

```bash
python solution.py
```
## 📂 Output Files

- `alert_feed.json`
- `alert_digest.html`
---
## 📊 Anomaly Categories

| Category              | Description                                             |
|----------------------|---------------------------------------------------------|
| SUDDEN_DROP          | Wellbeing drops ≥ 20 points from baseline               |
| SUSTAINED_LOW        | Wellbeing < 45 for ≥ 3 days                             |
| SOCIAL_WITHDRAWAL    | Drop in social engagement + downward gaze               |
| HYPERACTIVITY_SPIKE  | Energy increases ≥ 40 points                            |
| REGRESSION           | Recovery followed by sudden drop                        |
| GAZE_AVOIDANCE       | No eye contact for ≥ 3 days                             |
| ABSENCE_FLAG         | Student missing ≥ 2 consecutive days                    |
| PEER_OUTLIER         | Significantly below peer average                        |

---
## 📈 Baseline Logic

- Uses first **3 days** of data  
- Computes:
  - Mean wellbeing  
  - Standard deviation  
  - Trait averages  

### ⚙️ Adaptive Threshold

- If baseline variability is high:
  - `std > 15` → increase detection threshold by **50%**

---
## 📄 Output Formats

### 1. `alert_feed.json`

Machine-readable alert structure:

```json
{
  "person_id": "S1",
  "category": "SUSTAINED_LOW",
  "severity": "urgent",
  "description": "Wellbeing stayed below threshold",
  "date": "2026-01-05"
}
```
### 2. `alert_digest.html`

Interactive dashboard with:

- KPI summary  
- Alert table  
- Trend sparklines  
- Highlighted high-risk student  
- Absence tracking
---
## 📊 Dashboard Features

- KPI metrics (Total, Flagged, Avg Wellbeing)
- Highlight: Highest risk student
- Sparklines for trend visualization
- Severity-based color coding
- Student-wise anomaly breakdown
- Absence alerts
- Fully offline (no CDN)
---
## Key Design Decisions

- Personalized baselines  
  - Each student is evaluated against their own normal, not global thresholds  

- Multi-signal detection  
  - Combines:
    - Behavioral metrics  
    - Social engagement  
    - Non-verbal cues (gaze, eye contact)  

- Temporal awareness  
  - Uses historical sequences to detect:
    - Trends  
    - Regression  
    - Sustained patterns  

- Alert prioritization  
  - Alerts categorized as:
    - **Urgent**: Triggers a red left-border and status dot  
    - **Monitor**: Triggers an amber left-border and status dot    

- Offline-first dashboard  
  - No external dependencies  
  - Works without internet
---

##📁 Project Structure
```
.
├── solution.py
├── sample_data/
│ ├── day1.json
│ ├── day2.json
│ └── ...
├── alert_feed.json
├── alert_digest.html
└── README.md
```
---
## Conclusion

This system enables early detection of student distress, helping institutions take timely and proactive action.

### From passive analytics → intelligent intervention
---
## Author

**Khusbu Pandey**  
**23f2003897@ds.study.iitm.ac.in**
---
