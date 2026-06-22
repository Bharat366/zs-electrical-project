import re
from flask import Flask, request, jsonify

app = Flask(__name__)
MULT = {"B": 5, "C": 10, "D": 20}
TERMS = ("earth earthing ground grounding pit grid electrode impedance resistance resistivity "
         "zs ze ohm voltage volt current ampere amp breaker mcb mccb rcd rcbo elcb fuse fault "
         "loop conductor cable wire wiring phase neutral live insulation transformer circuit "
         "disconnect trip protective cpc bonding lightning surge busbar switchgear panel load "
         "power watt megger continuity polarity electric electrical electricity rod soil supply "
         "mains substation relay capacitor inductor").split()

REFUSAL = ("I'm an electrical-engineering assistant, so I can only answer electrical questions - "
           "earthing, fault loop impedance (Zs), breakers, conductors and the like. Please ask an "
           "electrical question, or give me your earth pit and grid measurements.")


def is_elec(t):
    t = t.lower()
    if "short circuit" in t or "ohm's law" in t or "ohms law" in t:
        return True
    return any(re.search(r"\b" + w + r"s?\b", t) for w in TERMS)


def num(m):
    return float(m.group(1)) if m else None


def parse(text, cur):
    t = " " + text.lower().replace("\u03a9", " ohm ") + " "
    if re.search(r"\b(reset|clear)\b", t):
        return {"reset": True}
    o = {}
    rating = num(re.search(r"(\d+\.?\d*)\s*a(?:mp\w*)?\b", t))
    if rating:
        o["rating"] = rating
    m = re.search(r"type\s*([bcd])\b", t) or re.search(r"\b([bcd])[- ]?(?:type|curve)\b", t)
    if m:
        o["mcbType"] = m.group(1).upper()
    g = num(re.search(r"grid\s*(?:is|=|:|at|of)?\s*(\d+\.?\d*)", t))
    if g is not None:
        o["grid"] = g
    r2 = num(re.search(r"(?:earth|protective)\s*conductor\s*(?:is|=|:|at|of)?\s*(\d+\.?\d*)", t)) \
        or num(re.search(r"\br2\s*[:=]?\s*(\d+\.?\d*)", t))
    if r2 is not None:
        o["r2"] = r2
    r1 = num(re.search(r"(?:phase|line)\s*conductor\s*(?:is|=|:|at|of)?\s*(\d+\.?\d*)", t)) \
        or num(re.search(r"\br1\s*[:=]?\s*(\d+\.?\d*)", t))
    if r1 is not None:
        o["r1"] = r1
    a = re.search(r"pits?\b|electrodes?\b", t)
    if a:
        w = t[a.end():]
        stop = re.search(r"\b(grid|type|phase|conductor|breaker|mcb|amp|r[12])\b", w)
        if stop:
            w = w[:stop.start()]
        nums = [float(x) for x in re.findall(r"\d+\.?\d*", w)]
        if nums:
            o["pits"] = nums
    return o


def calc(p):
    el = [x for x in (p.get("pits") or []) if isinstance(x, (int, float))]
    if isinstance(p.get("grid"), (int, float)):
        el.append(p["grid"])
    if not el:
        return None
    ze = 0.0 if any(v == 0 for v in el) else 1.0 / sum(1.0 / v for v in el)
    r1 = p.get("r1") or 0
    r2 = p.get("r2") or 0
    zs = ze + r1 + r2
    ia = lim = ok = None
    if p.get("mcbType") in MULT and p.get("rating"):
        ia = MULT[p["mcbType"]] * p["rating"]
        lim = (2.0 / 3.0) * (230.0 / ia)
        ok = zs <= lim
    return {"ze": ze, "zs": zs, "r1": r1, "r2": r2, "ia": ia, "lim": lim, "ok": ok, "n": len(el)}


def fmt(v):
    return "%g" % round(v, 3)


def faq(t):
    t = t.lower()
    if "ohm" in t and "law" in t:
        return ("Ohm's law: V = I x R (volts = amps x ohms). A fault drives current I = U0/Zs, so a "
                "lower loop impedance gives a bigger fault current that trips the breaker faster.")
    if ("mcb" in t or "breaker" in t) and ("type" in t or "what" in t or "curve" in t or "difference" in t):
        return ("MCB curves set how fast a breaker trips, via Ia = multiplier x rating: Type B x5, "
                "Type C x10, Type D x20. A higher multiplier needs a lower Zs, since max Zs = (2/3) x (U0/Ia).")
    if ("rcd" in t or "elcb" in t or "rcbo" in t):
        return ("An RCD/ELCB trips on current leaking to earth (shock protection); an MCB protects "
                "against overload/short circuit. An RCBO combines both in one unit.")
    if ("why" in t or "purpose" in t or "need" in t) and ("earth" in t or "ground" in t):
        return ("Earthing gives fault current a low-impedance path back to source so the breaker trips "
                "fast, and keeps exposed metal safe to touch. High earth resistance means slow, "
                "dangerous disconnection.")
    if ("improve" in t or "reduce" in t or "lower" in t) and ("earth" in t or "resistance" in t):
        return ("To lower earthing resistance: add electrodes in parallel; drive rods deeper/longer; "
                "space them apart; treat the soil; or bond pits into a grid. Parallel electrodes always "
                "give a lower combined Ze.")
    if ("standard" in t or "value" in t or "recommended" in t or "max" in t or "allowed" in t) \
            and ("earth" in t or "pit" in t or "grid" in t):
        return ("Recommended: each earth pit < 5 ohm, earth grid < 1 ohm. The combined parallel value "
                "is Ze in Zs = Ze + (R1 + R2).")
    if "zs" in t or "loop impedance" in t:
        return ("Zs is the earth fault loop impedance: Zs = Ze + (R1 + R2), where Ze is the earthing "
                "system (pits + grid in parallel), R1 the phase conductor and R2 the earth conductor. "
                "A low Zs lets enough fault current flow to trip the breaker fast.")
    return None


def assess(p, r):
    s = "Zs = Ze + (R1+R2) = %s + %s = %s ohm (%d electrode%s)." % (
        fmt(r["ze"]), fmt(r["r1"] + r["r2"]), fmt(r["zs"]), r["n"], "s" if r["n"] > 1 else "")
    v = None
    if r["lim"] is None:
        s += " Add a breaker (e.g. 'Type C 32A') and I'll check it against the limit."
    else:
        s += " Limit for Type %s %g A: max Zs = (2/3) x (230/%g) = %s ohm." % (
            p["mcbType"], p["rating"], r["ia"], fmt(r["lim"]))
        if r["ok"]:
            v = "pass"
            s += " PASS - Zs is within the limit; the breaker disconnects in time."
        else:
            v = "fail"
            s += (" FAIL - Zs exceeds the limit; lower the earthing resistance, increase conductor "
                  "size, or use a more sensitive breaker.")
    flags = []
    for i, x in enumerate(p.get("pits") or []):
        if x >= 5:
            flags.append("pit %d (%g) >= 5 ohm" % (i + 1, x))
    if isinstance(p.get("grid"), (int, float)) and p["grid"] >= 1:
        flags.append("grid (%g) >= 1 ohm" % p["grid"])
    if flags:
        s += " Note: " + "; ".join(flags) + "."
    return s, v


@app.route("/")
def home():
    return PAGE


@app.route("/chat", methods=["POST"])
def chat():
    d = request.get_json(force=True, silent=True) or {}
    msg = d.get("message", "")
    p = d.get("params") or {}
    up = parse(msg, p)
    if up.get("reset"):
        return jsonify({"reply": "Cleared. Give me earth pit and grid measurements to start again.",
                        "params": {}, "verdict": None})
    if up:
        p = dict(p)
        p.update(up)
        r = calc(p)
        if r:
            reply, v = assess(p, r)
        else:
            reply, v = "Give me at least one earthing measurement (an earth pit or grid resistance).", None
        return jsonify({"reply": reply, "params": p, "verdict": v})
    low = msg.strip().lower()
    if re.match(r"^(hi+|hello+|hey+|good (morning|afternoon|evening)|namaste)\b", low):
        reply = ("Hi! I'm your electrical-safety assistant. Give me earth pit and grid measurements, "
                 "or ask an electrical question like 'what is an MCB?'.")
    elif re.search(r"\b(thanks|thank you|cheers)\b", low):
        reply = "You're welcome! Ask me anything about earthing or fault loop impedance."
    elif is_elec(msg):
        reply = faq(msg) or ("That's electrical, but my specialty is earthing and fault loop impedance. "
                             "Ask about Zs, earth pits/grid, earth resistance, or breaker limits - or "
                             "give me measurements.")
    else:
        reply = REFUSAL
    return jsonify({"reply": reply, "params": p, "verdict": None})


PAGE = r'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Zs Chatbot</title>
<style>
  body{margin:0;background:#0E1419;color:#E6EDF3;font-family:system-ui,-apple-system,sans-serif;}
  .wrap{max-width:720px;margin:0 auto;padding:20px 16px;min-height:100vh;display:flex;flex-direction:column;}
  .eyebrow{font-family:monospace;font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:#39D98A;}
  h1{font-size:23px;margin:6px 0 4px;} .sub{font-family:monospace;font-size:12px;color:#7E8C99;}
  .card{background:#161E26;border:1px solid #27323D;border-radius:10px;display:flex;flex-direction:column;
    flex:1;overflow:hidden;min-height:440px;margin-top:14px;}
  .log{flex:1;overflow-y:auto;padding:18px;display:flex;flex-direction:column;gap:11px;}
  .msg{display:flex;gap:10px;max-width:92%;}
  .av{width:26px;height:26px;border-radius:7px;flex:none;display:grid;place-items:center;font-family:monospace;
    font-size:10px;font-weight:700;background:rgba(57,217,138,.14);color:#39D98A;}
  .msg.user{align-self:flex-end;flex-direction:row-reverse;} .msg.user .av{background:#1f3a30;}
  .bub{padding:10px 13px;border-radius:11px;font-size:14px;line-height:1.55;white-space:pre-wrap;
    background:#1B252F;border:1px solid #27323D;}
  .msg.user .bub{background:#1f3a30;border-color:#2c5a47;}
  .bub.pass{border-color:#39D98A;} .bub.fail{border-color:#FF5A5A;}
  .badge{display:inline-block;font-family:monospace;font-size:11px;font-weight:700;letter-spacing:.1em;
    padding:2px 9px;border-radius:20px;margin-bottom:6px;}
  .badge.pass{color:#39D98A;background:rgba(57,217,138,.13);} .badge.fail{color:#FF5A5A;background:rgba(255,90,90,.13);}
  .chips{display:flex;gap:7px;padding:0 14px 12px;flex-wrap:wrap;}
  .chip{background:#0E1419;border:1px solid #27323D;border-radius:20px;color:#7E8C99;font-size:11px;
    font-family:monospace;padding:6px 11px;cursor:pointer;}
  .chip:hover{color:#39D98A;border-color:#39D98A;}
  .row{display:flex;gap:9px;padding:13px;border-top:1px solid #27323D;background:#1B252F;}
  input{flex:1;background:#0E1419;border:1px solid #27323D;border-radius:8px;color:#E6EDF3;font-size:14px;
    padding:11px 13px;outline:none;} input:focus{border-color:#39D98A;}
  .send{background:#39D98A;color:#08120c;border:none;border-radius:8px;width:46px;font-size:18px;cursor:pointer;}
  footer{margin-top:12px;text-align:center;color:#7E8C99;font-size:11px;font-family:monospace;}
</style></head><body><div class="wrap">
  <div class="eyebrow">Electrical Safety - Chatbot</div>
  <h1>Zs Agent</h1>
  <div class="sub">Zs = Ze + (R1+R2) | limit (2/3)(U0/Ia) | pit &lt; 5 ohm, grid &lt; 1 ohm</div>
  <div class="card">
    <div class="log" id="log"></div>
    <div class="chips" id="chips"></div>
    <div class="row">
      <input id="inp" placeholder="Ask an electrical question, or give measurements...">
      <button class="send" id="send">&#10148;</button>
    </div>
  </div>
  <footer>Electrical questions only - anything off-topic is politely declined.</footer>
</div>
<script>
  var params = {}, log = document.getElementById("log"), inp = document.getElementById("inp");
  var chips = [
    ["3 pits + grid, Type C 32A", "three pits at 4.2, 5.1, 3.8 ohm, grid 0.9 ohm, Type C 32A"],
    ["What is an MCB?", "what is an MCB and how do the types differ?"],
    ["Why do we earth?", "why do we need earthing?"],
    ["Ask off-topic (test)", "what is the weather today?"]
  ];
  var cb = document.getElementById("chips");
  chips.forEach(function(c){ var b = document.createElement("button"); b.className = "chip";
    b.textContent = c[0]; b.onclick = function(){ send(c[1]); }; cb.appendChild(b); });
  function add(role, text, verdict){
    var m = document.createElement("div"); m.className = "msg " + role;
    var av = document.createElement("div"); av.className = "av"; av.textContent = role === "ai" ? "Zs" : "You";
    var b = document.createElement("div"); b.className = "bub" + (verdict ? " " + verdict : "");
    if(verdict){ var bd = document.createElement("span"); bd.className = "badge " + verdict;
      bd.textContent = verdict.toUpperCase(); b.appendChild(bd); b.appendChild(document.createElement("br")); }
    b.appendChild(document.createTextNode(text));
    m.appendChild(av); m.appendChild(b); log.appendChild(m); log.scrollTop = log.scrollHeight;
  }
  function send(text){
    text = (text || inp.value).trim(); if(!text) return; inp.value = ""; add("user", text);
    fetch("/chat", {method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({message: text, params: params})})
    .then(function(r){ return r.json(); })
    .then(function(d){ params = d.params || {}; add("ai", d.reply, d.verdict); })
    .catch(function(e){ add("ai", "Could not reach the server. Is 'python3 app.py' still running?"); });
  }
  document.getElementById("send").onclick = function(){ send(); };
  inp.addEventListener("keydown", function(e){ if(e.key === "Enter"){ e.preventDefault(); send(); } });
  add("ai", "Hi! I'm your electrical-safety assistant. Give me earth pit and grid measurements, or ask an electrical question like 'what is an MCB?'. I only answer electrical questions - anything else I'll politely decline.");
</script></body></html>'''


if __name__ == "__main__":
    print("Zs Chatbot running -> open http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
