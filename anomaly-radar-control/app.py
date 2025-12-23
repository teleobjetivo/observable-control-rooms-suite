"""
Anomaly Radar Control 🚨
Autor: Hugo Baghetti (@tele.objetivo)

Construí este demo para mostrar cómo detectar anomalías operacionales
de forma clara, visual y explicable, sin humo de IA.

Objetivo:
- Simular métricas reales de negocio / operaciones
- Detectar anomalías automáticamente
- Explicar por qué importan
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Anomaly Radar Control",
    layout="wide"
)

st.title("🚨 Anomaly Radar Control")
st.caption("Demo observable · métricas operacionales · detección explicable")

# -----------------------------
# Generación de datos sintéticos realistas
# -----------------------------
@st.cache_data
def generate_metrics(n=300):
    ts = pd.date_range(
        end=datetime.now(),
        periods=n,
        freq="H"
    )

    latency = np.random.normal(120, 15, n)
    errors = np.random.poisson(2, n)
    volume = np.random.normal(1000, 120, n)

    # Inyectar anomalías
    for i in np.random.choice(range(50, n-10), 4, replace=False):
        latency[i:i+3] += np.random.randint(80, 140)
        errors[i:i+3] += np.random.randint(6, 12)
        volume[i:i+3] -= np.random.randint(300, 500)

    return pd.DataFrame({
        "timestamp": ts,
        "latency_ms": latency,
        "errors": errors,
        "volume": volume
    })

df = generate_metrics()

# -----------------------------
# Controles
# -----------------------------
st.sidebar.header("⚙️ Umbrales")
latency_th = st.sidebar.slider("Latencia crítica (ms)", 150, 400, 220)
errors_th = st.sidebar.slider("Errores críticos (count)", 5, 30, 10)
volume_drop = st.sidebar.slider("Caída de volumen (%)", 10, 70, 35)

# -----------------------------
# Detección simple y explicable
# -----------------------------
df["latency_alert"] = df["latency_ms"] > latency_th
df["errors_alert"] = df["errors"] > errors_th
df["volume_alert"] = df["volume"] < (
    df["volume"].rolling(24).mean() * (1 - volume_drop / 100)
)

df["anomaly"] = (
    df["latency_alert"]
    | df["errors_alert"]
    | df["volume_alert"]
)

# -----------------------------
# KPIs
# -----------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total puntos", len(df))
col2.metric("Anomalías", int(df["anomaly"].sum()))
col3.metric("Latencia máx", f"{df['latency_ms'].max():.0f} ms")
col4.metric("Errores máx", int(df["errors"].max()))

# -----------------------------
# Visualización
# -----------------------------
st.subheader("📈 Métricas temporales")
st.line_chart(
    df.set_index("timestamp")[["latency_ms", "errors", "volume"]]
)

# -----------------------------
# Anomalías detectadas
# -----------------------------
st.subheader("🧠 Anomalías detectadas")

anomalies = df[df["anomaly"]].copy()

if anomalies.empty:
    st.success("No se detectaron anomalías con los umbrales actuales.")
else:
    st.dataframe(
        anomalies[[
            "timestamp",
            "latency_ms",
            "errors",
            "volume",
            "latency_alert",
            "errors_alert",
            "volume_alert"
        ]],
        use_container_width=True
    )

    st.markdown("### 🔎 Interpretación")
    st.write(
        f"Detecté **{len(anomalies)} eventos anómalos** donde una o más métricas "
        "superaron umbrales operacionales. Estos puntos merecen revisión inmediata "
        "porque impactan experiencia, estabilidad o costos."
    )

# -----------------------------
# Snapshot
# -----------------------------
if st.button("💾 Guardar snapshot"):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"outputs/anomaly_snapshot_{ts}.json"
    anomalies.to_json(path, orient="records", date_format="iso")
    st.success(f"Snapshot guardado en {path}")

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
