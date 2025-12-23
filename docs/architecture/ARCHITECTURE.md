# ARCHITECTURE — Orion Control Rooms Suite

## 1. Architectural Overview

Orion Control Rooms Suite is a **modular, observable and loosely-coupled system**
designed to orchestrate multiple analytical applications through standardized
JSON snapshots.

Each project operates as an **independent micro-application**, while the
Orion Control Room acts as a **supervisory orchestration layer**.

---

## 2. Core Principles

- Decoupled execution
- Snapshot-based communication
- Human-readable outputs
- Machine-consumable artifacts
- Zero hard runtime dependencies between apps
- Observable by design

---

## 3. High-Level Architecture (Level 1)

```
[ External Data Sources ]
          |
          v
+----------------------+
|  Domain Applications |
|----------------------|
| anomaly-radar-control|
| decision-intelligence|
| executive-report     |
| ops-cell-lite        |
+----------------------+
          |
          |  (JSON Snapshots)
          v
+----------------------------+
|   Orion Control Room       |
|----------------------------|
| Snapshot Discovery         |
| Normalization              |
| Health Evaluation          |
| Visualization              |
+----------------------------+
          |
          v
[ Humans / BI / APIs / AI ]
```

---

## 4. Domain Applications (Level 2)

Each domain app follows the same internal pattern:

```
Input Data
   |
   v
Pre-processing
   |
   v
Scoring / Analysis
   |
   v
Decision Logic
   |
   v
Snapshot Writer (JSON / MD)
```

### Snapshot Contract (Minimum)

```json
{
  "project": "string",
  "timestamp": "ISO-8601",
  "status": "ok | warning | critical",
  "metrics": {},
  "summary": "string"
}
```

---

## 5. Orion Control Room Responsibilities

- Discover latest snapshots per project
- Normalize heterogeneous payloads
- Classify health state
- Surface warnings and actions
- Enable downloads and traceability
- Act as **human-in-the-loop gateway**

---

## 6. AI / ML Extension Points

This architecture is intentionally AI-ready:

- Anomaly detection models
- Policy optimization agents
- Recommendation engines
- Auto-remediation triggers
- LLM-based explanation layers

All AI components plug **after snapshot generation** or **inside domain apps**,
never inside the control room core.

---

## 7. Example Use Cases

### Office Automation
- Process health monitoring
- SLA dashboards
- Auto-generated reports

### Research & Data Science
- Experiment tracking
- Result comparators
- Reproducible analysis pipelines

### Banking / Retail / BI
- Risk evaluation
- Policy simulations
- Executive decision rooms

---

## 8. Why This Architecture Works

- Scales horizontally
- Easy to reason about
- Easy to debug
- Easy to explain
- Easy to extend
- Hard to break

---

## 9. Author

**Hugo Baghetti**  
Orion Control Rooms Suite  
2025
