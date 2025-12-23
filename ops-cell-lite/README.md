# Ops Cell Lite 🧩

Autor: **Hugo Baghetti (@tele.objetivo)**

Este proyecto es una **célula operativa mínima**: un tablero muy simple que ayuda a ordenar el día (estado, checklist, prioridades, próximos pasos) y dejar evidencia en snapshots.

---

## 🎯 Qué hace

- Define estado operativo (Healthy / Warning / Action required).
- Permite checklist rápido (runbook mínimo).
- Registra decisiones y “next actions”.
- Exporta snapshots (para trazabilidad).

---

## 🧩 Ideal para

- Turnos / guardias (on‑call lite).
- Equipos chicos que necesitan orden sin burocracia.
- “War room” liviano.

---

## ▶️ Run local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

---

## 📁 Estructura

```text
ops-cell-lite/
├─ app.py
├─ README.md
├─ data/
├─ notebooks/
├─ src/
└─ outputs/
```

---

## ✅ Roadmap corto

- Export de checklist a Markdown.
- Modo “handoff” (cambio de turno).
- Plantillas por tipo de incidente.
