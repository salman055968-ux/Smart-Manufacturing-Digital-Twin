"""Deterministic educational manufacturing digital twin (not a real plant or ML model)."""
from __future__ import annotations

MACHINE_NAMES = ("Cutting", "Assembly", "Inspection")
BASE_CAPACITIES = {"Cutting": 55, "Assembly": 44, "Inspection": 40}
COST_PER_DEFECT = 20
MAINTENANCE_COST = 75
UPGRADE_COST = 600


def new_state():
    return {
        "hour": 0, "good": 0, "defective": 0, "checked": 0,
        "total_cut": 0, "total_assembled": 0, "downtime_minutes": 0,
        "operating_minutes": 0.0, "cost": 0, "raw_buffer": 0,
        "wip_cut": 0, "wip_assembly": 0,
        "machines": {
            name: {
                "capacity": BASE_CAPACITIES[name],
                "temperature": {"Cutting": 43.0, "Assembly": 48.0, "Inspection": 42.0}[name],
                "wear": {"Cutting": 18.0, "Assembly": 29.0, "Inspection": 23.0}[name],
                "upgraded": False, "maintenance_pending": False,
                "last_status": "READY", "last_util": 0.0,
            }
            for name in MACHINE_NAMES
        },
        "history": [], "events": [],
    }


def add_event(state, message, kind="INFO"):
    state["events"].insert(0, {"hour": state["hour"], "message": message, "type": kind})
    state["events"] = state["events"][:80]


def machine_risk(machine):
    """Transparent rule-based risk index, 0..100; NOT a statistical failure probability."""
    score = 0.65 * machine["wear"] + 1.55 * max(0.0, machine["temperature"] - 55.0)
    return int(max(0, min(100, round(score))))


def risk_label(score):
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MODERATE"
    return "LOW"


def schedule_maintenance(state, machine_name):
    machine = state["machines"][machine_name]
    if machine["maintenance_pending"]:
        return "Maintenance already scheduled for the next hour."
    machine["maintenance_pending"] = True
    add_event(state, f"Preventive maintenance scheduled: {machine_name} (next production hour).")
    return f"Maintenance scheduled for {machine_name} in the next simulation hour."


def upgrade_machine(state, machine_name):
    machine = state["machines"][machine_name]
    if machine["upgraded"]:
        return f"{machine_name} is already upgraded."
    machine["upgraded"] = True
    machine["capacity"] = round(BASE_CAPACITIES[machine_name] * 1.20)
    machine["wear"] = 8.0
    machine["temperature"] = 40.0
    machine["maintenance_pending"] = False
    state["cost"] += UPGRADE_COST
    add_event(state, f"Equipment lifecycle decision: {machine_name} upgraded (+20% capacity, {UPGRADE_COST} credits).", "ACTION")
    return f"{machine_name} upgraded. New capacity: {machine['capacity']} units/hour."


def run_hour(state, scenario="Normal operation", raw_supply=60, base_defect_pct=3.5):
    if scenario not in {"Normal operation", "Machine overheating", "Equipment breakdown", "Quality issue", "Material shortage"}:
        raise ValueError("Unknown test scenario")
    if raw_supply < 0 or not (0 <= base_defect_pct <= 100):
        raise ValueError("Invalid simulation settings")

    state["hour"] += 1
    hour = state["hour"]
    machine_ops = {}
    total_down = 0
    effective = {}
    health_notes = []

    # Faults are injected for a single hour. Overheating impacts Assembly;
    # mechanical breakdown impacts Cutting; quality issues impact inspection yield.
    for name in MACHINE_NAMES:
        m = state["machines"][name]
        down = 0
        m["last_status"] = "RUNNING"
        if m["maintenance_pending"]:
            down += 15
            state["cost"] += MAINTENANCE_COST
            m["wear"] = max(5, m["wear"] - 30)
            m["temperature"] = max(35, m["temperature"] - 16)
            m["maintenance_pending"] = False
            m["last_status"] = "MAINTENANCE"
            add_event(state, f"{name}: preventive maintenance completed (15 min).", "ACTION")
        if scenario == "Machine overheating" and name == "Assembly":
            m["temperature"] += 34
            add_event(state, "Overheating fault injected at Assembly.", "FAULT")
        if scenario == "Equipment breakdown" and name == "Cutting":
            down += 45
            m["wear"] = min(100, m["wear"] + 12)
            m["last_status"] = "BREAKDOWN"
            add_event(state, "Cutting breakdown detected; production reduced for safety (45 min).", "FAULT")
        if m["temperature"] >= 80:
            # Safety stop: cannot run at full production during excessive heat.
            down = max(down, 45)
            m["last_status"] = "SAFETY STOP"
            m["temperature"] -= 18
            add_event(state, f"{name}: high-temperature interlock; 45-min safety stop and cooling.", "FAULT")
        down = min(60, down)
        total_down += down
        available_fraction = (60 - down) / 60
        effective[name] = int(m["capacity"] * available_fraction)
        machine_ops[name] = {"downtime": down, "capacity": effective[name]}

    incoming = 15 if scenario == "Material shortage" else raw_supply
    if scenario == "Material shortage":
        add_event(state, "Material delivery shortage: only 15 raw units received.", "FAULT")
    state["raw_buffer"] += incoming
    cut = min(state["raw_buffer"], effective["Cutting"])
    state["raw_buffer"] -= cut
    state["wip_cut"] += cut
    assembled = min(state["wip_cut"], effective["Assembly"])
    state["wip_cut"] -= assembled
    state["wip_assembly"] += assembled
    inspected = min(state["wip_assembly"], effective["Inspection"])
    state["wip_assembly"] -= inspected

    inspection_machine = state["machines"]["Inspection"]
    defect_pct = base_defect_pct + 0.025 * inspection_machine["wear"]
    if scenario == "Quality issue":
        defect_pct += 13.0
        add_event(state, "Quality drift: defect rate increased for this hour.", "FAULT")
    defects = min(inspected, round(inspected * defect_pct / 100))
    good = inspected - defects

    state["total_cut"] += cut
    state["total_assembled"] += assembled
    state["checked"] += inspected
    state["defective"] += defects
    state["good"] += good
    state["cost"] += COST_PER_DEFECT * defects

    processed = {"Cutting": cut, "Assembly": assembled, "Inspection": inspected}
    for name in MACHINE_NAMES:
        m = state["machines"][name]
        utilization = (processed[name] / m["capacity"]) if m["capacity"] else 0
        m["last_util"] = round(utilization * 100, 1)
        state["operating_minutes"] += utilization * 60
        m["wear"] = min(100, m["wear"] + 3.0 * utilization)
        m["temperature"] = max(34, min(105, m["temperature"] + 8 * utilization - 4))
        if m["last_status"] == "RUNNING" and processed[name] == 0:
            m["last_status"] = "IDLE"
        machine_ops[name]["output"] = processed[name]
        machine_ops[name]["temperature"] = round(m["temperature"], 1)
        machine_ops[name]["wear"] = round(m["wear"], 1)
        machine_ops[name]["risk"] = machine_risk(m)
        machine_ops[name]["status"] = m["last_status"]
        if machine_risk(m) >= 70:
            health_notes.append(name)

    state["downtime_minutes"] += total_down
    if health_notes:
        add_event(state, f"Maintenance warning: high risk on {', '.join(health_notes)}.", "WARNING")
    add_event(state, f"Hour {hour}: {good} good, {defects} defective; {total_down} min total machine downtime.")

    row = {
        "Hour": hour, "Scenario": scenario, "Raw delivered": incoming,
        "Cut units": cut, "Assembled units": assembled,
        "Inspected units": inspected, "Good units": good, "Defective units": defects,
        "Good cumulative": state["good"], "Defective cumulative": state["defective"],
        "Raw buffer": state["raw_buffer"], "Cut WIP": state["wip_cut"],
        "Assembly WIP": state["wip_assembly"],
        "Downtime min": total_down,
        "Cost cumulative (credits)": state["cost"],
    }
    for name in MACHINE_NAMES:
        row[f"{name} risk"] = machine_ops[name]["risk"]
        row[f"{name} temperature C"] = machine_ops[name]["temperature"]
    state["history"].append(row)
    return row


def summary(state, target_per_hour=38):
    checked = state["checked"]
    hours = state["hour"]
    return {
        "good": state["good"],
        "defective": state["defective"],
        "yield_pct": round(100 * state["good"] / checked, 1) if checked else 0,
        "target_pct": round(100 * state["good"] / (hours * target_per_hour), 1) if hours and target_per_hour else 0,
        "throughput": round(state["good"] / hours, 1) if hours else 0,
        "utilization_pct": round(100 * state["operating_minutes"] / (3 * 60 * hours), 1) if hours else 0,
        "downtime": state["downtime_minutes"],
        "cost": state["cost"],
    }
