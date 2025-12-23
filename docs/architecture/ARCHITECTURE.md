
# Orion Control Room — Architecture

## 1. Visión General

La arquitectura está basada en **micro-aplicaciones desacopladas** que se comunican mediante
**artefactos persistentes (JSON snapshots)**, no mediante llamadas directas.

![Architecture Flow](images/05_ops_pipeline_flow.png)

---

## 2. Flujo Nivel 1 (Alto Nivel)

1. App ejecuta lógica (ML / reglas / simulación)
2. Genera snapshot JSON
3. Guarda en outputs/
4. Orion Control Room detecta
5. Normaliza
6. Consolida
7. Presenta y exporta

---

## 3. Flujo Nivel 2 (Detalle)

### 3.1 Apps Productoras
- anomaly-radar-control
- decision-intelligence-live
- executive-report-factory
- ops-cell-lite

Cada una:
- Ejecuta lógica
- Produce snapshot
- No conoce a las demás

### 3.2 Contrato Snapshot (simplificado)

```json
{
  "project": "anomaly-radar-control",
  "status": "ok",
  "timestamp": "2025-12-23T12:55:09Z",
  "kpis": {...},
  "payload": {...}
}
```

---

## 4. Mini-agentes y AI

- Detector de anomalías
- Priorizador contrafactual
- Generador de recomendaciones
- Simulador de políticas

Todos:
- Determinísticos
- Explicables
- Auditables

---

## 5. Human-in-the-loop (HITL)

Ops Cell Lite incorpora:
- Decisión humana
- Feedback
- Persistencia

Esto cierra el ciclo ML → humano → sistema.

---

## 6. Escalabilidad

La arquitectura permite:
- Pasar de local a cloud
- Agregar nuevas apps sin tocar el core
- Versionar políticas

---

## 7. Comparación con enfoques tradicionales

| Tradicional | Orion |
|------------|------|
| Dashboards acoplados | Snapshots desacoplados |
| Difícil auditar | Auditoría nativa |
| Caja negra | Explainable |
| Frágil | Reproducible |

---

## 8. Conclusión

Esta arquitectura convierte aplicaciones analíticas en **microservicios cognitivos**,
coordinados por contratos simples y observables.
