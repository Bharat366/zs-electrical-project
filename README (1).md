# Earth Fault Loop Impedance (Zs) Chatbot

An electrical-safety web assistant that calculates the **earth fault loop impedance (Zs)**
from earthing measurements and checks it against the breaker disconnection limit.
It works as a **chatbot that only answers electrical questions** — anything off-topic is
politely declined.

---

## What it does

- Takes earthing measurements in plain language, e.g.
  `three pits at 4.2, 5.1, 3.8 ohm, grid 0.9 ohm, Type C 32A`
- Combines the earth pits and grid **in parallel** to get the earthing resistance (Ze)
- Computes **Zs = Ze + (R1 + R2)** and the maximum allowed limit
- Returns an instant **PASS / FAIL** verdict with the margin and a recommendation
- Answers electrical questions (MCBs, earthing, Ohm's law, RCDs, etc.)
- Refuses non-electrical questions: *"I only answer questions about electrical subjects."*

---

## The engineering

```
Zs = Ze + (R1 + R2)
  Ze = parallel combination of all earth pits and the earth grid
       1/Ze = 1/R_pit1 + 1/R_pit2 + ... + 1/R_grid
  R1 = phase conductor resistance
  R2 = earth (protective) conductor resistance

Compliance:  Zs <= (2/3) x (U0 / Ia)
  U0 = line-to-earth voltage (230 V)
  Ia = MCB trip current = multiplier x rating   (Type B x5, C x10, D x20)

Recommended electrode values:  earth pit < 5 ohm,  earth grid < 1 ohm
```

---

## Tech stack

- **Backend:** Python + Flask (calculation engine, natural-language parser,
  electrical topic-guard and Q&A, served through a small REST API)
- **Frontend:** HTML, CSS and JavaScript chat interface (built into `app.py`)
- Runs locally in the browser — no internet required after setup

---

## How to run

```bash
# 1. (one-time) create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. install Flask
pip install flask

# 3. start the app
python3 app.py
```

Then open **http://localhost:5001** in your browser.

> On macOS, port 5000 is used by AirPlay Receiver, so this app runs on **5001**.

### Try it

- `three pits at 4.2, 5.1, 3.8 ohm, grid 0.9 ohm, Type C 32A`  → FAIL (Zs 0.553 ohm vs 0.479 ohm limit)
- `what is an MCB?`  → answered
- `why do we need earthing?`  → answered
- `what is the weather today?`  → politely declined

---

## Project files

| File | Description |
|------|-------------|
| `app.py` | The complete application (backend + web page) |
| `Zs_Chatbot_Presentation.pptx` | Project presentation slides |
| `demo` (video) | Screen-recorded demonstration |

---

*Author: Bharat Reddy · B.Tech AIML · Woxsen University, School of Technology*

*Note: the parallel model treats electrodes as electrically independent; on site, the
measured system resistance is the figure to trust for final verification. Always confirm
against the governing standard.*
