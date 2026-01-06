# Anomaly Radar Control 🚨

Autor: **Hugo Baghetti (@tele.objetivo)**

Este proyecto es un **radar liviano de anomalías**: toma una señal (métricas operacionales o indicadores) y la transforma en **priorización + explicación interpretada**.

---

## 🎯 Qué hace

- Simula o consume una tabla de señales (series / eventos).
- Calcula un **score de anomalía** (z‑score / percentil / heurística).
- Clasifica por severidad (**Info / Warning / Action required**).
- Muestra un **radar / ranking** y sugiere acciones.

---

## 🧩 Ideal para

- Soporte/Operaciones: spikes, caídas, outliers.
- Producto: métricas que “se salieron del carril”.
- Data Quality: reglas simples que alertan antes del desastre.

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
anomaly-radar-control/
├─ app.py
├─ README.md
├─ data/
├─ notebooks/
├─ src/
└─ outputs/
```

---

## 🔎 Cómo se usa

1. Abrir la app.
2. Elijir el dataset (demo o real).
3. Ajustar umbrales (sensibilidad).
4. Revisar el ranking y el “por qué”.
5. Exportar snapshot a `outputs/`.

---

## ✅ Roadmap 

- Ingesta desde CSV real + validaciones.
- “Explain” por anomalía (top drivers).
- Modo “trend” (comparar ventanas de tiempo).


