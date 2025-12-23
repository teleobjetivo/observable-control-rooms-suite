# Decision Intelligence Live 🧠

Autor: **Hugo Baghetti (@tele.objetivo)**

Este proyecto es un **simulador interactivo de decisiones**. Sirve para probar políticas, umbrales y escenarios (what‑if) con feedback inmediato.

---

## 🎯 Qué hace

- Define una **política** (reglas / pesos / thresholds).
- Ejecuta un **motor de scoring** sobre datos (demo o reales).
- Muestra impacto: trade‑offs, costos, riesgo y beneficios.
- Permite comparar **escenarios** y guardar snapshots reproducibles.

---

## 🧩 Ideal para

- Gestión TI / Operaciones: reglas de priorización.
- Producto: decisiones basadas en señales (no opiniones).
- Analítica: “si cambio X, ¿qué pasa con Y?”

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
decision-intelligence-live/
├─ app.py
├─ README.md
├─ data/
├─ notebooks/
├─ src/
└─ outputs/
```

---

## 🧠 Cómo lo uso yo

1. Defino la pregunta: “¿qué quiero optimizar?”
2. Ajusto pesos/umbrales.
3. Miro el ranking + métricas de resultado.
4. Comparo 2‑3 escenarios.
5. Exporto la configuración + resultados.

---

## ✅ Roadmap corto

- Importar políticas desde JSON.
- Guardar “policy versions” con etiqueta.
- Métrica de sensibilidad (tornado chart).
