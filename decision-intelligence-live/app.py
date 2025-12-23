"""
Decision Intelligence Live 🧠📊
Autor: Hugo Baghetti (@tele.objetivo)

Yo construí este demo para mostrar (en vivo) cómo paso de datos a decisiones:
- What-if con sliders (umbral / costo / riesgo / capacidad)
- Priorización bajo presupuesto (knapsack simple)
- Counterfactual: “qué mover y cuánto” para cumplir una política

Este proyecto NO es astronomía: es estrategia operacional con ingeniería simple y clara.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


# -----------------------------
# Page
# -----------------------------
st.set_page_config(page_title="Decision Intelligence Live", layout="wide")
st.title("🧠 Decision Intelligence Live")
st.caption("What-if · priorización con presupuesto · counterfactual explicable (sin humo)")


# -----------------------------
# Data model
# -----------------------------
@dataclass
class Policy:
    budget: int
    max_risk: float         # 0..1
    min_roi: float          # ROI mínimo aceptado
    max_actions: int
    risk_penalty: float     # penalización por riesgo en scoring


# -----------------------------
# Helpers
# -----------------------------
def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


@st.cache_data
def generate_actions(seed: int = 7, n: int = 18) -> pd.DataFrame:
    """
    Dataset sintético realista: acciones de mejora/mitigación con costo,
    beneficio esperado y riesgo.
    """
    rng = np.random.default_rng(seed)

    categories = [
        "Reliability", "Cost", "Growth", "Security", "Ops", "Data Quality"
    ]

    rows = []
    for i in range(1, n + 1):
        cat = categories[rng.integers(0, len(categories))]
        cost = int(rng.integers(15, 120)) * 1000  # CLP miles (solo para demo)
        benefit = float(rng.normal(1.6, 0.7))     # beneficio relativo
        benefit = clamp(benefit, 0.2, 4.0)

        # riesgo 0..1: acciones más baratas tienden a menos riesgo, no siempre
        base_risk = rng.normal(0.35, 0.18)
        risk = clamp(base_risk + (0.0000015 * (cost - 60000)), 0.05, 0.95)

        effort_days = int(clamp(rng.normal(6, 4), 1, 20))
        confidence = clamp(rng.normal(0.78, 0.12), 0.35, 0.98)

        rows.append({
            "id": f"A{i:02d}",
            "action": f"Action {i:02d} – {cat}",
            "category": cat,
            "cost_clp": cost,
            "benefit_score": benefit,
            "risk": risk,
            "effort_days": effort_days,
            "confidence": confidence
        })

    df = pd.DataFrame(rows)

    # ROI proxy (beneficio / costo)
    df["roi"] = df["benefit_score"] / (df["cost_clp"] / 100_000)  # normalizado
    return df


def score_actions(df: pd.DataFrame, policy: Policy) -> pd.DataFrame:
    """
    Scoring simple y explicable:
    score = (benefit * confidence) - (risk_penalty * risk) - (effort factor)
    """
    out = df.copy()

    effort_factor = (out["effort_days"] / 20.0)  # 0..1 aprox
    out["score"] = (out["benefit_score"] * out["confidence"]) - (policy.risk_penalty * out["risk"]) - (0.25 * effort_factor)

    # Aplicar policy filters
    out["eligible"] = (
        (out["risk"] <= policy.max_risk)
        & (out["roi"] >= policy.min_roi)
    )

    return out.sort_values(["eligible", "score"], ascending=[False, False])


def knapsack_select(df: pd.DataFrame, budget: int, max_items: int) -> Tuple[pd.DataFrame, Dict]:
    """
    Knapsack 0/1 con límite de items.
    Para mantenerlo rápido y robusto: DP por costo discretizado (miles).
    """
    candidates = df[df["eligible"]].copy()
    if candidates.empty:
        return candidates, {"method": "knapsack", "note": "no eligible actions"}

    # discretizamos a miles
    unit = 1000
    costs = (candidates["cost_clp"] // unit).astype(int).to_list()
    values = (candidates["score"] * 1000).astype(int).to_list()  # escalar a int
    ids = candidates["id"].to_list()

    B = budget // unit
    n = len(costs)

    # dp[k][b] = best value using <=k items within budget b
    # Usamos dict sparse para ahorrar memoria
    dp = [dict() for _ in range(max_items + 1)]
    parent = [dict() for _ in range(max_items + 1)]
    dp[0][0] = 0

    for idx in range(n):
        c = costs[idx]
        v = values[idx]
        for k in range(max_items - 1, -1, -1):
            for b, best in list(dp[k].items()):
                nb = b + c
                if nb > B:
                    continue
                nv = best + v
                if nb not in dp[k + 1] or nv > dp[k + 1][nb]:
                    dp[k + 1][nb] = nv
                    parent[k + 1][nb] = (k, b, idx)

    # encontrar mejor solución
    best_k, best_b, best_v = 0, 0, -1
    for k in range(1, max_items + 1):
        for b, v in dp[k].items():
            if v > best_v:
                best_k, best_b, best_v = k, b, v

    if best_v < 0:
        return candidates.iloc[0:0], {"method": "knapsack", "note": "no solution"}

    chosen_idx = []
    k, b = best_k, best_b
    while k > 0:
        pk, pb, idx = parent[k][b]
        chosen_idx.append(idx)
        k, b = pk, pb

    chosen_idx = list(reversed(chosen_idx))
    chosen_ids = [ids[i] for i in chosen_idx]
    selected = candidates[candidates["id"].isin(chosen_ids)].copy()

    info = {
        "method": "knapsack",
        "budget_clp": budget,
        "max_items": max_items,
        "selected_count": int(len(selected)),
        "selected_cost_clp": int(selected["cost_clp"].sum()),
        "selected_score_sum": float(selected["score"].sum()),
    }
    return selected.sort_values("score", ascending=False), info


def counterfactual(policy: Policy, df: pd.DataFrame) -> Dict:
    """
    Counterfactual simple:
    - Si no hay suficientes elegibles, sugerir:
      1) subir max_risk
      2) bajar min_roi
    hasta que aparezcan al menos max_actions candidatas
    """
    base = score_actions(df, policy)
    base_eligible = base[base["eligible"]]
    target = max(3, min(policy.max_actions, 8))

    if len(base_eligible) >= target:
        return {"status": "ok", "message": "La política actual ya habilita suficientes acciones.", "suggestions": []}

    suggestions = []
    # propuesta 1: relajar riesgo
    tmp = Policy(**policy.__dict__)
    for step in [0.05, 0.10, 0.15, 0.20]:
        tmp.max_risk = clamp(policy.max_risk + step, 0.05, 0.95)
        elig = score_actions(df, tmp)
        if len(elig[elig["eligible"]]) >= target:
            suggestions.append({
                "change": "max_risk",
                "from": policy.max_risk,
                "to": tmp.max_risk,
                "why": f"Con max_risk={tmp.max_risk:.2f} aparecen suficientes acciones elegibles."
            })
            break

    # propuesta 2: relajar ROI mínimo
    tmp = Policy(**policy.__dict__)
    for step in [0.10, 0.20, 0.30, 0.40]:
        tmp.min_roi = max(0.0, policy.min_roi - step)
        elig = score_actions(df, tmp)
        if len(elig[elig["eligible"]]) >= target:
            suggestions.append({
                "change": "min_roi",
                "from": policy.min_roi,
                "to": tmp.min_roi,
                "why": f"Con min_roi={tmp.min_roi:.2f} habilito más opciones sin tocar el riesgo."
            })
            break

    if not suggestions:
        return {
            "status": "warn",
            "message": "Con estos límites, el set es muy restrictivo. Sugiero relajar max_risk y/o min_roi más agresivamente.",
            "suggestions": []
        }

    return {"status": "fix", "message": "Para cumplir la política, recomiendo este ajuste mínimo:", "suggestions": suggestions}


def write_snapshot(payload: dict, out_dir: str = "outputs") -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    p = Path(out_dir) / f"decision_snapshot_{ts}.json"
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(p)


# -----------------------------
# Sidebar controls (Policy)
# -----------------------------
st.sidebar.header("⚙️ Policy Simulator (What-if)")
budget = st.sidebar.slider("Presupuesto (CLP)", 100_000, 2_000_000, 650_000, step=50_000)
max_actions = st.sidebar.slider("Máx. acciones", 1, 10, 5)
max_risk = st.sidebar.slider("Riesgo máximo (0..1)", 0.10, 0.95, 0.55, step=0.05)
min_roi = st.sidebar.slider("ROI mínimo (proxy)", 0.0, 3.0, 0.8, step=0.1)
risk_penalty = st.sidebar.slider("Penalización por riesgo", 0.0, 2.0, 0.9, step=0.1)

seed = st.sidebar.number_input("Seed dataset", min_value=1, max_value=9999, value=7, step=1)

policy = Policy(
    budget=int(budget),
    max_risk=float(max_risk),
    min_roi=float(min_roi),
    max_actions=int(max_actions),
    risk_penalty=float(risk_penalty),
)

df = generate_actions(seed=seed, n=18)
scored = score_actions(df, policy)

# -----------------------------
# Top KPIs
# -----------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Acciones", len(scored))
c2.metric("Elegibles", int(scored["eligible"].sum()))
c3.metric("Presupuesto", f"${policy.budget:,}".replace(",", "."))
c4.metric("Política", f"risk≤{policy.max_risk:.2f} · roi≥{policy.min_roi:.1f}")

st.divider()

# -----------------------------
# Visual: scatter (impact vs risk)
# -----------------------------
left, right = st.columns([0.60, 0.40])

with left:
    st.subheader("🧭 Mapa de decisiones (Benefit vs Risk)")
    fig = px.scatter(
        scored,
        x="risk",
        y="benefit_score",
        size="cost_clp",
        color="eligible",
        hover_data=["id", "category", "cost_clp", "roi", "confidence", "effort_days", "score"],
        title="Acciones: riesgo vs beneficio (tamaño = costo)"
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("📌 Top acciones (por score)")
    st.dataframe(
        scored.head(10)[["id", "category", "cost_clp", "benefit_score", "risk", "roi", "confidence", "effort_days", "score", "eligible"]],
        use_container_width=True
    )

st.divider()

# -----------------------------
# Optimizer (knapsack)
# -----------------------------
st.subheader("🧮 Optimization Planner (prioriza con presupuesto)")
selected, info = knapsack_select(scored, budget=policy.budget, max_items=policy.max_actions)

colA, colB, colC = st.columns(3)
colA.metric("Seleccionadas", info.get("selected_count", 0))
colB.metric("Costo total", f"${int(info.get('selected_cost_clp', 0)):,}".replace(",", "."))
colC.metric("Score total", f"{info.get('selected_score_sum', 0.0):.2f}")

if selected.empty:
    st.warning("No hay acciones elegibles con la política actual. Ajusta risk/roi o presupuesto.")
else:
    st.dataframe(
        selected[["id", "action", "category", "cost_clp", "benefit_score", "risk", "roi", "confidence", "effort_days", "score"]],
        use_container_width=True
    )

st.divider()

# -----------------------------
# Counterfactual
# -----------------------------
st.subheader("🧠 Counterfactual Explainer (qué mover para cumplir)")
cf = counterfactual(policy, df)

if cf["status"] == "ok":
    st.success(cf["message"])
elif cf["status"] == "fix":
    st.info(cf["message"])
    for s in cf["suggestions"]:
        st.write(f"- Cambiar **{s['change']}** de **{s['from']}** a **{s['to']}** → {s['why']}")
else:
    st.warning(cf["message"])

st.divider()

# -----------------------------
# Snapshot
# -----------------------------
st.subheader("💾 Snapshot reproducible")
st.caption("Guardo política + dataset + selección para compartir o auditar después.")

if st.button("Guardar snapshot JSON"):
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "policy": policy.__dict__,
        "dataset": df.to_dict(orient="records"),
        "scored_top10": scored.head(10).to_dict(orient="records"),
        "selected": selected.to_dict(orient="records"),
        "optimizer": info,
    }
    path = write_snapshot(payload)
    st.success(f"Snapshot guardado en: {path}")

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
