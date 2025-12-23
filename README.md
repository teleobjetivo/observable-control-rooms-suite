# Observable Control Rooms Suite 🛰️

Soy **Hugo Baghetti (@tele.objetivo)**. Construí esta suite como un **portafolio técnico ejecutable**: proyectos completos, versionados y documentados (no “demos sueltas”), con **apps Streamlit** que convierten datos y señales operacionales en **decisiones accionables**.

> **Objetivo:** mostrar criterio de ingeniería (diseño, observabilidad, narrativa ejecutiva) aplicado a productos pequeños pero reales.

---

## 🔥 Qué incluye

Esta suite contiene **5 proyectos autónomos** (cada uno con su `README.md`, `app.py`, estructura y outputs):

- **Orion Control Room** — decisiones de “ventanas recomendadas” a partir de señales climáticas (Open‑Meteo, sin API key).
- **Decision Intelligence Live** — simulador interactivo de decisiones y políticas (what‑if).
- **Executive Report Factory** — fábrica de reportes ejecutivos (Markdown) con vista previa y export.
- **Anomaly Radar Control** — tablero liviano de anomalías (radar + priorización + explicación).
- **Ops Cell Lite** — célula operativa mínima (estado, checklist, recomendaciones y snapshots).

---

## 🧱 Estructura general

```text
04_observable_control_rooms/
├─ anomaly-radar-control/
├─ decision-intelligence-live/
├─ executive-report-factory/
├─ ops-cell-lite/
├─ orion-control-room/
└─ README.md
```

Cada carpeta es un **proyecto independiente**.

---

## ▶️ Ejecución local (macOS / Linux)

Recomendación: un virtualenv por suite (rápido y limpio).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Luego, para correr un proyecto:

```bash
cd executive-report-factory
streamlit run app.py --server.port 8503
```

> Cambia la carpeta y el puerto según el proyecto.

---

## 🌐 Deploy público (Streamlit Community Cloud)

La forma más simple:
1. Subo este repo a GitHub (público).
2. En Streamlit Cloud elijo el repo y apunto a `./<proyecto>/app.py`.
3. Defino el **Python version** y dependencias (ideal: `requirements.txt` por proyecto o uno común + extras).

---

## ✅ Convenciones / Calidad

- **Narrativa ejecutiva:** cada app explica “qué significa” y “qué decido” con la salida.
- **Outputs reproducibles:** todo lo exportable queda en `outputs/`.
- **Diseño simple y claro:** UI con controles (umbrales/policies) y resultados inmediatos.
- **Criterio de ingeniería:** decisiones explícitas, trade‑offs y supuestos visibles.

---

## 📌 Licencia y Autoría

Autor: **Hugo Baghetti (@tele.objetivo)**  
Uso: portafolio público + demos ejecutables.  
Si reutilizas partes, agradezco atribución.

---

## Próximos pasos (cuando quieras)

- Badge de “Live Demo” por proyecto (cuando estén deployados).
- README en inglés (mirror).
- Tests mínimos (smoke) + lint.
- Makefile / scripts: `run_all.sh`, `freeze_requirements.sh`.
