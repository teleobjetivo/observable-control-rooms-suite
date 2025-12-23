"""
Ops Cell Lite 🧠⚙️
Autor: Hugo Baghetti (@tele.objetivo)

Yo construí este demo para mostrar una “célula” multi-agente simplificada:
1) Sensor Agent: genera / ingiere señales operacionales
2) Anomaly Agent: detecta anomalías con reglas claras
3) Explainer Agent: explica por qué saltó la alerta (top drivers)
4) Reviewer Agent (HITL): permite aprobar/rechazar y guardar feedback
5) Narrator Agent: produce un reporte ejecutivo final (Markdown)

Objetivo: una app visual que se vea “grande”, pero que sea rápida, reproducible y sin humo.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


# -----------------------------
# Page
# -----------------------------
st.set_page_config(page_title="Ops Cell Lite", layout="wide")
st.title("🧠⚙️ Ops Cell Lite")
st.caption("Multi-agente lite · observabilidad · human-in-the-loop · reporte final")

OUT_DIR = Path("outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------
# Data + Policy
# -----------------------------
@dataclass
class Thresholds:
    latency_p95_ms: int
    error_rate_pct: float
    volume_drop_pct: float
    saturation_pct: float


@dataclass
class Incident:
    incident_id: str
    ts: str
    severity: str
    signals: Dict
    drivers: List[Dict]
    recommendation: str
    reviewer: Dict


# -----------------------------
# Utilities
# -----------------------------
def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


@st.cache_data
def synth_signals(seed: int, hours: int, baseline: str) -> pd.DataFrame:
    """
    Sensor Agent: datos operacionales sintéticos, realistas.
    baseline: 'stable' | 'noisy' | 'peak'
    """
    rng = np.random.default_rng(seed)
    t0 = datetime.now() - timedelta(hours=hours)
    ts = [t0 + timedelta(minutes=15 * i) for i in range((hours * 60) // 15)]

    n = len(ts)

    # Baselines
    if baseline == "stable":
        lat_base, err_base, vol_base = 220, 0.6, 1000
        noise = 1.0
    elif baseline == "noisy":
        lat_base, err_base, vol_base = 260, 0.9, 1050
        noise = 1.6
    else:  # peak
        lat_base, err_base, vol_base = 320, 1.2, 1400
        noise = 1.4

    latency = rng.normal(lat_base, 45 * noise, size=n)
    errors = rng.normal(err_base, 0.25 * noise, size=n)
    volume = rng.normal(vol_base, 120 * noise, size=n)
    saturation = rng.normal(55 if baseline != "peak" else 68, 10 * noise, size=n)

    latency = np.clip(latency, 80, 1500)
    errors = np.clip(errors, 0.01, 15.0)
    volume = np.clip(volume, 50, 5000)
    saturation = np.clip(saturation, 5, 98)

    df = pd.DataFrame({
        "ts": ts,
        "latency_p95_ms": latency,
        "error_rate_pct": errors,
        "volume_rpm": volume,
        "saturation_pct": saturation,
    })

    # Inyectar 2–3 incidentes controlados
    spikes = rng.integers(low=int(n * 0.15), high=int(n * 0.9), size=3)
    for i, idx in enumerate(spikes):
        width = int(rng.integers(3, 8))
        sl = slice(idx, min(n, idx + width))

        kind = ["latency", "errors", "volume"][i % 3]
        if kind == "latency":
            df.loc[sl, "latency_p95_ms"] *= rng.uniform(1.8, 2.6)
            df.loc[sl, "saturation_pct"] *= rng.uniform(1.1, 1.3)
        elif kind == "errors":
            df.loc[sl, "error_rate_pct"] *= rng.uniform(2.0, 4.0)
        else:  # volume drop
            df.loc[sl, "volume_rpm"] *= rng.uniform(0.35, 0.6)

    # Suavizado leve
    for c in ["latency_p95_ms", "error_rate_pct", "volume_rpm", "saturation_pct"]:
        df[c] = df[c].rolling(2, min_periods=1).mean()

    return df


def detect_anomalies(df: pd.DataFrame, thr: Thresholds) -> pd.DataFrame:
    """
    Anomaly Agent: reglas claras, interpretables.
    """
    out = df.copy()

    # Baseline para volumen (comparación rolling)
    out["vol_ma"] = out["volume_rpm"].rolling(12, min_periods=6).mean()
    out["vol_drop_pct"] = (1 - (out["volume_rpm"] / out["vol_ma"])) * 100

    out["a_latency"] = out["latency_p95_ms"] > thr.latency_p95_ms
    out["a_errors"] = out["error_rate_pct"] > thr.error_rate_pct
    out["a_volume"] = out["vol_drop_pct"] > thr.volume_drop_pct
    out["a_saturation"] = out["saturation_pct"] > thr.saturation_pct

    out["anomaly_count"] = out[["a_latency", "a_errors", "a_volume", "a_saturation"]].sum(axis=1)

    # Severidad simple (0..3)
    def sev(row) -> str:
        k = int(row["anomaly_count"])
        if k >= 3:
            return "Critical"
        if k == 2:
            return "High"
        if k == 1:
            return "Medium"
        return "OK"

    out["severity"] = out.apply(sev, axis=1)
    return out


def top_drivers(row: pd.Series, thr: Thresholds) -> List[Dict]:
    """
    Explainer Agent: top drivers por distancia al umbral.
    """
    drivers = []

    # Latency
    if row["a_latency"]:
        drivers.append({
            "signal": "latency_p95_ms",
            "value": float(row["latency_p95_ms"]),
            "threshold": thr.latency_p95_ms,
            "delta": float(row["latency_p95_ms"] - thr.latency_p95_ms),
        })

    # Errors
    if row["a_errors"]:
        drivers.append({
            "signal": "error_rate_pct",
            "value": float(row["error_rate_pct"]),
            "threshold": thr.error_rate_pct,
            "delta": float(row["error_rate_pct"] - thr.error_rate_pct),
        })

    # Volume drop
    if row["a_volume"]:
        drivers.append({
            "signal": "volume_drop_pct",
            "value": float(row["vol_drop_pct"]),
            "threshold": thr.volume_drop_pct,
            "delta": float(row["vol_drop_pct"] - thr.volume_drop_pct),
        })

    # Saturation
    if row["a_saturation"]:
        drivers.append({
            "signal": "saturation_pct",
            "value": float(row["saturation_pct"]),
            "threshold": thr.saturation_pct,
            "delta": float(row["saturation_pct"] - thr.saturation_pct),
        })

    drivers = sorted(drivers, key=lambda d: abs(d["delta"]), reverse=True)
    return drivers[:3]


def recommendation_from_drivers(drivers: List[Dict]) -> str:
    """
    Narrator helper: recomendación simple según driver dominante.
    """
    if not drivers:
        return "Sin acción: métricas dentro de política."

    main = drivers[0]["signal"]
    if main == "latency_p95_ms":
        return "Revisar saturación/DB/colas. Activar auto-scale o reducir carga. Validar picos recientes."
    if main == "error_rate_pct":
        return "Auditar releases recientes. Revisar dependencias externas. Activar circuit breaker y rollback si aplica."
    if main == "volume_drop_pct":
        return "Validar ingesta/eventos. Revisar gateway/routing. Confirmar si hay caída real de tráfico o upstream."
    if main == "saturation_pct":
        return "Saturación alta: revisar CPU/mem y límites. Ajustar autoscaling y revisar jobs pesados."
    return "Revisar señales principales y ejecutar runbook estándar."


def build_exec_report(incidents: List[Incident], reviewer_notes: List[Dict], policy: Thresholds) -> str:
    """
    Narrator Agent: reporte final en Markdown.
    """
    ts = now_iso()
    lines = []
    lines.append(f"# Ops Cell Lite — Executive Brief")
    lines.append("")
    lines.append(f"Autor: Hugo Baghetti (@tele.objetivo)")
    lines.append(f"Generado: {ts}")
    lines.append("")
    lines.append("## Política (umbrales)")
    lines.append(f"- Latency p95: **>{policy.latency_p95_ms} ms**")
    lines.append(f"- Error rate: **>{policy.error_rate_pct:.2f}%**")
    lines.append(f"- Volume drop: **>{policy.volume_drop_pct:.1f}%** (vs media móvil)")
    lines.append(f"- Saturation: **>{policy.saturation_pct:.1f}%**")
    lines.append("")
    lines.append("## Resumen")
    if not incidents:
        lines.append("- No se detectaron incidentes bajo la política actual.")
    else:
        crit = sum(1 for i in incidents if i.severity in ("High", "Critical"))
        med = sum(1 for i in incidents if i.severity == "Medium")
        lines.append(f"- Incidentes detectados: **{len(incidents)}** (High/Critical: **{crit}**, Medium: **{med}**)")
    lines.append("")

    lines.append("## Incidentes (top)")
    if incidents:
        for inc in incidents[:8]:
            lines.append(f"### {inc.incident_id} — {inc.severity} — {inc.ts}")
            lines.append(f"**Recomendación:** {inc.recommendation}")
            if inc.drivers:
                lines.append("**Drivers:**")
                for d in inc.drivers:
                    lines.append(f"- {d['signal']}: {d['value']:.2f} (thr {d['threshold']}) Δ={d['delta']:.2f}")
            if inc.reviewer and inc.reviewer.get("decision"):
                lines.append(f"**HITL:** {inc.reviewer['decision']} — {inc.reviewer.get('note','')}")
            lines.append("")
    else:
        lines.append("- (vacío)")
        lines.append("")

    lines.append("## Feedback (HITL)")
    if reviewer_notes:
        for r in reviewer_notes[-10:]:
            lines.append(f"- {r['ts']} · {r['incident_id']} · {r['decision']} · {r.get('note','')}")
    else:
        lines.append("- Sin feedback capturado.")
    lines.append("")

    lines.append("## Próximos pasos recomendados")
    lines.append("- Formalizar runbook por tipo de driver.")
    lines.append("- Agregar integración real (webhook/Slack/email) y auditoría de cambios.")
    lines.append("- Convertir reglas en tests + CI para evitar regresiones.")
    lines.append("")

    return "\n".join(lines)


def save_json(obj: dict, filename: str) -> str:
    p = OUT_DIR / filename
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    return str(p)


def save_md(text: str, filename: str) -> str:
    p = OUT_DIR / filename
    p.write_text(text, encoding="utf-8")
    return str(p)


# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.header("⚙️ Control Panel")
seed = st.sidebar.number_input("Seed", 1, 9999, 11, 1)
hours = st.sidebar.slider("Horizonte (horas)", 6, 168, 72, 6)
baseline = st.sidebar.selectbox("Baseline", ["stable", "noisy", "peak"], index=1)

st.sidebar.subheader("Umbrales (Policy)")
lat_thr = st.sidebar.slider("Latency p95 (ms)", 150, 1200, 420, 10)
err_thr = st.sidebar.slider("Error rate (%)", 0.2, 8.0, 1.6, 0.1)
vol_drop_thr = st.sidebar.slider("Volume drop (%)", 5.0, 70.0, 25.0, 1.0)
sat_thr = st.sidebar.slider("Saturation (%)", 30.0, 95.0, 78.0, 1.0)

policy = Thresholds(
    latency_p95_ms=int(lat_thr),
    error_rate_pct=float(err_thr),
    volume_drop_pct=float(vol_drop_thr),
    saturation_pct=float(sat_thr),
)

st.sidebar.divider()
if st.sidebar.button("📌 Reset (sin romper nada)"):
    st.rerun()


# -----------------------------
# Agent pipeline
# -----------------------------
df = synth_signals(seed=seed, hours=hours, baseline=baseline)
det = detect_anomalies(df, policy)

# incident candidates: puntos con severidad != OK, tomamos los más recientes por severidad
cand = det[det["severity"] != "OK"].copy().sort_values("ts", ascending=False)
cand["rank"] = cand["severity"].map({"Critical": 3, "High": 2, "Medium": 1}).fillna(0)
cand = cand.sort_values(["rank", "ts"], ascending=[False, False]).head(12)

# Session state for HITL
if "review_log" not in st.session_state:
    st.session_state["review_log"] = []  # list of dict
if "approved" not in st.session_state:
    st.session_state["approved"] = set()
if "rejected" not in st.session_state:
    st.session_state["rejected"] = set()


# -----------------------------
# KPIs
# -----------------------------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Samples", len(det))
k2.metric("Incidents", len(cand))
k3.metric("High/Critical", int((cand["rank"] >= 2).sum()))
k4.metric("HITL decisions", len(st.session_state["review_log"]))

st.divider()


# -----------------------------
# Visuals
# -----------------------------
left, right = st.columns([0.62, 0.38])

with left:
    st.subheader("📈 Timeline")
    long = det.melt(
        id_vars=["ts", "severity"],
        value_vars=["latency_p95_ms", "error_rate_pct", "volume_rpm", "saturation_pct"],
        var_name="signal",
        value_name="value",
    )
    fig = px.line(long, x="ts", y="value", color="signal", title="Señales operacionales")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("🧭 Radar (última muestra)")
    last = det.iloc[-1]
    st.write(f"**Último timestamp:** {last['ts']}")
    st.write(f"**Severidad:** `{last['severity']}`")
    st.dataframe(
        pd.DataFrame([{
            "latency_p95_ms": float(last["latency_p95_ms"]),
            "error_rate_pct": float(last["error_rate_pct"]),
            "volume_rpm": float(last["volume_rpm"]),
            "saturation_pct": float(last["saturation_pct"]),
            "vol_drop_pct": float(last["vol_drop_pct"]),
        }]),
        use_container_width=True
    )

st.divider()


# -----------------------------
# Incidents table + HITL
# -----------------------------
st.subheader("🚨 Incidents + Human-in-the-loop (HITL)")

if cand.empty:
    st.success("No hay incidentes bajo la política actual. Si quieres 'stress', baja umbrales o cambia baseline.")
else:
    # construir incidents list (con drivers + rec)
    incidents: List[Incident] = []
    for _, row in cand.iterrows():
        drivers = top_drivers(row, policy)
        rec = recommendation_from_drivers(drivers)
        iid = f"INC-{pd.to_datetime(row['ts']).strftime('%H%M')}-{row['severity']}"
        reviewer = {"decision": "", "note": ""}

        # si ya hay decisión previa, la reflejo
        for r in reversed(st.session_state["review_log"]):
            if r["incident_id"] == iid:
                reviewer = {"decision": r["decision"], "note": r.get("note", "")}
                break

        incidents.append(Incident(
            incident_id=iid,
            ts=str(row["ts"]),
            severity=str(row["severity"]),
            signals={
                "latency_p95_ms": float(row["latency_p95_ms"]),
                "error_rate_pct": float(row["error_rate_pct"]),
                "volume_rpm": float(row["volume_rpm"]),
                "saturation_pct": float(row["saturation_pct"]),
                "vol_drop_pct": float(row["vol_drop_pct"]),
            },
            drivers=drivers,
            recommendation=rec,
            reviewer=reviewer,
        ))

    # tabla simple para navegar
    df_inc = pd.DataFrame([{
        "incident_id": i.incident_id,
        "ts": i.ts,
        "severity": i.severity,
        "main_driver": (i.drivers[0]["signal"] if i.drivers else "none"),
        "recommendation": i.recommendation
    } for i in incidents])

    st.dataframe(df_inc, use_container_width=True)

    st.write("")
    cA, cB = st.columns([0.55, 0.45])

    with cA:
        sel = st.selectbox("Selecciona incidente", df_inc["incident_id"].tolist())
        inc = next(i for i in incidents if i.incident_id == sel)

        st.markdown(f"### {inc.incident_id} — {inc.severity}")
        st.write(f"**Timestamp:** {inc.ts}")
        st.write(f"**Recomendación:** {inc.recommendation}")

        st.markdown("**Drivers (top):**")
        if inc.drivers:
            st.dataframe(pd.DataFrame(inc.drivers), use_container_width=True)
        else:
            st.write("- (sin drivers)")

        st.markdown("**Señales:**")
        st.json(inc.signals)

    with cB:
        st.markdown("### ✅ Reviewer (HITL)")
        decision = st.radio(
            "Decisión",
            ["(sin decisión)", "Approve", "Reject"],
            index=0 if not inc.reviewer.get("decision") else (1 if inc.reviewer["decision"] == "Approve" else 2),
            key=f"dec_{sel}",
        )
        note = st.text_area("Nota (opcional)", value=inc.reviewer.get("note", ""), key=f"note_{sel}")

        if st.button("Guardar feedback", key=f"save_{sel}"):
            if decision == "(sin decisión)":
                st.warning("Elige Approve o Reject para registrar feedback.")
            else:
                entry = {
                    "ts": now_iso(),
                    "incident_id": sel,
                    "decision": decision,
                    "note": note.strip(),
                }
                st.session_state["review_log"].append(entry)
                if decision == "Approve":
                    st.session_state["approved"].add(sel)
                    st.session_state["rejected"].discard(sel)
                else:
                    st.session_state["rejected"].add(sel)
                    st.session_state["approved"].discard(sel)
                st.success("Feedback guardado.")
                st.rerun()

st.divider()


# -----------------------------
# Narrator: executive report
# -----------------------------
st.subheader("📝 Narrator Agent — Executive Report")

# reconstruir incidents list para el reporte (incluye decisiones)
final_incidents: List[Incident] = []
if not cand.empty:
    for _, row in cand.iterrows():
        iid = f"INC-{pd.to_datetime(row['ts']).strftime('%H%M')}-{row['severity']}"
        drivers = top_drivers(row, policy)
        rec = recommendation_from_drivers(drivers)

        reviewer = {"decision": "", "note": ""}
        for r in reversed(st.session_state["review_log"]):
            if r["incident_id"] == iid:
                reviewer = {"decision": r["decision"], "note": r.get("note", "")}
                break

        final_incidents.append(Incident(
            incident_id=iid,
            ts=str(row["ts"]),
            severity=str(row["severity"]),
            signals={
                "latency_p95_ms": float(row["latency_p95_ms"]),
                "error_rate_pct": float(row["error_rate_pct"]),
                "volume_rpm": float(row["volume_rpm"]),
                "saturation_pct": float(row["saturation_pct"]),
                "vol_drop_pct": float(row["vol_drop_pct"]),
            },
            drivers=drivers,
            recommendation=rec,
            reviewer=reviewer,
        ))

md = build_exec_report(final_incidents, st.session_state["review_log"], policy)
st.markdown(md)

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("💾 Guardar reporte (MD)"):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = save_md(md, f"ops_cell_report_{ts}.md")
        st.success(f"Reporte guardado: {path}")

with col2:
    if st.button("💾 Guardar snapshot (JSON)"):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        payload = {
            "generated_at": now_iso(),
            "policy": policy.__dict__,
            "signals_tail": det.tail(120).to_dict(orient="records"),
            "incidents": [i.__dict__ for i in final_incidents],
            "review_log": st.session_state["review_log"],
        }
        path = save_json(payload, f"ops_cell_snapshot_{ts}.json")
        st.success(f"Snapshot guardado: {path}")

with col3:
    st.caption(f"Local run · {now_iso()}")

# -------------------------------------------------
# Control Room Snapshot (SAFE / OPTIONAL)
# -------------------------------------------------
import json
from datetime import datetime
from pathlib import Path

def write_control_room_snapshot(project, status="healthy", kpis=None):
    try:
        out = Path("outputs")
        out.mkdir(exist_ok=True)

        snapshot = {
            "project": project,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "kpis": kpis or {}
        }

        with open(out / "control_room_snapshot.json", "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)

    except Exception as e:
        # Nunca debe romper la app
        print("Snapshot error:", e)


# Ejecutar snapshot mínimo (no depende de nada)
write_control_room_snapshot(
    project="anomaly-radar-control",
    status="running"
)
