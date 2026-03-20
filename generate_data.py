import json
import os
import random

random.seed(42)

# Create folders
os.makedirs("sample_data", exist_ok=True)
os.makedirs("images", exist_ok=True)  # ensure images folder exists

# Updated names (matching your images)
names = [
    "AARAV", "Anamika", "Harshita", "Jahanvi", "Manav",
    "Mohini", "Ranjhana", "Rohini", "Sparshita", "Sushmita",
    "Student11", "Student12", "Student13", "Student14", "Student15",
    "Student16", "Student17", "Student18", "Student19", "Student20"
]

students = [f"S{i}" for i in range(1, 21)]


def create_day(day):
    data = {
        "date": f"2026-01-0{day}",
        "persons": []
    }

    for i, sid in enumerate(students):

        # 🔴 ABSENCE → S10 missing after Day 3
        if sid == "S10" and day >= 4:
            continue

        base = 65

        wellbeing = base
        social = base - random.randint(0, 5)
        energy_p = random.randint(35, 50)
        energy_m = random.randint(30, 45)

        gaze = random.choice(["forward", "side", "down"])
        eye = random.choice([True, True, False])

        # ---------------- ANOMALY PATTERNS ----------------

        # 🔴 S1 → Sudden Drop
        if sid == "S1":
            if day == 4:
                wellbeing = 40
            if day == 5:
                wellbeing = 35

        # 🔴 S2 → Sustained Low
        if sid == "S2" and day >= 3:
            wellbeing = 42 - day

        # 🔴 S3 → Hyperactivity
        if sid == "S3" and day >= 4:
            energy_p = 85
            energy_m = 80

        # 🔴 S5 → Social Withdrawal
        if sid == "S5" and day >= 4:
            social = 20
            gaze = "down"

        # 🔴 S7 → Gaze Avoidance
        if sid == "S7" and day >= 3:
            eye = False

        # 🔴 S9 → Regression
        if sid == "S9":
            if day == 1:
                wellbeing = 50
            elif day == 2:
                wellbeing = 60
            elif day == 3:
                wellbeing = 70
            elif day == 4:
                wellbeing = 40

        # 🔴 EXTRA ANOMALIES

        if sid in ["S11", "S12"] and day >= 4:
            wellbeing = 38

        if sid in ["S13", "S14"] and day >= 3:
            wellbeing = 40

        if sid in ["S15", "S16"] and day >= 4:
            social = 20
            gaze = "down"

        if sid in ["S17", "S18"] and day >= 3:
            eye = False

        if sid == "S19" and day >= 4:
            energy_p = 90
            energy_m = 85

        # --------------------------------------------------

        name = names[i]

        data["persons"].append({
            "person_id": sid,
            "name": name,
            "image_path": f"images/{name}.png",  # 🔥 image added here
            "wellbeing_score": wellbeing,
            "social_engagement": social,
            "physical_energy": energy_p,
            "movement_energy": energy_m,
            "gaze_direction": gaze,
            "eye_contact": eye
        })

    return data


# Generate 5 days
for day in range(1, 6):
    d = create_day(day)

    with open(f"sample_data/analysis_Day{day}.json", "w") as f:
        json.dump(d, f, indent=2)

print("✅ Dataset generated with image paths!")