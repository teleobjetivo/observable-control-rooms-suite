# Executive Report Factory 📄

Autor: **Hugo Baghetti (@tele.objetivo)**

Este proyecto es una **fábrica automática de reportes ejecutivos**: toma datos operacionales (o un dataset demo) y genera un **resumen Markdown** claro, accionable y exportable.

---

## 🎯 Qué hace

- Carga datos (demo o reales).
- Aplica una **policy** (criterios de prioridad / umbrales).
- Genera un reporte Markdown con:
  - resumen ejecutivo,
  - hallazgos,
  - top ventanas / top casos,
  - recomendaciones,
  - supuestos y riesgos.
- Permite **vista previa** y **export**.

> La idea es simple: que el output sea “mandable” a un gerente sin pedir perdón.

---

## ▶️ Run local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py --server.port 8503
```

---

## 📦 Dependencias

Si usas tablas markdown, `pandas.to_markdown()` necesita `tabulate`.  
Lo dejo como dependencia en requirements.

---

## 📁 Estructura

```text
executive-report-factory/
├─ app.py
├─ README.md
├─ data/
├─ notebooks/
├─ src/
└─ outputs/
```

---

## ✅ Roadmap corto

- Templates: “Operations”, “Product”, “Risk”.
- Export a PDF (wkhtmltopdf o reportlab).
- Modo “weekly digest” (últimos 7 días).
