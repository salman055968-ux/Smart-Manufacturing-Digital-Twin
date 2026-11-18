"""Smart Manufacturing Digital Twin - 492CPE industrial trends educational demo."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from simulation import (
    MACHINE_NAMES, machine_risk, new_state, risk_label, run_hour,
    schedule_maintenance, summary, upgrade_machine,
)

st.set_page_config(page_title="Smart Manufacturing | Digital Twin", page_icon="🏭", layout="wide")

st.markdown("""
<style>
:root { --accent: #2dd4bf; }
[data-testid="stAppViewContainer"] {background: linear-gradient(160deg,#08111e 0%,#0c1928 65%,#08111e 100%);color:#dbe8f2;}
[data-testid="stHeader"] {background:rgba(8,17,30,.88);}
[data-testid="stSidebar"] {background:#0f1d2d;}
[data-testid="stMetric"] {background:#102338;border:1px solid #214253;border-radius:14px;padding:14px;}
[data-testid="stMetricLabel"] {color:#9fb6c6;}
[data-testid="stMetricValue"] {color:#e7f7f3;}
[data-testid="stVerticalBlockBorderWrapper"] {border-color:#214253;}
.hero {padding:1.3rem 1.5rem;border:1px solid #24504e;border-radius:16px;
background:linear-gradient(100deg,#0c302f,#102239);margin:0 0 1.2rem 0;}
.hero h1 {font-size:2.05rem;color:#e7faf7;margin:0 0 .4rem 0;}
.kicker {color:#5eead4;letter-spacing:2.5px;font-weight:700;font-size:.75rem;}
.sub {color:#b3cdd5;font-size:.95rem;margin:.1rem 0 0;}
.machine {padding:1rem 1.2rem;background:#0f2233;border:1px solid #254457;border-radius:13px;min-height:143px;}
.machine h4 {color:#e2f7f6;margin:.15rem 0 .6rem;}
.ok {color:#2dd4bf;font-weight:700;} .warn {color:#fbbe59;font-weight:700;}
.bad {color:#ff7b87;font-weight:700;}
small, .muted {color:#aac1ca;}
div.stButton > button[kind="primary"] {background:#0b9c8f;color:#fff;border:0;}
</style>""", unsafe_allow_html=True)

if "twin" not in st.session_state:
    st.session_state.twin = new_state()
if "notice" not in st.session_state:
    st.session_state.notice = ""

state = st.session_state.twin

with st.sidebar:
    st.markdown("### ⚙️ Simulation controls")
    scenario = st.selectbox(
        "Inject a scenario (next simulated hour)",
        ["Normal operation", "Machine overheating", "Equipment breakdown", "Quality issue", "Material shortage"],
    )
    raw_supply = st.slider("Raw material supply per hour", 10, 90, 60, 5)
    defect_rate = st.slider("Base defect rate (%)", 0.0, 12.0, 3.5, 0.5)
    target = st.slider("Good-unit target per hour", 20, 55, 38, 1)
    if st.button("▶ Simulate next hour", type="primary", use_container_width=True):
        run_hour(state, scenario, raw_supply, defect_rate)
        st.session_state.notice = f"Simulated hour {state['hour']} using: {scenario}."
        st.rerun()
    if st.button("⏩ Simulate remaining 8-hour shift", use_container_width=True):
        remaining = max(0, 8 - state["hour"])
        if remaining:
            for _ in range(remaining):
                run_hour(state, scenario, raw_supply, defect_rate)
            st.session_state.notice = f"Shift simulation complete: {remaining} additional hours."
        else:
            st.session_state.notice = "Eight-hour shift already completed. Reset to try another shift."
        st.rerun()
    if st.button("↻ Reset simulation", use_container_width=True):
        st.session_state.twin = new_state()
        st.session_state.notice = "Simulation reset to initial conditions."
        st.rerun()
    st.divider()
    st.markdown("### 🔧 Maintenance and upgrades")
    selected = st.selectbox("Machine", MACHINE_NAMES)
    if st.button("Schedule preventive maintenance", use_container_width=True):
        st.session_state.notice = schedule_maintenance(state, selected)
        st.rerun()
    if st.button("Upgrade / replace this machine", use_container_width=True):
        st.session_state.notice = upgrade_machine(state, selected)
        st.rerun()
    st.caption("Maintenance acts next simulated hour. Upgrade acts immediately; all values are hypothetical.")

st.markdown("""
<div class="hero">
<div class="kicker">KING KHALID UNIVERSITY · 492CPE · INDUSTRIAL TRENDS</div>
<h1>🏭 Smart Manufacturing Digital Twin</h1>
<p class="sub">Virtual production line · Live operating indicators · Fault prediction · Maintenance & lifecycle decisions</p>
</div>
""", unsafe_allow_html=True)

if st.session_state.notice:
    st.info(st.session_state.notice)

stats = summary(state, target)
a, b, c, d, e = st.columns(5)
a.metric("Good products", stats["good"])
b.metric("Defective products", stats["defective"])
c.metric("Quality yield", f"{stats['yield_pct']}%")
d.metric("Total downtime", f"{stats['downtime']} min")
e.metric("Production hour", f"{state['hour']} / 8")

st.write("")
views = st.tabs(["🏗️ Production line", "📊 Performance", "🌡️ Predictive maintenance", "♻️ Product lifecycle", "🧪 Test evidence"])

with views[0]:
    st.subheader("Virtual production process")
    st.caption("Raw materials → Cutting → Assembly → Inspection → Finished goods")
    st.code("RAW MATERIALS  ──▶  CUTTING  ──▶  ASSEMBLY  ──▶  INSPECTION  ──▶  GOOD PRODUCTS", language="text")
    cols = st.columns(3)
    for col, name in zip(cols, MACHINE_NAMES):
        m = state["machines"][name]
        risk = machine_risk(m)
        color = "bad" if risk >= 70 else "warn" if risk >= 40 else "ok"
        with col:
            st.markdown(f"""
            <div class="machine"><h4>{name}</h4>
            <div><span class="muted">Status:</span> <b>{m['last_status']}</b></div>
            <div><span class="muted">Capacity:</span> <b>{m['capacity']} units / hour</b></div>
            <div><span class="muted">Temperature:</span> <b>{m['temperature']:.1f} °C</b></div>
            <div><span class="muted">Wear:</span> <b>{m['wear']:.1f}%</b></div>
            <div><span class="muted">Risk:</span> <span class="{color}">{risk}/100 · {risk_label(risk)}</span></div>
            </div>""", unsafe_allow_html=True)
            st.progress(min(1.0, m["wear"] / 100), text=f"Machine wear: {m['wear']:.0f}%")
    st.divider()
    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Raw material buffer", state["raw_buffer"])
    b2.metric("Waiting for assembly", state["wip_cut"])
    b3.metric("Waiting for inspection", state["wip_assembly"])
    b4.metric("Inspected units", state["checked"])
    st.caption("The simulation uses simplified hourly flow calculations, not physical sensor data.")

with views[1]:
    st.subheader("Production performance")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Good units/hour", stats["throughput"])
    c2.metric("Machine utilization", f"{stats['utilization_pct']}%")
    c3.metric("Production target reached", f"{stats['target_pct']}%")
    c4.metric("Simulated cost", f"{stats['cost']} credits")
    if state["history"]:
        df = pd.DataFrame(state["history"])
        x, y = st.columns(2)
        with x:
            st.markdown("**Production by hour**")
            st.line_chart(df.set_index("Hour")[["Good units", "Defective units"]])
        with y:
            st.markdown("**Cumulative good production**")
            st.line_chart(df.set_index("Hour")[["Good cumulative"]])
        st.markdown("**Work-in-progress / bottleneck**")
        st.line_chart(df.set_index("Hour")[["Cut WIP", "Assembly WIP"]])
    else:
        st.info("Click 'Simulate next hour' to generate production measurements.")

with views[2]:
    st.subheader("Rule-based equipment problem prediction")
    st.warning("Risk scores are educational heuristic indicators, NOT machine-learning predictions or actual failure probabilities.")
    rows = []
    for name, m in state["machines"].items():
        score = machine_risk(m)
        action = ("Schedule maintenance or consider replacement" if score >= 70
                  else "Plan preventive maintenance soon" if score >= 40
                  else "Continue monitoring")
        rows.append({"Machine": name, "Temperature (°C)": round(m["temperature"], 1),
                     "Wear (%)": round(m["wear"], 1), "Risk score /100": score,
                     "Risk level": risk_label(score), "Decision support": action})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.markdown("**Transparent prediction rule**")
    st.code("risk_score = 0.65 × wear + 1.55 × max(0, temperature - 55)", language="text")
    st.caption("Score is capped between 0 and 100. HIGH ≥ 70; MODERATE ≥ 40; LOW < 40.")
    if state["history"]:
        df = pd.DataFrame(state["history"])
        st.markdown("**Machine risk trends**")
        st.line_chart(df.set_index("Hour")[[f"{name} risk" for name in MACHINE_NAMES]])

with views[3]:
    st.subheader("Equipment and product lifecycle decisions")
    st.markdown("The model supports decisions about **maintenance, equipment replacement, and product quality improvement**.")
    recommendations = []
    for name, m in state["machines"].items():
        risk = machine_risk(m)
        if risk >= 70:
            decision = "HIGH risk: schedule maintenance. Consider upgrading if issues recur."
        elif risk >= 40:
            decision = "MODERATE risk: plan preventive maintenance."
        else:
            decision = "LOW risk: monitor and continue operating."
        recommendations.append({"Asset": name, "Capacity / hour": m["capacity"],
                                "Risk": risk_label(risk), "Suggested decision": decision,
                                "Upgraded?": "Yes" if m["upgraded"] else "No"})
    st.dataframe(pd.DataFrame(recommendations), use_container_width=True, hide_index=True)
    if stats["yield_pct"] and stats["yield_pct"] < 95:
        st.error("Product lifecycle recommendation: investigate inspection quality; measured yield is below 95%.")
    elif state["hour"]:
        st.success("Product lifecycle recommendation: quality is meeting the 95% simulation benchmark.")
    else:
        st.info("Run the line to receive a recommendation based on measured quality.")
    st.markdown("""**Model decision assumptions:** preventive maintenance costs 75 credits and requires 15 min;
    upgrading costs 600 credits and increases a machine's nominal capacity by 20%.
    These values are training assumptions; they are not real supplier quotes.""")

with views[4]:
    st.subheader("Fault injection and test records")
    st.markdown("Use the sidebar's **Inject a scenario** field and run one simulated hour for each experiment.")
    st.markdown("""
    | Test | Expected observable effect |
    |---|---|
    | Normal operation | Goods produced and station statistics update |
    | Machine overheating | Assembly interlock, cooling and downtime |
    | Equipment breakdown | Cutting capacity reduced and 45 min downtime |
    | Quality issue | Defective output increases |
    | Material shortage | Raw input falls to 15 units |
    """)
    if state["history"]:
        df = pd.DataFrame(state["history"])
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇ Download simulation results (CSV)", data=csv,
                           file_name="digital_twin_test_results.csv", mime="text/csv")
    else:
        st.info("No tests recorded yet. Run a scenario to start collecting evidence.")
    if state["events"]:
        st.markdown("**Controller event log (newest first)**")
        for evt in state["events"][:30]:
            st.caption(f"Hour {evt['hour']} · {evt['type']} · {evt['message']}")

st.divider()
st.caption("Industrial Trends 492CPE | Educational software digital twin | No real equipment connected | Built with Python + Streamlit")
