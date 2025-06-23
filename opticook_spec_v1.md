
# Opticook – Backend & API Specification  
**On‑Prem MVP • July 2025**

---

## 1 · Overview

Opticook coordinates a group of **chefs** as they execute a recipe.  
The backend decides *who* should do *what* and *when*, aiming for the
shortest possible makespan.  
This spec targets the **initial on‑prem deployment**: one process, one
cooking session, no public internet exposure.

Repository branch:  
<https://github.com/drorspei/opticook/tree/opticookopenai3/opticook3>

---

## 2 · Domain model

```
Recipe
 ├─ CookingInstruction  (CI)   – high‑level step, may depend on other CIs
 │    └─ AtomicInstruction (AI) – indivisible action with duration + attention
 └─ dependencies
```

### 2.1 Data classes  `backend/data_models.py`

```python
@dataclass(frozen=True)
class Chef:
    name: str
    addr: Optional[str] = None
    heartbeat: Optional[int] = None
    disconnected: bool = False

@dataclass(frozen=True)
class AtomicInstruction:
    attention: bool          # True = needs full attention
    duration: int            # integer **quanta** (30‑s units)
    description: str

@dataclass(frozen=True)
class CookingInstruction:
    index: int
    aiList: List[AtomicInstruction]
    dependencies: List[int]

@dataclass(frozen=True)
class ActiveTask:
    instruction_index: int
    ai_index: int
    start_time: Optional[int] = None   # epoch seconds

@dataclass(frozen=True)
class DoneTask:
    instruction_index: int
    chef_name: str
    time_data: List[Tuple[int, int]]   # (start, end) per AI

@dataclass(frozen=True)
class Session:
    recipe: List[CookingInstruction]
    chefs_data: Dict[str, Chef]
    cooking_map: Dict[str, Dict[int, ActiveTask]]
    done_tasks: Dict[int, DoneTask]
```

### 2.2 Time units

```python
COOKING_TIME_UNIT = 30  # seconds per quantum

def time_in_units(seconds: float) -> int:
    """Return ceil(seconds / 30)."""
```

* **Loader rule** – When building `Session.recipe`, call
  `time_in_units(raw_seconds)` and **store the integer quanta**.  
* All scheduling and validation logic operates on **quanta**.  
  UI may convert to seconds for display.

---

## 3 · Scheduling & constraints

* **Objective** Minimise total cooking time (makespan).  
* **Attention** Each chef may run *≤ 1* high‑attention AI at once; any
  number of low‑attention timers in parallel.  
* **Precedence** A CI may start only after every CI in its `dependencies`
  is completely finished.

A placeholder heuristic scheduler is acceptable for MVP; plumb the API so
it can be swapped with a SAT‑based search in a later sprint.

---

## 4 · Session lifecycle

| Event | Rule |
|-------|------|
| Heartbeat | Client polls every **30 s** |
| Disconnect | Flag chef after **6** missed beats (≈ 3 min) |
| On disconnect | Release chef’s ActiveTasks and re‑schedule |
| Device swap | Allowed – same `chef_name` |
| Join/leave mid‑session | Not supported (future work) |

---

## 5 · API surface

Single namespace prefix: `/api/v1/session/current/…`

| Route | Method | Body / Query | Returns |
|-------|--------|--------------|---------|
| `/start` | POST | `{recipe_id, chefs:[str]}` | `{session_id:"current"}` |
| `/heartbeat` | GET | `?chef=<name>` | Full `Session` JSON |
| `/done` | POST | `{chef, instruction_index}` | Full `Session` JSON |
| `/state` | GET | — | Full `Session` JSON |
| `/reset` | POST | — | `{}` (dev only) |

**Error codes**

* `400` – malformed body / timer not elapsed  
* `404` – unknown path (only `"current"` session exists)  
* `409` – session already running (`/start`)  
* `410` – heartbeat from a disconnected chef

---

## 6 · Deployment assumptions

* **Environment** Private network, on‑prem VM / container.  
* **Workers** Exactly one (`uvicorn --workers 1`).  
* **Persistence** In‑memory singleton.  Restart wipes state.  
* **HTTPS** Optional internally; add TLS proxy only if exposing outside.

---

## 7 · Security model

No authentication.  Anyone on the same LAN who knows the URL can drive the
API.  Harden later with a session secret or JWT when needed.

---

## 8 · Future backlog

* Undo / mistake button  
* Mid‑session join / leave  
* Work‑balance fairness in scheduler  
* Persistent store (pickle, Redis)  
* Admin dashboard  
* Rate‑limit & auth  
* Push updates (WebSocket / SSE)

---

*End of specification – On‑Prem MVP.*
