#!/usr/bin/env python3
"""
VZ — Vaishu AI Companion
Run:   python3 vaishu.py
Open:  http://localhost:5000
"""
import subprocess, sys
for pkg,imp in [("flask","flask"),("requests","requests")]:
    try: __import__(imp)
    except: subprocess.check_call([sys.executable,"-m","pip","install",pkg,"-q"])

# ╔══════════════════════════════════════════════╗
# ║  PASTE YOUR API KEY HERE (optional)           ║
API_KEY = ""
# ╚══════════════════════════════════════════════╝

from flask import Flask, request, jsonify, render_template_string
from pathlib import Path
import json, datetime, random, time, re, socket
import urllib.request, urllib.error, urllib.parse

app = Flask(__name__)
D = Path.home() / ".vaishu"; D.mkdir(exist_ok=True)
F = {k: D/f"{k}.json" for k in ["profile","tasks","mood","habits","history","wellness","reminders"]}

def load(k, d=None):
    if d is None: d = {}
    try:
        if F[k].exists(): return json.loads(F[k].read_text())
    except: pass
    return d

def save(k,v): F[k].write_text(json.dumps(v,indent=2,default=str))

def tod():
    h=datetime.datetime.now().hour
    if 5<=h<12: return "morning"
    if 12<=h<17: return "afternoon"
    if 17<=h<21: return "evening"
    return "night"

def is_overdue(t):
    if t.get("done") or not t.get("due"): return False
    try: return datetime.datetime.fromisoformat(t["due"])<datetime.datetime.now()
    except: return False

QUOTES=[
    "Every day is a fresh start. 🌅",
    "You are stronger than you think. 💪",
    "Small steps lead to big changes. 🚶",
    "Progress over perfection — always. ✨",
    "You deserve to be taken care of. 💙",
    "I believe in you. ⭐",
    "Be kind to yourself today. 🌸",
    "One breath at a time. 🌬️",
]

DEFAULT_HABITS=[
    {"id":1,"name":"Drink 8 glasses of water","emoji":"💧","streak":0,"last_done":""},
    {"id":2,"name":"Eat 3 proper meals","emoji":"🍽️","streak":0,"last_done":""},
    {"id":3,"name":"Sleep 7–8 hours","emoji":"😴","streak":0,"last_done":""},
    {"id":4,"name":"Exercise or walk","emoji":"🚶","streak":0,"last_done":""},
    {"id":5,"name":"No screens before bed","emoji":"📵","streak":0,"last_done":""},
    {"id":6,"name":"Take vitamins / meds","emoji":"💊","streak":0,"last_done":""},
    {"id":7,"name":"Meditate or breathe","emoji":"🧘","streak":0,"last_done":""},
    {"id":8,"name":"Read or journal","emoji":"📖","streak":0,"last_done":""},
]

LANGUAGES = {
    "en": "English", "es": "Spanish / Español", "fr": "French / Français",
    "de": "German / Deutsch", "hi": "Hindi / हिन्दी", "zh": "Chinese / 中文",
    "ja": "Japanese / 日本語", "ar": "Arabic / العربية", "pt": "Portuguese / Português",
    "ru": "Russian / Русский", "ko": "Korean / 한국어", "it": "Italian / Italiano",
    "tr": "Turkish / Türkçe", "bn": "Bengali / বাংলা", "ur": "Urdu / اردو",
    "auto": "Auto-detect (match user)"
}

CONV=[]

def ai(user_msg):
    global CONV
    key=API_KEY or load("profile").get("api_key","")
    if user_msg=="__clear__": CONV.clear(); return "ok"
    if not key:
        return ("⚠️ No API key set.\n\nGo to Profile → API Key → paste yours.\nGet your free key at console.anthropic.com")
    p=load("profile"); tasks=load("tasks",[]); moods=load("mood",[])
    pending=len([t for t in tasks if not t.get("done")])
    overdue=[t["title"] for t in tasks if is_overdue(t)]
    last_mood=moods[-1]["mood"] if moods else "unknown"
    lang=p.get("language","auto")
    now=datetime.datetime.now(); ml=user_msg.lower()

    # Local fast responses
    if re.search(r'\bjoke\b',ml):
        return random.choice([
            "Why don't scientists trust atoms? They make up everything! 😄",
            "Why did the Python dev wear glasses? He couldn't C#! 😂",
            "What do you call a fish without eyes? A fsh! 😆",
            "Why is the math book always stressed? Too many problems! 😅"
        ])
    if re.search(r'\bmotivat|inspire|pump me up|cheer me up\b',ml):
        return random.choice([
            "You didn't come this far to only come this far. Keep going! 🔥",
            "The fact that you're still trying is already incredible. ⭐",
            "Hard days build strong people. You've got this. 💪",
            "Every expert was once a beginner. Keep showing up. 🌱"
        ])
    if re.search(r'\bweather\b',ml):
        c=re.search(r'weather(?:\s+in)?\s+([a-zA-Z ]+)',ml)
        city=(c.group(1).strip() if c else "")
        try:
            url=f"https://wttr.in/{urllib.parse.quote(city or 'auto')}?format=3"
            req=urllib.request.Request(url,headers={"User-Agent":"curl/7.0"})
            with urllib.request.urlopen(req,timeout=8) as r: return "🌤 "+r.read().decode().strip()
        except: return "Couldn't fetch weather right now. Check your connection."
    if re.search(r'\bwhat time\b|\btime now\b|\bthe time\b',ml):
        return f"It's {now.strftime('%I:%M %p')} right now. ⏰"
    if re.search(r'\bwhat.?s today\b|\bwhat day\b|\bthe date\b',ml):
        return f"Today is {now.strftime('%A, %B %d %Y')}. 📅"
    if re.search(r'\bgood morning\b',ml):
        q=random.choice(QUOTES)
        return f"Good morning, {p.get('name','friend')}! ☀️\n\n\"{q}\"\n\nYou have {pending} task{'s' if pending!=1 else ''} today. Let's make it count! 💙"
    if re.search(r'\bgood night\b',ml):
        return f"Good night, {p.get('name','friend')}! 🌙\n\nPut your screens away 30 minutes before sleep. Rest well — you deserve it. 💙"
    if re.search(r'\bbreathe|breathing|calm me|help me relax\b',ml):
        return "🌬️ Box Breathing:\n\n• Inhale slowly... 1, 2, 3, 4\n• Hold... 1, 2, 3, 4\n• Exhale slowly... 1, 2, 3, 4\n• Hold... 1, 2, 3, 4\n\nRepeat 4 times. You're doing great. 🧘"
    if re.search(r'\bcalculate|calc\s+\d',ml):
        e=re.search(r'(?:calculate|calc)\s+([\d\s\+\-\*\/\(\)\.%]+)',ml)
        if e:
            try:
                r2=eval(re.sub(r'[^0-9+\-*/()., ]','',e.group(1)),{"__builtins__":{}},{})
                return f"🧮 {e.group(1).strip()} = **{r2}**"
            except: pass
    if re.search(r'\bflip.?coin|heads.?tails\b',ml):
        return f"🪙 **{random.choice(['Heads','Tails'])}!**"
    if re.search(r'\broll.?dice\b',ml):
        return f"🎲 You rolled a **{random.randint(1,6)}!**"

    # Language instruction
    lang_instruction = ""
    if lang != "auto" and lang != "en":
        lang_instruction = f"\nIMPORTANT: Always respond in {LANGUAGES.get(lang, lang)} regardless of what language the user writes in."
    elif lang == "auto":
        lang_instruction = "\nIMPORTANT: Detect the language the user is writing in and always respond in that same language."

    system=f"""You are Vaishu (VZ), a warm, emotionally intelligent personal AI companion who feels like a close best friend.
You genuinely care about {p.get('name','the user')} and their wellbeing.
Be conversational, supportive, real — never robotic or clinical. Use light emojis naturally.
Keep responses 2-5 sentences unless more is clearly needed.
Your name is Vaishu, sometimes called VZ.
Today: {now.strftime('%A %B %d, %I:%M %p')} ({tod()}) | Tasks pending: {pending} | Overdue: {overdue} | Last mood: {last_mood} | Streak: {p.get('streak',0)} days{lang_instruction}"""

    CONV.append({"role":"user","content":user_msg})
    payload=json.dumps({
        "model":"claude-sonnet-4-20250514",
        "max_tokens":800,
        "system":system,
        "messages":CONV[-20:]
    }).encode()
    req=urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={"x-api-key":key,"anthropic-version":"2023-06-01","content-type":"application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            reply=json.loads(r.read().decode())["content"][0]["text"]
        CONV.append({"role":"assistant","content":reply})
        if len(CONV)>40: CONV[:]=CONV[-40:]
        h=load("history",[]); h.append({"ts":now.isoformat(),"user":user_msg[:200],"vaishu":reply[:300]})
        save("history",h[-200:])
        return reply
    except urllib.error.HTTPError as e:
        body=e.read().decode()[:200]
        return f"⚠️ API error {e.code}: {body}"
    except Exception as e:
        return f"⚠️ Error: {str(e)[:80]}"

# ── ROUTES ──────────────────────────────────────────────
@app.route("/")
def index(): return render_template_string(HTML)

@app.route("/api/chat",methods=["POST"])
def api_chat():
    msg=request.json.get("message","").strip()
    if not msg: return jsonify({"reply":"Say something! 💙"})
    return jsonify({"reply":ai(msg)})

@app.route("/api/status")
def api_status():
    p=load("profile"); tasks=load("tasks",[]); moods=load("mood",[])
    now=datetime.datetime.now()
    return jsonify({
        "name":p.get("name","Friend"),"tod":tod(),
        "time":now.strftime("%I:%M %p"),"date":now.strftime("%A, %B %d"),
        "pending":len([t for t in tasks if not t.get("done")]),
        "overdue":len([t for t in tasks if is_overdue(t)]),
        "streak":p.get("streak",0),
        "mood":moods[-1]["mood"].capitalize() if moods else "—",
        "quote":random.choice(QUOTES),
        "api_set":bool(API_KEY or p.get("api_key","")),
        "language":p.get("language","auto")
    })

@app.route("/api/tasks",methods=["GET"])
def get_tasks():
    tasks=load("tasks",[]); [t.update(overdue=is_overdue(t)) for t in tasks]; return jsonify(tasks)

@app.route("/api/tasks",methods=["POST"])
def add_task():
    d=request.json; tasks=load("tasks",[])
    tasks.append({"id":int(time.time()*1000),"title":d.get("title",""),"priority":d.get("priority","medium"),
                  "due":d.get("due"),"done":False,"created_at":datetime.datetime.now().isoformat()})
    save("tasks",tasks); return jsonify({"ok":True})

@app.route("/api/tasks/<int:tid>/done",methods=["POST"])
def done_task(tid):
    tasks=load("tasks",[]); [t.update(done=True,completed_at=datetime.datetime.now().isoformat()) for t in tasks if t.get("id")==tid]
    save("tasks",tasks); return jsonify({"ok":True})

@app.route("/api/tasks/<int:tid>",methods=["DELETE"])
def del_task(tid):
    tasks=[t for t in load("tasks",[]) if t.get("id")!=tid]; save("tasks",tasks); return jsonify({"ok":True})

@app.route("/api/mood",methods=["POST"])
def log_mood():
    d=request.json; ml=load("mood",[])
    ml.append({"ts":datetime.datetime.now().isoformat(),"mood":d.get("mood",""),"note":d.get("note","")})
    save("mood",ml[-1000:]); return jsonify({"ok":True})

@app.route("/api/habits",methods=["GET"])
def get_habits():
    habits=load("habits",DEFAULT_HABITS); today=datetime.date.today().isoformat()
    for h in habits: h["done_today"]=h.get("last_done","")==today
    return jsonify(habits)

@app.route("/api/habits/<int:hid>/done",methods=["POST"])
def done_habit(hid):
    habits=load("habits",DEFAULT_HABITS); today=datetime.date.today().isoformat()
    yest=(datetime.date.today()-datetime.timedelta(days=1)).isoformat()
    for h in habits:
        if h.get("id")==hid:
            prev=h.get("last_done","")
            h["streak"]=(h.get("streak",0)+1) if prev in(yest,"") else(1 if prev!=today else h.get("streak",0))
            h["last_done"]=today
    save("habits",habits); return jsonify({"ok":True,"streak":next((h["streak"] for h in habits if h["id"]==hid),0)})

@app.route("/api/settings",methods=["GET"])
def get_settings():
    p=load("profile")
    return jsonify({
        "name":p.get("name",""),"wake_time":p.get("wake_time","07:00"),
        "sleep_time":p.get("sleep_time","23:00"),
        "has_key":bool(API_KEY or p.get("api_key","")),
        "language":p.get("language","auto")
    })

@app.route("/api/settings",methods=["POST"])
def save_settings():
    d=request.json; p=load("profile")
    for k in ["name","api_key","wake_time","sleep_time","language"]:
        if d.get(k) is not None: p[k]=d[k]
    p["setup_complete"]=True; save("profile",p); return jsonify({"ok":True})

HTML=r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#080810">
<title>VZ · Vaishu</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
:root{
  --bg:#080810;
  --s1:#0e0e1c;--s2:#141426;--s3:#1a1a30;--s4:#22223a;
  --a1:#6d28d9;--a2:#7c3aed;--a3:#8b5cf6;--al:rgba(109,40,217,.22);
  --p1:#db2777;--p2:#ec4899;--pl:rgba(236,72,153,.15);
  --tx:#eeeeff;--t2:#8888aa;--t3:#44446a;
  --gn:#10b981;--rd:#ef4444;--yw:#f59e0b;
  --brd:rgba(109,40,217,.2);
  --font:'Sora',sans-serif;
  --mono:'Space Mono',monospace;
}
html,body{
  height:100%;background:var(--bg);color:var(--tx);
  font-family:var(--font);max-width:480px;margin:0 auto;
  overflow:hidden;position:relative;
}

/* ═══ NOISE OVERLAY ═══════════════════════════════════ */
body::before{
  content:'';position:fixed;inset:0;z-index:0;pointer-events:none;
  background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E");
  opacity:.4;
}

/* ═══ AMBIENT GLOW ════════════════════════════════════ */
.ambient{
  position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden;
}
.amb-blob{
  position:absolute;border-radius:50%;filter:blur(80px);opacity:.12;
  animation:blobFloat 8s ease-in-out infinite;
}
.amb-blob:nth-child(1){width:300px;height:300px;background:var(--a1);top:-80px;left:-60px;animation-delay:0s}
.amb-blob:nth-child(2){width:250px;height:250px;background:var(--p1);bottom:-60px;right:-40px;animation-delay:-3s}
.amb-blob:nth-child(3){width:200px;height:200px;background:#1d4ed8;top:40%;left:30%;animation-delay:-5s}
@keyframes blobFloat{
  0%,100%{transform:translate(0,0) scale(1)}
  33%{transform:translate(20px,-20px) scale(1.05)}
  66%{transform:translate(-15px,15px) scale(.95)}
}

/* ═══ ONBOARDING ══════════════════════════════════════ */
#onboard{
  position:fixed;inset:0;z-index:999;max-width:480px;margin:0 auto;
  background:var(--bg);display:flex;flex-direction:column;
  align-items:center;justify-content:flex-start;padding:48px 24px 40px;
  overflow-y:auto;gap:0;
}
.ob-logo-wrap{
  display:flex;flex-direction:column;align-items:center;margin-bottom:32px;
}
.ob-logo{
  width:90px;height:90px;border-radius:28px;
  background:linear-gradient(145deg,#1a0a3a 0%,#2d0f5a 50%,#1a0a3a 100%);
  border:1.5px solid rgba(109,40,217,.5);
  display:flex;align-items:center;justify-content:center;
  position:relative;overflow:visible;margin-bottom:20px;
  box-shadow:0 0 0 1px rgba(109,40,217,.15),0 20px 60px rgba(109,40,217,.3),0 0 100px rgba(109,40,217,.1);
  animation:logoBreath 4s ease-in-out infinite;
}
@keyframes logoBreath{
  0%,100%{box-shadow:0 0 0 1px rgba(109,40,217,.15),0 20px 60px rgba(109,40,217,.3),0 0 100px rgba(109,40,217,.1)}
  50%{box-shadow:0 0 0 1px rgba(109,40,217,.3),0 20px 80px rgba(109,40,217,.5),0 0 140px rgba(109,40,217,.2)}
}
.ob-logo .logo-v{
  font-family:var(--font);font-size:46px;font-weight:800;
  background:linear-gradient(135deg,#a78bfa,#fff 60%,#c4b5fd);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;line-height:1;letter-spacing:-3px;
}
.ob-logo .logo-z{
  font-family:var(--mono);font-size:18px;font-weight:700;
  color:#8b5cf6;position:absolute;bottom:14px;right:14px;
  line-height:1;letter-spacing:-1px;opacity:.9;
}
.ob-title{
  font-size:28px;font-weight:800;letter-spacing:-1px;
  background:linear-gradient(135deg,#fff,#c4b5fd);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;margin-bottom:6px;text-align:center;
}
.ob-sub{font-size:14px;color:var(--t2);text-align:center;line-height:1.8;font-weight:300}

.ob-step{
  width:100%;background:var(--s1);border:1px solid var(--brd);
  border-radius:22px;padding:20px;margin-top:18px;
  position:relative;overflow:hidden;
}
.ob-step::before{
  content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(139,92,246,.4),transparent);
}
.ob-step-num{
  font-family:var(--mono);font-size:10px;color:var(--a3);
  letter-spacing:2px;text-transform:uppercase;margin-bottom:10px;
  display:flex;align-items:center;gap:8px;
}
.ob-step-num::after{content:'';flex:1;height:1px;background:var(--brd)}
.ob-label{font-size:13px;font-weight:600;color:var(--tx);margin-bottom:8px}
.ob-input{
  width:100%;background:rgba(255,255,255,.04);
  border:1px solid var(--brd);border-radius:14px;
  padding:13px 16px;color:var(--tx);font-size:15px;
  outline:none;font-family:var(--font);transition:.25s;
  caret-color:var(--a3);
}
.ob-input:focus{border-color:var(--a3);background:rgba(109,40,217,.08);box-shadow:0 0 0 3px rgba(109,40,217,.12)}
.ob-input::placeholder{color:var(--t3)}
.ob-hint{font-size:11px;color:var(--t2);margin-top:8px;line-height:1.6}
.ob-hint a{color:var(--a3);text-decoration:none}

.ob-btn{
  width:100%;padding:15px;margin-top:22px;
  background:linear-gradient(135deg,var(--a1),var(--p1));
  border:none;border-radius:16px;color:#fff;
  font-size:16px;font-weight:700;font-family:var(--font);
  cursor:pointer;letter-spacing:.3px;
  box-shadow:0 4px 30px rgba(109,40,217,.4),0 1px 0 rgba(255,255,255,.1) inset;
  transition:.2s;position:relative;overflow:hidden;
}
.ob-btn::before{
  content:'';position:absolute;inset:0;
  background:linear-gradient(135deg,rgba(255,255,255,.12),transparent);
}
.ob-btn:active{transform:scale(.98)}
.ob-btn:disabled{opacity:.4;cursor:not-allowed}

/* ═══ APP SHELL ═══════════════════════════════════════ */
#app{display:none;flex-direction:column;height:100vh;height:100dvh;position:relative;z-index:1}

/* ═══ TOPBAR ══════════════════════════════════════════ */
.topbar{
  display:flex;align-items:center;gap:10px;padding:10px 14px;
  background:rgba(8,8,16,.9);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);
  border-bottom:1px solid var(--brd);flex-shrink:0;position:relative;z-index:5;
}
.tb-logo{
  width:38px;height:38px;border-radius:12px;
  background:linear-gradient(145deg,#1a0a3a,#2d0f5a);
  border:1px solid rgba(109,40,217,.4);
  display:flex;align-items:center;justify-content:center;
  position:relative;flex-shrink:0;
  box-shadow:0 4px 16px rgba(109,40,217,.3);
}
.tb-logo .lv{font-family:var(--font);font-size:18px;font-weight:800;
  background:linear-gradient(135deg,#a78bfa,#fff);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
  line-height:1;letter-spacing:-1px;}
.tb-logo .lz{font-family:var(--mono);font-size:7px;font-weight:700;color:#8b5cf6;
  position:absolute;bottom:5px;right:5px;line-height:1;}
.tb-info{flex:1;min-width:0}
.tb-name{font-size:16px;font-weight:700;letter-spacing:-.4px}
.tb-stat{font-size:11px;color:var(--a3);margin-top:1px;display:flex;align-items:center;gap:5px;font-family:var(--mono)}
.pulse-dot{width:6px;height:6px;border-radius:50%;background:var(--gn);animation:pdot 2s infinite;flex-shrink:0}
@keyframes pdot{0%,100%{opacity:1;box-shadow:0 0 0 0 rgba(16,185,129,.4)}50%{opacity:.5;box-shadow:0 0 0 4px transparent}}
.tb-actions{display:flex;gap:6px}
.ib{
  width:36px;height:36px;
  background:rgba(255,255,255,.04);
  border:1px solid var(--brd);border-radius:11px;
  display:flex;align-items:center;justify-content:center;
  cursor:pointer;font-size:16px;transition:.15s;
  color:var(--t2);flex-shrink:0;user-select:none;
}
.ib:active{transform:scale(.88)}.ib.on{background:var(--a2);border-color:var(--a2);color:#fff}

/* ═══ STATS STRIP ═════════════════════════════════════ */
.strip{
  display:flex;gap:6px;padding:8px 12px;overflow-x:auto;flex-shrink:0;
  background:var(--s1);border-bottom:1px solid var(--brd);
}
.strip::-webkit-scrollbar{display:none}
.pill{
  display:flex;align-items:center;gap:5px;
  background:rgba(255,255,255,.04);border:1px solid var(--brd);
  border-radius:20px;padding:4px 11px;
  font-size:11px;color:var(--t2);white-space:nowrap;flex-shrink:0;
  font-family:var(--mono);
}
.pill b{color:var(--a3);font-weight:700}
.pill.warn{border-color:rgba(239,68,68,.3);background:rgba(239,68,68,.06)}
.pill.warn b{color:var(--rd)}

/* ═══ SCREENS ═════════════════════════════════════════ */
.screen{display:none;flex:1;overflow-y:auto;flex-direction:column;padding:0 0 70px;overscroll-behavior:contain}
.screen::-webkit-scrollbar{width:2px}
.screen::-webkit-scrollbar-thumb{background:var(--s3)}
.screen.on{display:flex}
#chatScreen{padding:0}

/* ═══ MESSAGES ════════════════════════════════════════ */
.msgs{flex:1;padding:14px 12px;display:flex;flex-direction:column;gap:10px;min-height:100%}
.msg{display:flex;gap:8px;animation:msgIn .28s cubic-bezier(.34,1.4,.64,1)}
@keyframes msgIn{from{opacity:0;transform:translateY(16px) scale(.94)}to{opacity:1;transform:none}}
.msg.user{flex-direction:row-reverse;align-self:flex-end;max-width:82%}
.msg.ai{max-width:90%}
.av{
  width:28px;height:28px;border-radius:9px;
  background:linear-gradient(145deg,#1a0a3a,#2d0f5a);
  border:1px solid rgba(109,40,217,.4);
  display:flex;align-items:center;justify-content:center;
  flex-shrink:0;margin-top:3px;
  box-shadow:0 2px 10px rgba(109,40,217,.25);
}
.av .lv{font-size:12px;font-weight:800;font-family:var(--font);
  background:linear-gradient(135deg,#a78bfa,#fff);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
  line-height:1;letter-spacing:-1px;}
.bub{
  padding:10px 14px;border-radius:18px;
  font-size:14px;line-height:1.65;white-space:pre-wrap;word-break:break-word;
  font-weight:400;
}
.ai .bub{
  background:var(--s2);border:1px solid var(--brd);
  border-radius:4px 18px 18px 18px;color:var(--tx);
}
.user .bub{
  background:linear-gradient(135deg,var(--a1) 0%,var(--p1) 100%);
  border-radius:18px 4px 18px 18px;color:#fff;
  box-shadow:0 4px 16px rgba(109,40,217,.3);
}
.bub b{font-weight:700}.bub em{font-style:italic}
.typdot{display:flex;gap:5px;padding:6px 2px;align-items:center}
.typdot span{width:6px;height:6px;background:var(--a3);border-radius:50%;animation:td 1.4s infinite}
.typdot span:nth-child(2){animation-delay:.2s}.typdot span:nth-child(3){animation-delay:.4s}
@keyframes td{0%,60%,100%{transform:translateY(0);opacity:.25}30%{transform:translateY(-7px);opacity:1}}
.day-sep{
  text-align:center;font-size:10px;color:var(--t3);padding:4px 0;
  display:flex;align-items:center;gap:8px;
  font-family:var(--mono);letter-spacing:.5px;
}
.day-sep::before,.day-sep::after{content:'';flex:1;height:1px;background:var(--s3)}

/* ═══ INPUT BAR ═══════════════════════════════════════ */
.ibar{
  position:fixed;bottom:58px;left:0;right:0;max-width:480px;margin:0 auto;
  display:flex;align-items:flex-end;gap:7px;padding:8px 10px;
  background:rgba(8,8,16,.95);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);
  border-top:1px solid var(--brd);z-index:10;
}
.ibar textarea{
  flex:1;background:rgba(255,255,255,.04);border:1px solid var(--brd);
  border-radius:20px;padding:10px 15px;color:var(--tx);
  font-size:14px;resize:none;outline:none;max-height:100px;min-height:42px;
  line-height:1.5;font-family:var(--font);transition:.2s;
  caret-color:var(--a3);
}
.ibar textarea:focus{border-color:rgba(109,40,217,.5);background:rgba(109,40,217,.06)}
.ibar textarea::placeholder{color:var(--t3)}
.ibtn{
  width:42px;height:42px;border-radius:50%;border:none;
  cursor:pointer;display:flex;align-items:center;justify-content:center;
  font-size:18px;transition:.15s;flex-shrink:0;
}
.ibtn:active{transform:scale(.85)}
.mic-btn{background:rgba(255,255,255,.06);border:1px solid var(--brd);color:var(--t2)}
.mic-btn.on{background:var(--rd);color:#fff;animation:mpulse 1s infinite;border-color:var(--rd)}
@keyframes mpulse{0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,.5)}50%{box-shadow:0 0 0 8px transparent}}
.send-btn{
  background:linear-gradient(135deg,var(--a1),var(--p1));color:#fff;
  box-shadow:0 3px 16px rgba(109,40,217,.35);
}

/* ═══ BOTTOM NAV ══════════════════════════════════════ */
.bnav{
  position:fixed;bottom:0;left:0;right:0;max-width:480px;margin:0 auto;
  display:flex;background:rgba(14,14,28,.97);
  backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);
  border-top:1px solid var(--brd);height:58px;z-index:20;
}
.nb{
  flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;
  gap:2px;font-size:9px;font-weight:500;color:var(--t3);cursor:pointer;
  border:none;background:none;padding:6px 0;transition:.2s;
  letter-spacing:.3px;text-transform:uppercase;font-family:var(--mono);
}
.nb .ni{font-size:19px;transition:.2s}
.nb.on{color:var(--a3)}
.nb.on .ni{filter:drop-shadow(0 0 8px var(--a2));transform:scale(1.1)}

/* ═══ FAB ═════════════════════════════════════════════ */
.fab{
  position:fixed;bottom:70px;right:16px;width:50px;height:50px;
  background:linear-gradient(135deg,var(--a1),var(--p1));
  border-radius:50%;display:none;align-items:center;justify-content:center;
  font-size:24px;color:#fff;cursor:pointer;
  box-shadow:0 4px 24px rgba(109,40,217,.45);z-index:15;border:none;
  transition:.15s;user-select:none;
}
.fab:active{transform:scale(.88)}.fab.show{display:flex}

/* ═══ SECTION PADDING ═════════════════════════════════ */
#tasksScreen,#habitsScreen,#profileScreen,#guideScreen{padding:16px 14px 80px;gap:0}
.sec-head{margin-bottom:20px}
.sec-title{font-size:22px;font-weight:800;letter-spacing:-.6px;margin-bottom:3px}
.sec-sub{font-size:12px;color:var(--t2);font-family:var(--mono)}

/* ═══ TASKS ═══════════════════════════════════════════ */
.tcard{
  background:var(--s1);border:1px solid var(--brd);border-radius:18px;
  padding:13px 14px;display:flex;align-items:center;gap:11px;margin-bottom:8px;
  transition:opacity .3s,transform .12s;position:relative;overflow:hidden;
}
.tcard::before{
  content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(139,92,246,.2),transparent);
}
.tcard:active{transform:scale(.99)}.tcard.done{opacity:.3}
.tchk{
  width:24px;height:24px;border:2px solid rgba(109,40,217,.5);border-radius:8px;
  cursor:pointer;display:flex;align-items:center;justify-content:center;
  flex-shrink:0;transition:.2s;font-size:12px;font-weight:700;color:transparent;
}
.tchk.done{background:var(--a2);border-color:var(--a2);color:#fff;border-radius:8px}
.tinfo{flex:1;min-width:0}
.ttitle{font-size:14px;font-weight:500;line-height:1.4}
.ttitle.done{text-decoration:line-through;color:var(--t3)}
.tmeta{font-size:11px;color:var(--t2);margin-top:4px;display:flex;align-items:center;gap:5px;font-family:var(--mono)}
.tmeta.ov{color:var(--rd)}
.badge{font-size:10px;padding:2px 8px;border-radius:20px;font-weight:700;font-family:var(--mono)}
.bh{background:rgba(239,68,68,.12);color:var(--rd);border:1px solid rgba(239,68,68,.2)}
.bm{background:rgba(245,158,11,.1);color:var(--yw);border:1px solid rgba(245,158,11,.2)}
.bl{background:rgba(16,185,129,.1);color:var(--gn);border:1px solid rgba(16,185,129,.2)}
.tdel{color:var(--t3);cursor:pointer;padding:5px;font-size:15px;flex-shrink:0;transition:.15s}
.tdel:active{color:var(--rd)}

/* ═══ HABITS ══════════════════════════════════════════ */
.hcard{
  background:var(--s1);border:1px solid var(--brd);border-radius:18px;
  padding:14px 16px;display:flex;align-items:center;gap:13px;margin-bottom:8px;
  cursor:pointer;transition:.15s;position:relative;overflow:hidden;
}
.hcard::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(139,92,246,.2),transparent)}
.hcard:active{transform:scale(.98)}
.hcard.done{border-color:rgba(16,185,129,.3);background:rgba(16,185,129,.04)}
.hcard.done::before{background:linear-gradient(90deg,transparent,rgba(16,185,129,.3),transparent)}
.hemoji{font-size:24px;flex-shrink:0}
.hinfo{flex:1}.hname{font-size:14px;font-weight:500}
.hstreak{font-size:11px;color:var(--t2);margin-top:3px;font-family:var(--mono)}
.hstreak b{color:var(--yw)}
.hbox{font-size:22px;transition:.3s;flex-shrink:0}

/* ═══ PROFILE ═════════════════════════════════════════ */
.phead{
  display:flex;flex-direction:column;align-items:center;
  padding:28px 0 22px;gap:12px;
}
.pav{
  width:78px;height:78px;border-radius:26px;
  background:linear-gradient(145deg,#1a0a3a,#2d0f5a);
  border:1.5px solid rgba(109,40,217,.4);
  display:flex;align-items:center;justify-content:center;position:relative;
  box-shadow:0 0 40px rgba(109,40,217,.3),0 0 80px rgba(109,40,217,.1);
}
.pav .lv{font-size:34px;font-weight:800;font-family:var(--font);
  background:linear-gradient(135deg,#a78bfa,#fff);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
  letter-spacing:-2px;}
.pav .lz{font-size:11px;font-weight:700;color:#8b5cf6;
  position:absolute;bottom:10px;right:10px;font-family:var(--mono);}
.pname{font-size:22px;font-weight:800;letter-spacing:-.5px}
.psub{font-size:11px;color:var(--t2);font-family:var(--mono);letter-spacing:.3px}
.pgroup{
  background:var(--s1);border:1px solid var(--brd);border-radius:20px;
  overflow:hidden;margin-bottom:12px;position:relative;
}
.pgroup::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(139,92,246,.3),transparent)}
.pitem{
  display:flex;align-items:center;gap:13px;padding:14px 16px;
  border-bottom:1px solid rgba(255,255,255,.04);cursor:pointer;
  transition:.15s;user-select:none;
}
.pitem:last-child{border-bottom:none}.pitem:active{background:rgba(255,255,255,.03)}
.pico{font-size:19px;width:28px;text-align:center;flex-shrink:0}
.ptext{flex:1}.plabel{font-size:14px;font-weight:500}
.pval{font-size:11px;color:var(--t2);margin-top:2px;font-family:var(--mono)}
.parr{color:var(--t3);font-size:18px}

/* ═══ GUIDE ═══════════════════════════════════════════ */
.guide-hero{
  background:var(--s1);border:1px solid var(--brd);border-radius:20px;
  padding:20px;margin-bottom:14px;text-align:center;position:relative;overflow:hidden;
}
.guide-hero::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(139,92,246,.4),transparent)}
.guide-hero-icon{font-size:36px;margin-bottom:10px}
.guide-hero-title{font-size:17px;font-weight:700;margin-bottom:6px;letter-spacing:-.3px}
.guide-hero-sub{font-size:13px;color:var(--t2);line-height:1.6}
.guide-section{margin-bottom:14px}
.guide-section-title{
  font-size:11px;font-weight:700;color:var(--a3);letter-spacing:1.5px;
  text-transform:uppercase;margin-bottom:10px;font-family:var(--mono);
  display:flex;align-items:center;gap:8px;
}
.guide-section-title::after{content:'';flex:1;height:1px;background:var(--brd)}
.guide-card{
  background:var(--s1);border:1px solid var(--brd);border-radius:16px;
  padding:14px 16px;margin-bottom:8px;
}
.guide-row{display:flex;align-items:flex-start;gap:12px;margin-bottom:12px}
.guide-row:last-child{margin-bottom:0}
.guide-icon{font-size:20px;flex-shrink:0;width:28px;text-align:center;margin-top:1px}
.guide-text .gt-title{font-size:13px;font-weight:600;margin-bottom:2px}
.guide-text .gt-desc{font-size:12px;color:var(--t2);line-height:1.6}
.cmd-tag{
  display:inline-block;background:rgba(109,40,217,.15);border:1px solid rgba(109,40,217,.25);
  border-radius:8px;padding:2px 8px;font-size:11px;font-family:var(--mono);color:var(--a3);
  margin:2px 2px 2px 0;
}

/* ═══ OVERLAY / SHEET ═════════════════════════════════ */
.ov{
  position:fixed;inset:0;max-width:480px;margin:0 auto;
  background:rgba(0,0,0,.8);display:none;align-items:flex-end;
  z-index:100;backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
}
.ov.on{display:flex}
.sheet{
  background:var(--s1);border-radius:28px 28px 0 0;
  padding:0 18px 44px;width:100%;
  animation:sheetUp .32s cubic-bezier(.34,1.15,.64,1);
  max-height:90dvh;overflow-y:auto;
  border-top:1px solid var(--brd);
  position:relative;
}
.sheet::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(139,92,246,.4),transparent)}
@keyframes sheetUp{from{transform:translateY(100%)}to{transform:translateY(0)}}
.handle{width:36px;height:4px;background:rgba(255,255,255,.12);border-radius:2px;margin:14px auto 22px}
.sh-title{font-size:19px;font-weight:700;margin-bottom:18px;letter-spacing:-.4px}
.fg{margin-bottom:14px}
.fl{font-size:11px;font-weight:600;color:var(--a3);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;display:block;font-family:var(--mono)}
.fi{
  width:100%;background:rgba(255,255,255,.04);border:1px solid var(--brd);
  border-radius:14px;padding:12px 14px;color:var(--tx);font-size:14px;
  outline:none;font-family:var(--font);transition:.2s;caret-color:var(--a3);
}
.fi:focus{border-color:rgba(109,40,217,.5);box-shadow:0 0 0 3px rgba(109,40,217,.1)}
.fi::placeholder{color:var(--t3)}
select.fi option{background:var(--s2)}
.shbtn{
  width:100%;padding:14px;
  background:linear-gradient(135deg,var(--a1),var(--p1));
  border:none;border-radius:16px;color:#fff;font-size:15px;font-weight:700;
  font-family:var(--font);cursor:pointer;
  box-shadow:0 4px 20px rgba(109,40,217,.35);transition:.15s;margin-top:4px;
}
.shbtn:active{transform:scale(.98)}.shbtn:disabled{opacity:.4;cursor:not-allowed}
.shbtn2{
  background:rgba(255,255,255,.05);border:1px solid var(--brd);color:var(--t2);
  box-shadow:none;margin-top:10px;
}

/* mood */
.mgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:16px}
.mi{
  background:rgba(255,255,255,.04);border:2px solid transparent;border-radius:16px;
  padding:12px 6px;text-align:center;cursor:pointer;transition:.15s;user-select:none;
}
.mi:active,.mi.sel{border-color:var(--a2);background:rgba(109,40,217,.14)}
.me{font-size:24px}.ml{font-size:10px;color:var(--t2);margin-top:4px;font-family:var(--mono)}

/* toast */
.toast{
  position:fixed;top:70px;left:50%;transform:translateX(-50%);
  background:var(--s3);border:1px solid var(--brd);border-radius:24px;
  padding:9px 20px;font-size:13px;color:var(--tx);z-index:500;
  animation:toastIn .25s cubic-bezier(.34,1.4,.64,1);white-space:nowrap;
  pointer-events:none;box-shadow:0 8px 30px rgba(0,0,0,.5);font-family:var(--mono);
}
@keyframes toastIn{from{opacity:0;transform:translateX(-50%) translateY(-12px) scale(.9)}}

/* ═══ OVERLAY SCREEN (Google Assistant style) ═════════ */
#assistantOverlay{
  position:fixed;inset:0;max-width:480px;margin:0 auto;z-index:200;
  display:none;flex-direction:column;align-items:center;justify-content:flex-end;
  padding-bottom:60px;
  background:rgba(8,8,16,.92);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
}
#assistantOverlay.on{display:flex}
.ao-ring{
  width:90px;height:90px;border-radius:50%;position:relative;
  display:flex;align-items:center;justify-content:center;margin-bottom:24px;
}
.ao-ring::before{
  content:'';position:absolute;inset:-8px;border-radius:50%;
  border:2px solid transparent;
  background:linear-gradient(135deg,var(--a1),var(--p1)) border-box;
  -webkit-mask:linear-gradient(#fff 0 0) padding-box,linear-gradient(#fff 0 0);
  -webkit-mask-composite:destination-out;mask-composite:exclude;
  animation:ringPulse 1.5s ease-in-out infinite;
}
@keyframes ringPulse{
  0%,100%{transform:scale(1);opacity:.7}
  50%{transform:scale(1.08);opacity:1}
}
.ao-logo{
  width:90px;height:90px;border-radius:50%;
  background:linear-gradient(145deg,#1a0a3a,#2d0f5a);
  border:1.5px solid rgba(109,40,217,.5);
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  box-shadow:0 0 60px rgba(109,40,217,.5);
  position:relative;
}
.ao-logo .lv{font-size:38px;font-weight:800;font-family:var(--font);
  background:linear-gradient(135deg,#a78bfa,#fff);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
  line-height:1;letter-spacing:-2px;}
.ao-logo .lz{font-size:12px;font-weight:700;color:#8b5cf6;
  position:absolute;bottom:12px;right:12px;font-family:var(--mono);}
.ao-waves{
  display:flex;align-items:center;gap:5px;height:30px;margin-bottom:20px;
}
.ao-wave{
  width:4px;border-radius:2px;background:linear-gradient(to top,var(--a1),var(--p2));
  animation:waveAnim 0.8s ease-in-out infinite;
}
.ao-wave:nth-child(1){height:10px;animation-delay:0s}
.ao-wave:nth-child(2){height:20px;animation-delay:.1s}
.ao-wave:nth-child(3){height:28px;animation-delay:.2s}
.ao-wave:nth-child(4){height:20px;animation-delay:.3s}
.ao-wave:nth-child(5){height:14px;animation-delay:.4s}
.ao-wave:nth-child(6){height:24px;animation-delay:.5s}
.ao-wave:nth-child(7){height:18px;animation-delay:.6s}
@keyframes waveAnim{
  0%,100%{transform:scaleY(0.4);opacity:.6}
  50%{transform:scaleY(1);opacity:1}
}
.ao-waves.idle .ao-wave{animation:none;height:4px;opacity:.3}
.ao-text{
  font-size:18px;font-weight:600;letter-spacing:-.3px;
  margin-bottom:8px;text-align:center;
}
.ao-sub{font-size:13px;color:var(--t2);margin-bottom:32px;text-align:center;font-family:var(--mono)}
.ao-transcript{
  font-size:16px;color:var(--a3);text-align:center;
  min-height:24px;font-weight:500;margin-bottom:20px;letter-spacing:-.2px;
  max-width:300px;line-height:1.5;
}
.ao-close{
  width:56px;height:56px;border-radius:50%;
  background:rgba(255,255,255,.06);border:1px solid var(--brd);
  display:flex;align-items:center;justify-content:center;
  font-size:22px;cursor:pointer;transition:.15s;
}
.ao-close:active{transform:scale(.9)}

/* wake badge */
.wbadge{
  display:none;align-items:center;gap:7px;
  background:rgba(109,40,217,.1);border:1px solid rgba(109,40,217,.25);
  border-radius:20px;padding:5px 14px;font-size:11px;color:var(--a3);
  margin:8px 12px 0;font-family:var(--mono);letter-spacing:.3px;
}
.wbadge.on{display:flex}
.wbadge .wd{width:6px;height:6px;border-radius:50%;background:var(--a2);animation:pdot 1s infinite}

a{color:var(--a3);text-decoration:none}
</style>
</head>
<body>
<div class="ambient">
  <div class="amb-blob"></div>
  <div class="amb-blob"></div>
  <div class="amb-blob"></div>
</div>

<!-- ════ ONBOARDING ════ -->
<div id="onboard">
  <div class="ob-logo-wrap">
    <div class="ob-logo">
      <span class="logo-v">V</span>
      <span class="logo-z">z</span>
    </div>
    <div class="ob-title">Vaishu</div>
    <div class="ob-sub">Your personal AI companion.<br>Always here. Always caring. 💙</div>
  </div>

  <div class="ob-step">
    <div class="ob-step-num">Step 01 — Your Name</div>
    <div class="ob-label">What should I call you?</div>
    <input class="ob-input" id="obName" placeholder="Enter your name..."/>
  </div>

  <div class="ob-step">
    <div class="ob-step-num">Step 02 — API Key</div>
    <div class="ob-label">Anthropic API Key</div>
    <input class="ob-input" id="obKey" placeholder="sk-ant-api03-..." autocomplete="off" spellcheck="false"/>
    <div class="ob-hint">
      Get your free key → <a href="https://console.anthropic.com" target="_blank">console.anthropic.com</a><br>
      Your key is stored only on this device.
    </div>
  </div>

  <div class="ob-step">
    <div class="ob-step-num">Step 03 — Language</div>
    <div class="ob-label">Preferred Language</div>
    <select class="ob-input" id="obLang">
      <option value="auto">Auto-detect (match your language)</option>
      <option value="en">English</option>
      <option value="hi">Hindi / हिन्दी</option>
      <option value="es">Spanish / Español</option>
      <option value="fr">French / Français</option>
      <option value="de">German / Deutsch</option>
      <option value="zh">Chinese / 中文</option>
      <option value="ja">Japanese / 日本語</option>
      <option value="ar">Arabic / العربية</option>
      <option value="pt">Portuguese / Português</option>
      <option value="ru">Russian / Русский</option>
      <option value="ko">Korean / 한국어</option>
      <option value="it">Italian / Italiano</option>
      <option value="tr">Turkish / Türkçe</option>
      <option value="bn">Bengali / বাংলা</option>
      <option value="ur">Urdu / اردو</option>
    </select>
    <div class="ob-hint">Vaishu can speak and understand any language.</div>
  </div>

  <button class="ob-btn" onclick="obDone()">✦ Start Chatting with Vaishu</button>
</div>

<!-- ════ APP ════ -->
<div id="app">

  <!-- TOPBAR -->
  <div class="topbar">
    <div class="tb-logo">
      <span class="lv">V</span><span class="lz">z</span>
    </div>
    <div class="tb-info">
      <div class="tb-name">Vaishu</div>
      <div class="tb-stat"><span class="pulse-dot"></span><span id="tbStat">Online</span></div>
    </div>
    <div class="tb-actions">
      <button class="ib" onclick="openMoodSheet()" title="Mood">😊</button>
      <button class="ib" id="wakeBtn" onclick="toggleWake()" title="Background listening">🎙️</button>
    </div>
  </div>

  <div class="wbadge" id="wakeBadge">
    <span class="wd"></span>Say "Sup Vaishu" or "Hey Vaishu"
  </div>

  <!-- STATS -->
  <div class="strip">
    <div class="pill">📋 <b id="sTask">0</b> tasks</div>
    <div class="pill">💭 <b id="sMood">—</b></div>
    <div class="pill">🔥 <b id="sStrk">0</b>d streak</div>
    <div class="pill warn" id="sOvPill" style="display:none">⚠️ <b id="sOv">0</b> overdue</div>
    <div class="pill">⏰ <b id="sTime">—</b></div>
  </div>

  <!-- SCREENS -->
  <div class="screen on" id="chatScreen">
    <div class="msgs" id="msgs"></div>
  </div>

  <div class="screen" id="tasksScreen">
    <div class="sec-head">
      <div class="sec-title">Tasks</div>
      <div class="sec-sub">Tap circle to complete</div>
    </div>
    <div id="taskList"></div>
  </div>

  <div class="screen" id="habitsScreen">
    <div class="sec-head">
      <div class="sec-title">Daily Habits</div>
      <div class="sec-sub">Tap to mark done today</div>
    </div>
    <div id="habitList"></div>
  </div>

  <div class="screen" id="profileScreen">
    <div class="phead">
      <div class="pav"><span class="lv">V</span><span class="lz">z</span></div>
      <div class="pname" id="pName">Friend</div>
      <div class="psub" id="pSub">VZ · Vaishu AI</div>
    </div>
    <div class="pgroup">
      <div class="pitem" onclick="openSet('name')">
        <div class="pico">✏️</div>
        <div class="ptext"><div class="plabel">Change Name</div><div class="pval" id="pvName">—</div></div>
        <div class="parr">›</div>
      </div>
      <div class="pitem" onclick="openSet('key')">
        <div class="pico">🔑</div>
        <div class="ptext"><div class="plabel">API Key</div><div class="pval" id="pvKey">—</div></div>
        <div class="parr">›</div>
      </div>
      <div class="pitem" onclick="openSet('lang')">
        <div class="pico">🌐</div>
        <div class="ptext"><div class="plabel">Language</div><div class="pval" id="pvLang">Auto-detect</div></div>
        <div class="parr">›</div>
      </div>
      <div class="pitem" onclick="openSet('sched')">
        <div class="pico">⏰</div>
        <div class="ptext"><div class="plabel">Wake / Sleep Schedule</div><div class="pval" id="pvSched">—</div></div>
        <div class="parr">›</div>
      </div>
    </div>
    <div class="pgroup">
      <div class="pitem" onclick="clearMem()">
        <div class="pico">🧹</div>
        <div class="ptext"><div class="plabel">Clear Chat Memory</div><div class="pval">Reset Vaishu's memory</div></div>
        <div class="parr">›</div>
      </div>
      <div class="pitem" onclick="goTo('guide')">
        <div class="pico">📖</div>
        <div class="ptext"><div class="plabel">User Guide</div><div class="pval">How to use Vaishu</div></div>
        <div class="parr">›</div>
      </div>
      <div class="pitem" onclick="openSheet('emergSh')">
        <div class="pico">🆘</div>
        <div class="ptext"><div class="plabel">Emergency Numbers</div><div class="pval">911 · 988 · Text 741741</div></div>
        <div class="parr">›</div>
      </div>
    </div>
  </div>

  <!-- GUIDE SCREEN -->
  <div class="screen" id="guideScreen">
    <div class="guide-hero">
      <div class="guide-hero-icon">📖</div>
      <div class="guide-hero-title">Welcome to Vaishu (VZ)</div>
      <div class="guide-hero-sub">Your personal AI companion. Here's everything you can do.</div>
    </div>

    <div class="guide-section">
      <div class="guide-section-title">Voice Activation</div>
      <div class="guide-card">
        <div class="guide-row">
          <div class="guide-icon">🎙️</div>
          <div class="guide-text">
            <div class="gt-title">Wake Word (Background)</div>
            <div class="gt-desc">Tap the 🎙️ button in the top bar. Then say <span class="cmd-tag">Sup Vaishu</span> or <span class="cmd-tag">Hey Vaishu</span> — Vaishu will pop up on screen like Google Assistant, ready to listen.</div>
          </div>
        </div>
        <div class="guide-row">
          <div class="guide-icon">🔴</div>
          <div class="guide-text">
            <div class="gt-title">Manual Mic</div>
            <div class="gt-desc">Tap the mic 🎤 button in the chat bar to speak directly. Works in any language.</div>
          </div>
        </div>
      </div>
    </div>

    <div class="guide-section">
      <div class="guide-section-title">Chat Commands</div>
      <div class="guide-card">
        <div class="guide-row">
          <div class="guide-icon">🌤️</div>
          <div class="guide-text">
            <div class="gt-title">Weather</div>
            <div class="gt-desc"><span class="cmd-tag">weather in London</span> <span class="cmd-tag">weather today</span></div>
          </div>
        </div>
        <div class="guide-row">
          <div class="guide-icon">😂</div>
          <div class="guide-text">
            <div class="gt-title">Fun</div>
            <div class="gt-desc"><span class="cmd-tag">tell me a joke</span> <span class="cmd-tag">flip a coin</span> <span class="cmd-tag">roll a dice</span></div>
          </div>
        </div>
        <div class="guide-row">
          <div class="guide-icon">🧮</div>
          <div class="guide-text">
            <div class="gt-title">Calculator</div>
            <div class="gt-desc"><span class="cmd-tag">calc 250 * 4</span> <span class="cmd-tag">calculate 15% of 200</span></div>
          </div>
        </div>
        <div class="guide-row">
          <div class="guide-icon">🧘</div>
          <div class="guide-text">
            <div class="gt-title">Wellness</div>
            <div class="gt-desc"><span class="cmd-tag">help me breathe</span> <span class="cmd-tag">calm me down</span> <span class="cmd-tag">motivate me</span></div>
          </div>
        </div>
        <div class="guide-row">
          <div class="guide-icon">💬</div>
          <div class="guide-text">
            <div class="gt-title">Just Talk</div>
            <div class="gt-desc">Talk to Vaishu in any language. She adapts to you. Ask anything, vent, share your day — she always listens.</div>
          </div>
        </div>
      </div>
    </div>

    <div class="guide-section">
      <div class="guide-section-title">Tasks & Habits</div>
      <div class="guide-card">
        <div class="guide-row">
          <div class="guide-icon">📋</div>
          <div class="guide-text">
            <div class="gt-title">Add Tasks</div>
            <div class="gt-desc">Go to Tasks tab → tap <b>＋</b>. Or tell Vaishu in chat: <span class="cmd-tag">add task finish report</span></div>
          </div>
        </div>
        <div class="guide-row">
          <div class="guide-icon">🏃</div>
          <div class="guide-text">
            <div class="gt-title">Daily Habits</div>
            <div class="gt-desc">Tap any habit to mark it done. Build streaks. Vaishu tracks your consistency.</div>
          </div>
        </div>
      </div>
    </div>

    <div class="guide-section">
      <div class="guide-section-title">Languages</div>
      <div class="guide-card">
        <div class="guide-row">
          <div class="guide-icon">🌐</div>
          <div class="guide-text">
            <div class="gt-title">Multilingual</div>
            <div class="gt-desc">Vaishu speaks 15+ languages. Set your language in Profile → Language, or use Auto-detect and write in any language — Vaishu will reply in the same language.</div>
          </div>
        </div>
      </div>
    </div>

    <div class="guide-section">
      <div class="guide-section-title">Making it an App</div>
      <div class="guide-card">
        <div class="guide-row">
          <div class="guide-icon">📱</div>
          <div class="guide-text">
            <div class="gt-title">Add to Home Screen (iOS / Android)</div>
            <div class="gt-desc">Open <span class="cmd-tag">http://127.0.0.1:5000</span> in your phone's browser → tap Share → "Add to Home Screen". It will open like a real app, fullscreen, no browser bar.</div>
          </div>
        </div>
        <div class="guide-row">
          <div class="guide-icon">🤖</div>
          <div class="guide-text">
            <div class="gt-title">Real APK (Android)</div>
            <div class="gt-desc">Yes — it's possible! Use <b>WebView APK</b> approach: install Android Studio, create a new project, paste the WebView code that loads <span class="cmd-tag">http://10.0.2.2:5000</span>, build APK. Or use <b>PWA Builder</b> (pwabuilder.com) to generate an APK from the web app if you host it online.</div>
          </div>
        </div>
        <div class="guide-row">
          <div class="guide-icon">☁️</div>
          <div class="guide-text">
            <div class="gt-title">Share with Many People</div>
            <div class="gt-desc">Deploy to a server (Railway, Render, or a VPS). Users access it at your domain, each with their own profile. Or wrap in a React Native / Flutter WebView app and publish to Play Store.</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- INPUT -->
  <div class="ibar" id="ibar">
    <button class="ibtn mic-btn" id="micBtn" onclick="toggleMic()">🎤</button>
    <textarea id="inp" placeholder="Talk to Vaishu..." rows="1"
      oninput="autoResize(this)" onkeydown="onKey(event)"></textarea>
    <button class="ibtn send-btn" onclick="sendMsg()">➤</button>
  </div>

  <!-- FAB -->
  <button class="fab" id="fab" onclick="openSheet('addSh')">＋</button>

  <!-- NAV -->
  <nav class="bnav">
    <button class="nb on" id="nb-chat" onclick="goTo('chat')"><span class="ni">💬</span>Chat</button>
    <button class="nb" id="nb-tasks" onclick="goTo('tasks')"><span class="ni">📋</span>Tasks</button>
    <button class="nb" id="nb-habits" onclick="goTo('habits')"><span class="ni">🏃</span>Habits</button>
    <button class="nb" id="nb-profile" onclick="goTo('profile')"><span class="ni">👤</span>Profile</button>
  </nav>
</div>

<!-- ════ ASSISTANT OVERLAY ════ -->
<div id="assistantOverlay">
  <div class="ao-ring">
    <div class="ao-logo">
      <span class="lv">V</span>
      <span class="lz">z</span>
    </div>
  </div>
  <div class="ao-waves idle" id="aoWaves">
    <div class="ao-wave"></div><div class="ao-wave"></div><div class="ao-wave"></div>
    <div class="ao-wave"></div><div class="ao-wave"></div><div class="ao-wave"></div>
    <div class="ao-wave"></div>
  </div>
  <div class="ao-text" id="aoText">Hey, it's Vaishu!</div>
  <div class="ao-sub" id="aoSub">Listening...</div>
  <div class="ao-transcript" id="aoTranscript"></div>
  <div class="ao-close" onclick="closeAssistant()">✕</div>
</div>

<!-- ════ SHEETS ════ -->

<!-- Add Task -->
<div class="ov" id="addSh" onclick="closeSheet('addSh')">
 <div class="sheet" onclick="event.stopPropagation()">
  <div class="handle"></div>
  <div class="sh-title">Add Task</div>
  <div class="fg"><label class="fl">Task Name</label>
    <input class="fi" id="tName" placeholder="What do you need to do?"/></div>
  <div class="fg"><label class="fl">Priority</label>
    <select class="fi" id="tPri">
      <option value="medium">Medium</option>
      <option value="high">High ⚡</option>
      <option value="low">Low</option>
    </select></div>
  <button class="shbtn" onclick="addTask()">Add Task</button>
  <button class="shbtn shbtn2" onclick="closeSheet('addSh')">Cancel</button>
 </div>
</div>

<!-- Mood -->
<div class="ov" id="moodSh" onclick="closeSheet('moodSh')">
 <div class="sheet" onclick="event.stopPropagation()">
  <div class="handle"></div>
  <div class="sh-title">How are you feeling?</div>
  <div class="mgrid">
    <div class="mi" onclick="pickM('happy',this)"><div class="me">😊</div><div class="ml">Happy</div></div>
    <div class="mi" onclick="pickM('calm',this)"><div class="me">😌</div><div class="ml">Calm</div></div>
    <div class="mi" onclick="pickM('excited',this)"><div class="me">🤩</div><div class="ml">Excited</div></div>
    <div class="mi" onclick="pickM('grateful',this)"><div class="me">🙏</div><div class="ml">Grateful</div></div>
    <div class="mi" onclick="pickM('tired',this)"><div class="me">😴</div><div class="ml">Tired</div></div>
    <div class="mi" onclick="pickM('stressed',this)"><div class="me">😤</div><div class="ml">Stressed</div></div>
    <div class="mi" onclick="pickM('sad',this)"><div class="me">😢</div><div class="ml">Sad</div></div>
    <div class="mi" onclick="pickM('anxious',this)"><div class="me">😰</div><div class="ml">Anxious</div></div>
    <div class="mi" onclick="pickM('lonely',this)"><div class="me">🥺</div><div class="ml">Lonely</div></div>
    <div class="mi" onclick="pickM('angry',this)"><div class="me">😠</div><div class="ml">Angry</div></div>
    <div class="mi" onclick="pickM('sick',this)"><div class="me">🤒</div><div class="ml">Sick</div></div>
    <div class="mi" onclick="pickM('numb',this)"><div class="me">😶</div><div class="ml">Numb</div></div>
  </div>
  <input class="fi" id="mNote" placeholder="Any notes? (optional)" style="margin-bottom:14px"/>
  <button class="shbtn" id="mBtn" onclick="submitMood()" disabled>Log Mood & Chat</button>
 </div>
</div>

<!-- Settings -->
<div class="ov" id="setSh" onclick="closeSheet('setSh')">
 <div class="sheet" onclick="event.stopPropagation()">
  <div class="handle"></div>
  <div class="sh-title" id="setTitle">Settings</div>
  <div id="setBody"></div>
  <button class="shbtn" onclick="saveSet()">Save</button>
  <button class="shbtn shbtn2" onclick="closeSheet('setSh')">Cancel</button>
 </div>
</div>

<!-- Emergency -->
<div class="ov" id="emergSh" onclick="closeSheet('emergSh')">
 <div class="sheet" onclick="event.stopPropagation()">
  <div class="handle"></div>
  <div class="sh-title">🆘 Emergency</div>
  <div style="background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.25);border-radius:16px;padding:18px;font-size:14px;line-height:2.2;font-family:var(--mono)">
    <b>Emergency</b> — 911 (US) · 999 (UK) · 112 (EU)<br>
    <b>Suicide Line</b> — 988 (US)<br>
    <b>Crisis Text</b> — Text HOME → 741741<br>
    <b>Poison Control</b> — 1-800-222-1222
  </div>
  <div style="text-align:center;font-size:13px;color:var(--t2);margin-top:18px;line-height:1.8">
    You are not alone.<br>Vaishu is always here for you. 💙
  </div>
 </div>
</div>

<script>
'use strict';
let selMood='', setMode='', recog=null, wakeRecog=null;
let listening=false, wakeOn=false, assistantOpen=false;
const synth=window.speechSynthesis;

// ── BOOT ──────────────────────────────────────────────
async function boot(){
  const s=await fetch('/api/settings').then(r=>r.json()).catch(()=>({}));
  if(!s.name){
    document.getElementById('onboard').style.display='flex';
    return;
  }
  startApp(s.name);
}

async function obDone(){
  const name=document.getElementById('obName').value.trim();
  const key=document.getElementById('obKey').value.trim();
  const lang=document.getElementById('obLang').value;
  if(!name){toast('Enter your name first! ✨');return;}
  await post('/api/settings',{name,api_key:key||undefined,language:lang});
  startApp(name);
}

async function startApp(name){
  document.getElementById('onboard').style.display='none';
  document.getElementById('app').style.display='flex';
  setupSpeech();
  await refreshStatus();
  await loadTasks(); await loadHabits(); await loadProfile();
  const st=await fetch('/api/status').then(r=>r.json());
  addDay('Today');
  addMsg(`Good ${st.tod}, ${name}! 💙\n\nI'm Vaishu — your personal AI companion. Always here.\n\nSay **"Sup Vaishu"** anytime to call me up, log your mood, manage tasks, or just talk. I speak your language. 🌐`,'ai');
  vspeak(`Good ${st.tod} ${name}! Vaishu is here for you.`);
  setInterval(refreshStatus,30000);
}

// ── STATUS ─────────────────────────────────────────────
async function refreshStatus(){
  const s=await fetch('/api/status').then(r=>r.json()).catch(()=>({}));
  if(!s.name) return;
  document.getElementById('sTask').textContent=s.pending||0;
  document.getElementById('sMood').textContent=s.mood||'—';
  document.getElementById('sStrk').textContent=s.streak||0;
  document.getElementById('sTime').textContent=s.time||'—';
  document.getElementById('pName').textContent=s.name;
  document.getElementById('pSub').textContent=s.date;
  const op=document.getElementById('sOvPill');
  if(s.overdue>0){op.style.display='flex';document.getElementById('sOv').textContent=s.overdue;}
  else op.style.display='none';
  const st=document.getElementById('tbStat');
  st.textContent=s.api_set?'Online':'⚠️ Set API key';
  st.parentElement.style.color=s.api_set?'':'#ef4444';
}

// ── CHAT ───────────────────────────────────────────────
function addDay(label){
  const m=document.getElementById('msgs');
  const d=document.createElement('div'); d.className='day-sep'; d.textContent=label;
  m.appendChild(d);
}
function addMsg(text,role){
  const m=document.getElementById('msgs');
  const d=document.createElement('div'); d.className='msg '+role;
  d.innerHTML = role==='ai'
    ? `<div class="av"><span class="lv">V</span></div><div class="bub">${fmt(text)}</div>`
    : `<div class="bub">${fmt(text)}</div>`;
  m.appendChild(d); m.scrollTop=m.scrollHeight;
}
function fmt(t){
  return String(t)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/\*\*(.+?)\*\*/g,'<b>$1</b>')
    .replace(/\*(.+?)\*/g,'<em>$1</em>')
    .replace(/\n/g,'<br>');
}
function showTyp(){
  const m=document.getElementById('msgs');
  const d=document.createElement('div'); d.className='msg ai'; d.id='typ';
  d.innerHTML=`<div class="av"><span class="lv">V</span></div><div class="bub"><div class="typdot"><span></span><span></span><span></span></div></div>`;
  m.appendChild(d); m.scrollTop=m.scrollHeight;
}
function hideTyp(){const t=document.getElementById('typ');if(t)t.remove();}

async function sendMsg(txt=''){
  const inp=document.getElementById('inp');
  const msg=txt||inp.value.trim(); if(!msg) return;
  inp.value=''; autoResize(inp); addMsg(msg,'user'); showTyp();
  const st=document.getElementById('tbStat');
  st.textContent='Thinking...';
  try{
    const r=await post('/api/chat',{message:msg});
    hideTyp(); addMsg(r.reply,'ai'); vspeak(r.reply); refreshStatus();
  }catch(e){hideTyp();addMsg('⚠️ Connection error.','ai');}
  st.textContent='Online';
}
function onKey(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMsg();}}
function autoResize(el){el.style.height='auto';el.style.height=Math.min(el.scrollHeight,100)+'px';}

// ── VOICE ──────────────────────────────────────────────
function setupSpeech(){
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR) return;
  recog=new SR(); recog.lang=''; recog.continuous=false; recog.interimResults=false;
  recog.onresult=e=>{
    const t=e.results[0][0].transcript;
    stopListen();
    if(assistantOpen){
      closeAssistant(); goTo('chat'); sendMsg(t);
    } else {
      sendMsg(t);
    }
  };
  recog.onend=()=>stopListen(); recog.onerror=()=>stopListen();
}

function toggleMic(){listening?stopListen():startListen();}
function startListen(overlay=false){
  if(!recog){toast('Voice not supported in this browser'); return;}
  try{ recog.start(); }catch(e){ return; }
  listening=true;
  if(!overlay){
    const b=document.getElementById('micBtn'); b.classList.add('on'); b.textContent='🔴';
    document.getElementById('tbStat').textContent='🎤 Listening...';
  }
}
function stopListen(){
  listening=false; try{recog&&recog.stop();}catch(e){}
  const b=document.getElementById('micBtn'); b.classList.remove('on'); b.textContent='🎤';
  const st=document.getElementById('tbStat'); if(st.textContent.includes('Listening')) st.textContent='Online';
}

// ── WAKE WORD ──────────────────────────────────────────
function toggleWake(){
  wakeOn=!wakeOn;
  const btn=document.getElementById('wakeBtn');
  const badge=document.getElementById('wakeBadge');
  if(wakeOn){
    btn.classList.add('on'); badge.classList.add('on');
    startWakeListener();
    toast('Wake mode ON — say "Sup Vaishu"');
  } else {
    btn.classList.remove('on'); badge.classList.remove('on');
    stopWakeListener(); toast('Wake mode OFF');
  }
}
function startWakeListener(){
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){toast('Voice not supported');return;}
  wakeRecog=new SR();
  wakeRecog.continuous=true; wakeRecog.interimResults=true; wakeRecog.lang='';
  wakeRecog.onresult=e=>{
    const txt=Array.from(e.results).map(r=>r[0].transcript).join(' ').toLowerCase();
    if(txt.includes('sup vaishu')||txt.includes('hey vaishu')||txt.includes('vaishu')){
      stopWakeListener();
      wakeOn=false;
      document.getElementById('wakeBtn').classList.remove('on');
      document.getElementById('wakeBadge').classList.remove('on');
      openAssistant();
    }
  };
  wakeRecog.onend=()=>{if(wakeOn) try{wakeRecog.start();}catch(e){}};
  try{wakeRecog.start();}catch(e){}
}
function stopWakeListener(){try{wakeRecog&&wakeRecog.stop();}catch(e){} wakeRecog=null;}

// ── ASSISTANT OVERLAY (Google Assistant style) ─────────
function openAssistant(){
  assistantOpen=true;
  const ov=document.getElementById('assistantOverlay');
  ov.classList.add('on');
  const waves=document.getElementById('aoWaves');
  const aoText=document.getElementById('aoText');
  const aoSub=document.getElementById('aoSub');
  const aoTr=document.getElementById('aoTranscript');
  aoText.textContent="Hey, it's Vaishu!";
  aoSub.textContent='Listening...';
  aoTr.textContent='';
  waves.classList.remove('idle');

  // Start listening with interim transcript
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){closeAssistant();return;}
  const ar=new SR(); ar.lang=''; ar.continuous=false; ar.interimResults=true;
  ar.onresult=e=>{
    let interim='';
    for(let i=0;i<e.results.length;i++){
      if(e.results[i].isFinal){
        const t=e.results[i][0].transcript;
        aoTr.textContent=t;
        waves.classList.add('idle');
        aoText.textContent='Got it!';
        aoSub.textContent='Thinking...';
        setTimeout(()=>{
          closeAssistant(); goTo('chat'); sendMsg(t);
        },600);
      } else {
        interim+=e.results[i][0].transcript;
        aoTr.textContent=interim;
      }
    }
  };
  ar.onend=()=>{
    if(assistantOpen){waves.classList.add('idle');aoSub.textContent="Didn't catch that. Try again.";}
  };
  ar.onerror=()=>{
    waves.classList.add('idle');aoSub.textContent="Mic error. Check permissions.";
  };
  try{ar.start();}catch(e){closeAssistant();}
  document.getElementById('assistantOverlay')._ar=ar;

  vspeak("I'm listening");
}
function closeAssistant(){
  assistantOpen=false;
  try{document.getElementById('assistantOverlay')._ar&&document.getElementById('assistantOverlay')._ar.stop();}catch(e){}
  document.getElementById('assistantOverlay').classList.remove('on');
  document.getElementById('aoWaves').classList.add('idle');
}

function vspeak(text){
  if(!synth) return; synth.cancel();
  const clean=text.replace(/<[^>]+>/g,' ').replace(/[*_`#]/g,'').replace(/\s+/g,' ').trim().substring(0,500);
  if(!clean) return;
  const u=new SpeechSynthesisUtterance(clean); u.rate=1.0; u.pitch=1.05;
  const vs=synth.getVoices();
  const fv=vs.find(v=>/Samantha|Zira|Google UK English Female|Female/i.test(v.name));
  if(fv) u.voice=fv;
  synth.speak(u);
}

// ── NAVIGATION ──────────────────────────────────────────
function goTo(name){
  document.querySelectorAll('.screen').forEach(s=>s.classList.remove('on'));
  document.querySelectorAll('.nb').forEach(b=>b.classList.remove('on'));
  document.getElementById(name+'Screen').classList.add('on');
  const nb=document.getElementById('nb-'+name);
  if(nb) nb.classList.add('on');
  document.getElementById('ibar').style.display=name==='chat'?'flex':'none';
  document.getElementById('fab').className='fab'+(name==='tasks'?' show':'');
  if(name==='tasks') loadTasks();
  if(name==='habits') loadHabits();
  if(name==='profile') loadProfile();
}

// ── TASKS ────────────────────────────────────────────────
async function loadTasks(){
  const tasks=await fetch('/api/tasks').then(r=>r.json());
  const l=document.getElementById('taskList');
  if(!tasks.length){
    l.innerHTML='<div style="text-align:center;color:var(--t2);padding:50px 20px;font-size:14px;font-family:var(--mono)">No tasks yet.<br><br>Tap <b style="color:var(--a3)">＋</b> or tell Vaishu in chat.</div>';
    return;
  }
  const bc={high:'bh',medium:'bm',low:'bl'};
  l.innerHTML=tasks.map(t=>`
    <div class="tcard${t.done?' done':''}">
      <div class="tchk${t.done?' done':''}" onclick="doneTask(${t.id})">${t.done?'✓':''}</div>
      <div class="tinfo">
        <div class="ttitle${t.done?' done':''}">${esc(t.title)}</div>
        <div class="tmeta${t.overdue?' ov':''}">
          <span class="badge ${bc[t.priority]||'bm'}">${t.priority}</span>
          ${t.overdue?'⚠️ Overdue':''}
        </div>
      </div>
      <span class="tdel" onclick="delTask(${t.id})">🗑</span>
    </div>`).join('');
}
async function doneTask(id){await fetch(`/api/tasks/${id}/done`,{method:'POST'});loadTasks();refreshStatus();toast('✅ Done!');}
async function delTask(id){await fetch(`/api/tasks/${id}`,{method:'DELETE'});loadTasks();refreshStatus();toast('Deleted');}
async function addTask(){
  const title=document.getElementById('tName').value.trim();
  const pri=document.getElementById('tPri').value;
  if(!title){toast('Enter a task name!');return;}
  await post('/api/tasks',{title,priority:pri});
  document.getElementById('tName').value='';
  closeSheet('addSh'); loadTasks(); refreshStatus(); toast('✅ Task added!');
}

// ── HABITS ───────────────────────────────────────────────
async function loadHabits(){
  const habits=await fetch('/api/habits').then(r=>r.json());
  document.getElementById('habitList').innerHTML=habits.map(h=>`
    <div class="hcard${h.done_today?' done':''}" onclick="doneHabit(${h.id})">
      <div class="hemoji">${h.emoji}</div>
      <div class="hinfo">
        <div class="hname">${esc(h.name)}</div>
        <div class="hstreak">Streak: <b>${h.streak} days 🔥</b></div>
      </div>
      <div class="hbox">${h.done_today?'✅':'⬜'}</div>
    </div>`).join('');
}
async function doneHabit(id){
  const r=await fetch(`/api/habits/${id}/done`,{method:'POST'}).then(r=>r.json());
  loadHabits(); toast(`🔥 Streak: ${r.streak} days!`);
}

// ── MOOD ─────────────────────────────────────────────────
function openMoodSheet(){
  selMood='';
  document.querySelectorAll('.mi').forEach(m=>m.classList.remove('sel'));
  document.getElementById('mNote').value='';
  document.getElementById('mBtn').disabled=true;
  openSheet('moodSh');
}
function pickM(mood,el){
  selMood=mood;
  document.querySelectorAll('.mi').forEach(m=>m.classList.remove('sel'));
  el.classList.add('sel');
  document.getElementById('mBtn').disabled=false;
}
async function submitMood(){
  if(!selMood) return;
  const note=document.getElementById('mNote').value.trim();
  await post('/api/mood',{mood:selMood,note});
  closeSheet('moodSh'); refreshStatus(); toast('Mood logged 💙');
  goTo('chat'); await sendMsg(`I'm feeling ${selMood}${note?' — '+note:''}`);
}

// ── PROFILE ──────────────────────────────────────────────
async function loadProfile(){
  const s=await fetch('/api/settings').then(r=>r.json());
  document.getElementById('pName').textContent=s.name||'Friend';
  document.getElementById('pvName').textContent=s.name||'—';
  document.getElementById('pvKey').textContent=s.has_key?'✅ API key set':'⚠️ Tap to add key';
  document.getElementById('pvSched').textContent=`Wake ${s.wake_time||'—'} · Sleep ${s.sleep_time||'—'}`;
  const langMap={auto:'Auto-detect',en:'English',hi:'Hindi',es:'Spanish',fr:'French',de:'German',zh:'Chinese',ja:'Japanese',ar:'Arabic',pt:'Portuguese',ru:'Russian',ko:'Korean',it:'Italian',tr:'Turkish',bn:'Bengali',ur:'Urdu'};
  document.getElementById('pvLang').textContent=langMap[s.language||'auto']||s.language||'Auto-detect';
}

let setMode='';
function openSet(mode){
  setMode=mode;
  const titles={name:'Change Name',key:'API Key',lang:'Language',sched:'Schedule'};
  document.getElementById('setTitle').textContent=titles[mode]||'Settings';
  let html='';
  if(mode==='name')
    html=`<div class="fg"><label class="fl">Your Name</label><input class="fi" id="sv1" placeholder="Your name"/></div>`;
  else if(mode==='key')
    html=`<div class="fg"><label class="fl">Anthropic API Key</label>
      <input class="fi" id="sv1" placeholder="sk-ant-..." autocomplete="off" spellcheck="false"/>
      <div style="font-size:11px;color:var(--t2);margin-top:8px;font-family:var(--mono)">
        Get free key → <a href="https://console.anthropic.com" target="_blank">console.anthropic.com</a>
      </div></div>`;
  else if(mode==='lang')
    html=`<div class="fg"><label class="fl">Language</label>
      <select class="fi" id="sv1">
        <option value="auto">Auto-detect</option>
        <option value="en">English</option>
        <option value="hi">Hindi / हिन्दी</option>
        <option value="es">Spanish / Español</option>
        <option value="fr">French / Français</option>
        <option value="de">German / Deutsch</option>
        <option value="zh">Chinese / 中文</option>
        <option value="ja">Japanese / 日本語</option>
        <option value="ar">Arabic / العربية</option>
        <option value="pt">Portuguese / Português</option>
        <option value="ru">Russian / Русский</option>
        <option value="ko">Korean / 한국어</option>
        <option value="it">Italian / Italiano</option>
        <option value="tr">Turkish / Türkçe</option>
        <option value="bn">Bengali / বাংলা</option>
        <option value="ur">Urdu / اردو</option>
      </select></div>`;
  else if(mode==='sched')
    html=`<div class="fg"><label class="fl">Wake-up Time</label><input class="fi" id="sv1" type="time" value="07:00"/></div>
      <div class="fg"><label class="fl">Bedtime</label><input class="fi" id="sv2" type="time" value="23:00"/></div>`;
  document.getElementById('setBody').innerHTML=html;
  openSheet('setSh');
}
async function saveSet(){
  const body={};
  if(setMode==='name'){const v=document.getElementById('sv1').value.trim();if(v)body.name=v;}
  else if(setMode==='key'){const v=document.getElementById('sv1').value.trim();if(v)body.api_key=v;}
  else if(setMode==='lang'){body.language=document.getElementById('sv1').value;}
  else if(setMode==='sched'){body.wake_time=document.getElementById('sv1').value;body.sleep_time=document.getElementById('sv2').value;}
  await post('/api/settings',body); closeSheet('setSh'); loadProfile(); refreshStatus(); toast('✅ Saved!');
}
async function clearMem(){
  await post('/api/chat',{message:'__clear__'});
  document.getElementById('msgs').innerHTML='';
  addDay('Today'); addMsg('Memory cleared. Fresh start! 💙','ai');
  toast('Memory cleared');
}

// ── UTILS ─────────────────────────────────────────────────
function openSheet(id){document.getElementById(id).classList.add('on');}
function closeSheet(id){document.getElementById(id).classList.remove('on');}
function esc(t){return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function toast(msg){
  document.querySelectorAll('.toast').forEach(t=>t.remove());
  const t=document.createElement('div'); t.className='toast'; t.textContent=msg;
  document.body.appendChild(t); setTimeout(()=>t.remove(),2500);
}
async function post(url,data){
  const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  return r.json();
}

window.addEventListener('DOMContentLoaded',boot);
window.speechSynthesis.onvoiceschanged=()=>{};
</script>
</body>
</html>"""

if __name__=="__main__":
    try: ip=socket.gethostbyname(socket.gethostname())
    except: ip="127.0.0.1"
    print("\n"+"═"*52)
    print("  Vz  VAISHU AI  —  Starting up...")
    print("═"*52)
    print(f"  Open in your browser:")
    print(f"  ➜  http://127.0.0.1:5000")
    print(f"  ➜  http://{ip}:5000  (other devices on WiFi)")
    print()
    if API_KEY:
        print(f"  ✅  API key pre-loaded!")
    else:
        print(f"  ⚠️   No API key — set one in Profile tab")
    print()
    print(f"  💡  Say 'Sup Vaishu' to activate voice mode")
    print(f"  📱  Add to Home Screen for app-like experience")
    print("═"*52+"\n")
    app.run(host="0.0.0.0",port=5000,debug=False)
