"""
Executive Report Factory 📄
Autor: Hugo Baghetti (@tele.objetivo)

Yo construí esta demo para transformar datos reales en un reporte ejecutivo “tipo consultora”
en menos de 2 minutos, con un flujo simple y observable:

- Obtengo datos reales desde Open-Meteo (sin API key).
- Calculo señales y KPIs (riesgo operativo por clima).
- Genero un reporte ejecutivo en Markdown (listo para pegar en email / Confluence / Jira).
- Exporto artefactos reproducibles a outputs/ (MD + JSON).

Repo (suite): https://github.com/teleobjetivo/observable-control-rooms-suite
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import requests
import streamlit as st

APP_TITLE = "Executive Report Factory"
OUT_DIR = Path("outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_CITY = "Viña del Mar, CL"
DEFAULT_LAT = -33.0246
DEFAULT_LON = -71.5518


@dataclass(frozen=True)
class Policy:
    horizon_hours: int
    max_cloud: int
    max_wind_kmh: int
    max_precip_mmph: float
    min_score: float
    window_min_len: int  # hours


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fetch_open_meteo_hourly(lat: float, lon: float, hours: int) -> pd.DataFrame:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,cloud_cover,precipitation,wind_speed_10m",
        "forecast_days": max(1, math.ceil(hours / 24)),
        "timezone": "auto",
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    payload = r.json()
    hourly = payload.get("hourly", {})
    df = pd.DataFrame(
        {
            "time": hourly.get("time", []),
            "temp_c": hourly.get("temperature_2m", []),
            "cloud_%": hourly.get("cloud_cover", []),
            "precip_mm": hourly.get("precipitation", []),
            "wind_kmh": hourly.get("wind_speed_10m", []),
        }
    )
    if df.empty:
        return df
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").head(hours).reset_index(drop=True)
    return df


def compute_score(df: pd.DataFrame, policy: Policy) -> pd.DataFrame:
    out = df.copy()
    cloud_pen = (out["cloud_%"] / max(1, policy.max_cloud)).clip(lower=0)
    wind_pen = (out["wind_kmh"] / max(1, policy.max_wind_kmh)).clip(lower=0)
    precip_pen = (out["precip_mm"] / max(1e-6, policy.max_precip_mmph)).clip(lower=0)

    w_cloud, w_wind, w_precip = 0.45, 0.35, 0.20
    penalty = (w_cloud * cloud_pen + w_wind * wind_pen + w_precip * precip_pen)

    out["score"] = (100 * (1 / (1 + penalty))).clip(0, 100)
    out["is_good"] = out["score"] >= policy.min_score
    return out


def contiguous_windows(df: pd.DataFrame, min_len: int) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["start", "end", "hours", "avg_score"])

    windows: List[Dict[str, Any]] = []
    start_idx = None

    for i, good in enumerate(df["is_good"].tolist()):
        if good and start_idx is None:
            start_idx = i
        if (not good or i == len(df) - 1) and start_idx is not None:
            end_idx = i if good and i == len(df) - 1 else i - 1
            hours = end_idx - start_idx + 1
            if hours >= min_len:
                wdf = df.iloc[start_idx : end_idx + 1]
                windows.append(
                    {
                        "start": wdf["time"].iloc[0],
                        "end": wdf["time"].iloc[-1],
                        "hours": int(hours),
                        "avg_score": float(wdf["score"].mean()),
                        "min_score": float(wdf["score"].min()),
                        "max_wind": float(wdf["wind_kmh"].max()),
                        "max_cloud": float(wdf["cloud_%"].max()),
                        "max_precip": float(wdf["precip_mm"].max()),
                    }
                )
            start_idx = None

    return pd.DataFrame(windows)


def kpis(df: pd.DataFrame, windows: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {"rows": 0, "good_hours": 0, "best_window_hours": 0, "avg_score": None}

    good_hours = int(df["is_good"].sum())
    avg_score = float(df["score"].mean())
    best_window_hours = int(windows["hours"].max()) if not windows.empty else 0

    return {
        "rows": int(len(df)),
        "good_hours": good_hours,
        "good_hours_pct": float(100 * good_hours / max(1, len(df))),
        "best_window_hours": best_window_hours,
        "avg_score": avg_score,
        "score_p10": float(df["score"].quantile(0.10)),
        "score_p90": float(df["score"].quantile(0.90)),
    }


def build_markdown_report(
    city: str,
    lat: float,
    lon: float,
    policy: Policy,
    df: pd.DataFrame,
    windows: pd.DataFrame,
) -> str:
    ts = now_iso()
    ks = kpis(df, windows)

    recs: List[str] = []
    if windows.empty:
        recs.append("No encontré ventanas que cumplan el umbral actual. Sugerencia: relajar *min_score* o ampliar horizonte.")
    else:
        w = windows.sort_values(["avg_score", "hours"], ascending=False).iloc[0]
        recs.append(
            f"Ventana recomendada: **{w['start']} → {w['end']}** "
            f"({int(w['hours'])}h, avg score {w['avg_score']:.1f})."
        )
        recs.append(
            f"Riesgos dentro de la ventana: nubes<= {w['max_cloud']:.0f}%, "
            f"viento<= {w['max_wind']:.0f} km/h, precip<= {w['max_precip']:.2f} mm/h."
        )
        recs.append("Plan sugerido: bloquear agenda + preparar recursos 30–60 min antes del inicio de la ventana.")

    top_table = ""
    if not windows.empty:
        top = windows.sort_values(["avg_score", "hours"], ascending=False).head(5).copy()
        top["start"] = top["start"].astype(str)
        top["end"] = top["end"].astype(str)
        top_table = top[["start", "end", "hours", "avg_score"]].to_markdown(index=False)

    md = f"""# Executive Report — Climate Operational Window

**Autor:** Hugo Baghetti (@tele.objetivo)  
**Generado (UTC):** {ts}  
**Ubicación:** {city} ({lat:.4f}, {lon:.4f})

---

## 1) Resumen ejecutivo
- Horizonte analizado: **{policy.horizon_hours} horas**
- Horas “buenas” bajo política actual: **{ks.get('good_hours', 0)}h ({ks.get('good_hours_pct', 0):.1f}%)**
- Score promedio: **{ks.get('avg_score', 0):.1f}** (P10 {ks.get('score_p10', 0):.1f} · P90 {ks.get('score_p90', 0):.1f})
- Mejor ventana: **{ks.get('best_window_hours', 0)} horas**

## 2) Política aplicada (what‑if)
- Nubes máx: **{policy.max_cloud}%**
- Viento máx: **{policy.max_wind_kmh} km/h**
- Precipitación máx: **{policy.max_precip_mmph} mm/h**
- Score mínimo: **{policy.min_score}**
- Mínimo horas por ventana: **{policy.window_min_len}h**

## 3) Recomendaciones accionables
{chr(10).join([f"- {r}" for r in recs])}

## 4) Top ventanas (si aplica)
{top_table if top_table else "_Sin ventanas detectadas con esta política._"}

## 5) Notas técnicas (breve)
- Fuente: **Open‑Meteo** (forecast hourly, sin API key).
- Score: penalización ponderada por nubes/viento/precip sobre umbrales, escalada a 0–100.
- Artefactos reproducibles: export MD + JSON en `outputs/`.

---
"""
    return md


def write_artifacts(
    city: str,
    lat: float,
    lon: float,
    policy: Policy,
    df: pd.DataFrame,
    windows: pd.DataFrame,
    md: str,
) -> Tuple[Path, Path]:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    md_path = OUT_DIR / f"executive_report_{ts}.md"
    json_path = OUT_DIR / f"executive_report_{ts}.json"

    md_path.write_text(md, encoding="utf-8")

    payload: Dict[str, Any] = {
        "generated_utc": now_iso(),
        "author": "Hugo Baghetti (@tele.objetivo)",
        "city": city,
        "lat": lat,
        "lon": lon,
        "policy": {
            "horizon_hours": policy.horizon_hours,
            "max_cloud": policy.max_cloud,
            "max_wind_kmh": policy.max_wind_kmh,
            "max_precip_mmph": policy.max_precip_mmph,
            "min_score": policy.min_score,
            "window_min_len": policy.window_min_len,
        },
        "kpis": kpis(df, windows),
        "windows": windows.assign(
            start=windows["start"].astype(str),
            end=windows["end"].astype(str),
        ).to_dict(orient="records") if not windows.empty else [],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return md_path, json_path


# ----------------------------
# UI
# ----------------------------
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title("📄 Executive Report Factory")
st.caption("Yo genero un reporte ejecutivo con datos reales (Open‑Meteo) y política what‑if. Exporto Markdown + JSON reproducibles.")

with st.sidebar:
    st.subheader("⚙️ Control Panel")
    st.caption("Datos reales vía Open‑Meteo · sin API key · gratis")

    city = st.text_input("Ubicación (nombre)", value=DEFAULT_CITY)

    use_vina = st.checkbox("Usar coordenadas predefinidas (Viña del Mar)", value=True)
    if use_vina:
        lat, lon = DEFAULT_LAT, DEFAULT_LON
    else:
        lat = st.number_input("Latitud", value=float(DEFAULT_LAT), format="%.5f")
        lon = st.number_input("Longitud", value=float(DEFAULT_LON), format="%.5f")

    st.divider()
    horizon = st.slider("Horizonte (horas)", min_value=24, max_value=168, value=72, step=12)

    st.markdown("**Política (umbrales)**")
    max_cloud = st.slider("Nubes máx (%)", min_value=0, max_value=100, value=35, step=5)
    max_wind = st.slider("Viento máx (km/h)", min_value=0, max_value=80, value=18, step=2)
    max_precip = st.slider("Precipitación máx (mm/h)", min_value=0.00, max_value=5.00, value=0.20, step=0.05, format="%.2f")
    min_score = st.slider("Score mínimo", min_value=10.0, max_value=95.0, value=60.0, step=5.0)
    window_min_len = st.slider("Mínimo horas por ventana", min_value=1, max_value=12, value=3, step=1)

    st.divider()
    run = st.button("🚀 Generar reporte", use_container_width=True)

policy = Policy(
    horizon_hours=int(horizon),
    max_cloud=int(max_cloud),
    max_wind_kmh=int(max_wind),
    max_precip_mmph=float(max_precip),
    min_score=float(min_score),
    window_min_len=int(window_min_len),
)

left, right = st.columns([0.55, 0.45], gap="large")

with left:
    st.subheader("📡 Datos + KPIs")
    if not run:
        st.info("Ajusta la política y presiona **Generar reporte**.")
        st.stop()

    with st.spinner("Consultando Open‑Meteo…"):
        df = fetch_open_meteo_hourly(lat, lon, policy.horizon_hours)

    if df.empty:
        st.error("No llegaron datos desde Open‑Meteo. Reintenta o cambia coordenadas.")
        st.stop()

    scored = compute_score(df, policy)
    windows = contiguous_windows(scored, policy.window_min_len)

    ks = kpis(scored, windows)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Horas analizadas", ks["rows"])
    c2.metric("Horas buenas", ks["good_hours"], f"{ks['good_hours_pct']:.1f}%")
    c3.metric("Score promedio", f"{ks['avg_score']:.1f}")
    c4.metric("Mejor ventana (h)", ks["best_window_hours"])

    st.write("")
    st.caption("Preview tabla (primeras 24h):")
    st.dataframe(scored.head(24), use_container_width=True, height=260)

    st.write("")
    st.subheader("🪟 Ventanas recomendadas")
    if windows.empty:
        st.warning("Sin ventanas con la política actual. Prueba subir el umbral de nubes/viento/precip o bajar score mínimo.")
    else:
        st.dataframe(
            windows.sort_values(["avg_score", "hours"], ascending=False),
            use_container_width=True,
            height=260,
        )

with right:
    st.subheader("🧾 Preview del reporte (Markdown)")
    md = build_markdown_report(city, lat, lon, policy, scored, windows)
    st.markdown(md)

    st.write("")
    st.subheader("⬇️ Export")
    md_path, json_path = write_artifacts(city, lat, lon, policy, scored, windows, md)

    st.success(f"Reporte generado: outputs/{md_path.name}  ·  outputs/{json_path.name}")

    st.download_button(
        "⬇️ Descargar Markdown",
        data=md.encode("utf-8"),
        file_name=md_path.name,
        mime="text/markdown",
        use_container_width=True,
    )
    st.download_button(
        "⬇️ Descargar JSON",
        data=json_path.read_text(encoding="utf-8").encode("utf-8"),
        file_name=json_path.name,
        mime="application/json",
        use_container_width=True,
    )

st.caption(f"Local run · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

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
