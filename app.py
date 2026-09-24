from flask import Flask, render_template_string, request, redirect, session, Response
from markupsafe import Markup
from datetime import date, datetime, timedelta
import json, os, urllib.parse, csv
from io import StringIO
from functools import wraps
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import pytz

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', "motiz_secret_key_2026_v33")
app.config['PROPAGATE_EXCEPTIONS'] = True
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL: raise Exception("DATABASE_URL not set")
if DATABASE_URL.startswith("postgres://"): DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
engine = sa.create_engine(DATABASE_URL)
DBSession = sessionmaker(bind=engine)

PALMPAY_ACCOUNT = "8908025244"
PALMPAY_NAME = "HAMZAT KOLADE AJIMOTI"
PALMPAY_BANK = "PALMPAY"
LESSON_PRICE = 1000
QUESTION_PRICE = 500
ADMIN_PASS = os.environ.get('ADMIN_PASS', "24434")
FREE_Q = 10
PAID_Q = 90
BATCH_SIZE = 10
NIGERIA_TZ = pytz.timezone('Africa/Lagos')
FAVICON_URL = "https://i.imgur.com/5TCBgkN.png"
SEND_BTN_URL = "https://i.imgur.com/ADGwy5l.png"
BASE_URL = "https://motiz-e-learning-institution.onrender.com"
FIXED_AD_KEY = "f0869e31689755e244912b438511f4a9"
AD_REFRESH_MAIN = 60
FRIENDS_BATCH = 5
TICK_SENT = "✓ Sent"
TICK_DELIVERED = "✓✓ Delivered"
TICK_SEEN = "✓✓ Seen"
CALC_SUBJECTS = ["Mathematics", "Physics", "Chemistry", "Further Mathematics", "Financial Accounting", "Economics", "Biology", "Basic Science", "Basic Technology"]
MOTIZ_PROTECTED = ['motiz_support']

JSS_SUBJECTS = ["English Language", "Mathematics", "Basic Science", "Basic Technology", "Social Studies", "Civic Education", "Business Studies", "Agricultural Science", "Christian Religious Studies (CRS)", "Islamic Religious Studies (IRS)", "Physical and Health Education (PHE)"]
CLASSES = ["JSS1", "JSS2", "JSS3", "SS1", "SS2", "SS3"]
SUBJECTS = {
    "JSS1": JSS_SUBJECTS, "JSS2": JSS_SUBJECTS, "JSS3": JSS_SUBJECTS,
    "SS1_Science": ["English Language", "Mathematics", "Civic Education", "Physics", "Chemistry", "Biology", "Further Mathematics", "ICT", "Agricultural Science", "Geography"],
    "SS1_Commercial": ["English Language", "Mathematics", "Civic Education", "Economics", "Financial Accounting", "Commerce", "Business Management", "Government", "Computer Studies / ICT", "Marketing"],
    "SS1_Art": ["English Language", "Mathematics", "Civic Education", "Literature in English", "Government", "Christian Religious Studies (CRS)", "Islamic Religious Studies (IRS)", "Yoruba", "Economics", "Computer Studies / ICT", "Craft"],
    "SS2_Science": ["English Language", "Mathematics", "Civic Education", "Physics", "Chemistry", "Biology", "Further Mathematics", "ICT", "Agricultural Science", "Geography"],
    "SS2_Commercial": ["English Language", "Mathematics", "Civic Education", "Economics", "Financial Accounting", "Commerce", "Business Management", "History", "Computer Studies / ICT", "Marketing"],
    "SS2_Art": ["English Language", "Mathematics", "Civic Education", "Literature in English", "Government", "Christian Religious Studies (CRS)", "Islamic Religious Studies (IRS)", "Yoruba", "Economics", "Computer Studies / ICT", "Craft"],
    "SS3_Science": ["English Language", "Mathematics", "Civic Education", "Physics", "Chemistry", "Biology", "Further Mathematics", "ICT", "Agricultural Science", "Geography"],
    "SS3_Commercial": ["English Language", "Mathematics", "Civic Education", "Economics", "Financial Accounting", "Commerce", "Business Management", "Government", "Computer Studies / ICT", "Marketing"],
    "SS3_Art": ["English Language", "Mathematics", "Civic Education", "Literature in English", "Government", "Christian Religious Studies (CRS)", "Islamic Religious Studies (IRS)", "Yoruba", "Economics", "Computer Studies / ICT", "Craft"]
}
ADMIN_LEVELS = {"jss1": ["JSS1"], "jss2": ["JSS2"], "jss3": ["JSS3"], "sss1": ["SS1_Science","SS1_Commercial","SS1_Art"], "sss2": ["SS2_Science","SS2_Commercial","SS2_Art"], "sss3": ["SS3_Science","SS3_Commercial","SS3_Art"]}
SUBJECT_EMOJI = {"Mathematics":"📐","Further Mathematics":"📏","Physics":"⚛️","Chemistry":"🧑‍🔬","Biology":"🧬","English Language":"📝","Economics":"📊","Financial Accounting":"💰","Commerce":"🏪","Business Management":"📈","Literature in English":"📚","Government":"🏛️","Christian Religious Studies":"✝️","Christian Religious Studies (CRS)":"✝️","Islamic Religious Studies":"☪️","Islamic Religious Studies (IRS)":"☪️","Yoruba":"🗣️","ICT":"💻","Computer Studies / ICT":"💻","Agricultural Science":"🌾","Geography":"🌍","Basic Science":"🔬","Basic Technology":"🔧","Social Studies":"🌐","Civic Education":"⚖️","Business Studies":"💼","Physical and Health Education":"⚽","Marketing":"📢","History":"📜","Craft":"🎨"}
def subj_emoji(s):
    for k,v in SUBJECT_EMOJI.items():
        if k.lower() in s.lower() or s.lower() in k.lower(): return v
    return "📖"

def init_db():
    with engine.connect() as conn:
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, nickname TEXT UNIQUE, name TEXT, password TEXT, class TEXT, dept TEXT, q_cycle TEXT DEFAULT 'free', q_used INTEGER DEFAULT 0, free_questions_used INTEGER DEFAULT 0, lesson_expiry DATE, correct INTEGER DEFAULT 0, wrong INTEGER DEFAULT 0, friends TEXT DEFAULT '[]', blocked TEXT DEFAULT '[]', referred_by TEXT DEFAULT NULL, referral_count INTEGER DEFAULT 0, free_days INTEGER DEFAULT 0, is_verified BOOLEAN DEFAULT FALSE, payment_verified_date TEXT, last_seen TIMESTAMP, push_sub TEXT DEFAULT '');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS payments (id SERIAL PRIMARY KEY, nickname TEXT, name TEXT, type TEXT, status TEXT, bank_used TEXT, account_name TEXT, date_paid TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS friend_requests (id SERIAL PRIMARY KEY, from_nickname TEXT, to_nickname TEXT, status TEXT DEFAULT 'Pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, nickname TEXT, name TEXT, text TEXT, likes TEXT DEFAULT '[]', comments TEXT DEFAULT '[]', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, bg TEXT DEFAULT '');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS dms (id SERIAL PRIMARY KEY, from_nickname TEXT, to_nickname TEXT, text TEXT, time TEXT, read_by TEXT DEFAULT '[]', delivered_to TEXT DEFAULT '[]');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS groups (id SERIAL PRIMARY KEY, name TEXT, creator TEXT, members TEXT DEFAULT '[]', messages TEXT DEFAULT '[]');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS lessons (id SERIAL PRIMARY KEY, class TEXT, dept TEXT, subject TEXT, title TEXT, notes TEXT, date TEXT, media_link TEXT DEFAULT '');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS questions (id SERIAL PRIMARY KEY, key TEXT, q TEXT, options TEXT, ans TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS referrals (id SERIAL PRIMARY KEY, referrer TEXT, referred TEXT, paid BOOLEAN DEFAULT FALSE, bonus_given BOOLEAN DEFAULT FALSE);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS cbt_progress (id SERIAL PRIMARY KEY, nickname TEXT, subject_key TEXT, used INTEGER DEFAULT 0, UNIQUE(nickname, subject_key));"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS notices (id SERIAL PRIMARY KEY, title TEXT, text TEXT, media_link TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS complaints (id SERIAL PRIMARY KEY, nickname TEXT, name TEXT, text TEXT, reply TEXT DEFAULT '', status TEXT DEFAULT 'Pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS daily_challenge (id SERIAL PRIMARY KEY, day DATE, subject TEXT, q TEXT, options TEXT, ans TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS daily_scores (id SERIAL PRIMARY KEY, nickname TEXT, name TEXT, score INTEGER DEFAULT 0, day DATE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.commit()
init_db()

def fix_old_users():
    with DBSession() as db:
        cols = [("users","free_questions_used","INTEGER DEFAULT 0"),("users","q_used","INTEGER DEFAULT 0"),("users","correct","INTEGER DEFAULT 0"),("users","wrong","INTEGER DEFAULT 0"),("users","referral_count","INTEGER DEFAULT 0"),("users","free_days","INTEGER DEFAULT 0"),("users","friends","TEXT DEFAULT '[]'"),("users","blocked","TEXT DEFAULT '[]'"),("users","referred_by","TEXT"),("users","payment_verified_date","TEXT"),("users","lesson_expiry","DATE"),("users","is_verified","BOOLEAN DEFAULT FALSE"),("users","last_seen","TIMESTAMP"),("users","push_sub","TEXT DEFAULT ''"),("dms","delivered_to","TEXT DEFAULT '[]'"),("lessons","media_link","TEXT DEFAULT ''"),("posts","bg","TEXT DEFAULT ''")]
        for table,col,typ in cols:
            try: db.execute(sa.text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {typ}")); db.commit()
            except: db.rollback()
fix_old_users()

def ensure_motiz_support():
    with DBSession() as db:
        exists = db.execute(sa.text("SELECT nickname FROM users WHERE nickname='motiz_support'")).scalar()
        if not exists:
            db.execute(sa.text("INSERT INTO users (nickname,name,password,class,dept,friends,is_verified,last_seen) VALUES ('motiz_support','MOTIZ SUPPORT','motiz_support_2026','SS3','Science','[]',TRUE,NOW()) ON CONFLICT (nickname) DO NOTHING")); db.commit()
        all_users = db.execute(sa.text("SELECT nickname, friends FROM users WHERE nickname!='motiz_support'")).mappings().all()
        for u in all_users:
            try:
                fr = json.loads(u['friends'] or '[]')
                if 'motiz_support' not in fr:
                    fr.append('motiz_support')
                    db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(fr), "u": u['nickname']})
            except: pass
        db.commit()
        all_nicks = db.execute(sa.text("SELECT nickname FROM users WHERE nickname!='motiz_support'")).scalars().all()
        db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname='motiz_support'"), {"f": json.dumps(all_nicks)}); db.commit()
ensure_motiz_support()

def get_setting(k, d=""):
    with DBSession() as db:
        v = db.execute(sa.text("SELECT value FROM settings WHERE key=:k"), {"k": k}).scalar()
        return v if v is not None else d
def set_setting(k, v):
    with DBSession() as db:
        db.execute(sa.text("INSERT INTO settings (key, value) VALUES (:k, :v) ON CONFLICT (key) DO UPDATE SET value=:v"), {"k": k, "v": v}); db.commit()
ADMIN_PASS = get_setting("admin_pass", ADMIN_PASS)
NOTICES = json.loads(get_setting("notices", json.dumps([{"title":"Welcome","text":"Welcome to MOTIZ E-LEARNING!","created_at": str(datetime.now(pytz.timezone('Africa/Lagos'))), "media_link": ""}])))
PINNED_NOTICE = get_setting("pinned_notice", "")

def get_user():
    nickname = session.get("nickname")
    if not nickname: return None, None
    with DBSession() as db:
        user = db.execute(sa.text("SELECT * FROM users WHERE nickname=:u"), {"u": nickname}).mappings().first()
        if user:
            user = dict(user)
            user['friends'] = json.loads(user.get('friends', '[]') or '[]')
            user['blocked'] = json.loads(user.get('blocked', '[]') or '[]')
        return nickname, user

def delete_old_posts_and_notices():
    global NOTICES
    cutoff = datetime.now(pytz.timezone('Africa/Lagos')) - timedelta(hours=24)
    with DBSession() as db: db.execute(sa.text("DELETE FROM posts WHERE created_at < :c"), {"c": cutoff}); db.commit()
    new_notices = []
    for n in NOTICES:
        try:
            notice_time = datetime.fromisoformat(n.get('created_at').replace('Z','+00:00'))
            if notice_time > cutoff: new_notices.append(n)
        except: new_notices.append(n)
    if len(new_notices)!= len(NOTICES): NOTICES = new_notices; set_setting("notices", json.dumps(NOTICES))

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        nickname, user = get_user()
        if not user: return redirect("/login")
        delete_old_posts_and_notices()
        return f(nickname, user, *args, **kwargs)
    return wrapper

def format_last_seen(dt):
    if not dt: return "Never"
    try:
        now = datetime.now(pytz.utc) if dt and dt.tzinfo else datetime.now()
        diff = now - dt; secs = diff.total_seconds()
        if secs < 300: return "<span style='color:green;font-weight:bold'>● Online now</span>"
        mins = int(secs // 60)
        if mins < 60: return f"{mins}m ago"
        hours = mins // 60
        if hours < 24: return f"{hours}h ago"
        days = hours // 24
        return f"{days}d ago"
    except: return "Unknown"
def format_12h(time_str):
    try:
        if not time_str: return ""
        s = str(time_str); import re; m = re.search(r'(\d{1,2}):(\d{2})', s)
        if m: h = int(m.group(1)); mm = m.group(2); ampm = "AM" if h < 12 else "PM"; h12 = h % 12; h12 = 12 if h12==0 else h12; return f"{h12}:{mm} {ampm}"
        return s[:16]
    except: return str(time_str)[:16]
def is_user_paid(user):
    if not user.get('is_verified'): return False
    if not user.get('payment_verified_date'): return True
    try: vd = datetime.strptime(user['payment_verified_date'], "%Y-%m-%d").date(); return date.today() <= vd + timedelta(days=30)
    except: return user.get('is_verified', False)
def get_unread_count(nickname):
    with DBSession() as db:
        all_dms = db.execute(sa.text("SELECT read_by FROM dms WHERE to_nickname=:u"), {"u": nickname}).mappings().all()
        count = 0
        for m in all_dms:
            try: rb = json.loads(m['read_by'] or '[]')
            except: rb = []
            if nickname not in rb: count += 1
        return count
def get_unread_per_friend(nickname, friend):
    with DBSession() as db:
        all_dms = db.execute(sa.text("SELECT read_by FROM dms WHERE from_nickname=:f AND to_nickname=:u"), {"f": friend, "u": nickname}).mappings().all()
        c=0
        for m in all_dms:
            try: rb=json.loads(m['read_by'] or '[]')
            except: rb=[]
            if nickname not in rb: c+=1
        return c

BASE = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/png" href="{FAVICON_URL}"><link rel="manifest" href="/manifest.json"><title>{{{{title}}}}</title><style>
:root{{--bg:#f0f2f5;--card:white;--text:#333;--primary:#0f3460}} body{{font-family:Segoe UI;background:var(--bg);color:var(--text);margin:0;padding:0;padding-bottom:90px}}
body.dark{{--bg:#121212;--card:#1e1e1e;--text:#eee}}
.header{{background:var(--primary);color:white;padding:6px 10px;text-align:center;position:fixed;top:0;width:100%;z-index:1000;display:flex;justify-content:space-between;align-items:center;height:70px}}
.header h1{{margin:0;font-size:0.80rem;flex:1;text-align:center;color:white!important;display:flex;align-items:center;justify-content:center;gap:6px}}
.header img.logo{{width:75px!important;height:75px!important;border-radius:50%}}
.theme-btn{{border:none;background:transparent;color:white;font-size:1.2rem;cursor:pointer}}
.exit-btn{{background:transparent;color:white;border:none;padding:5px 10px;font-size:1.3rem;cursor:pointer}}
.nav{{display:flex;gap:5px;background:#16213e;padding:6px 5px;flex-wrap:wrap;position:fixed;top:70px;width:100%;z-index:999}}
.nav a{{color:white!important;text-decoration:none;padding:5px 8px;border-radius:10px;border:1px solid #fff3;font-size:0.8rem}}
.container{{padding:10px;padding-top:145px;padding-bottom:90px}}
.card{{background:var(--card);padding:12px;margin:8px 0;border-radius:10px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}}
.card:last-child{{margin-bottom:90px!important}}
.btn{{background:#28a745;color:white!important;padding:10px;display:block;margin:8px auto;text-align:center;font-weight:bold;border:none;width:95%;max-width:350px;border-radius:8px;cursor:pointer}}
.btn.red{{background:#e94560!important}}.btn.blue{{background:#0f3460!important;border:1px solid white}}.btn.orange{{background:#ff9800!important}}.btn.gray{{background:#555!important}}
input:not([type=radio]),select,textarea{{width:100%;padding:10px;margin:5px 0;border-radius:5px;border:1px solid #ccc;box-sizing:border-box;background:var(--card);color:var(--text)}}
.option{{background:#f0f2f5;padding:14px 16px;margin:10px 0;border-radius:10px;color:black;display:flex;gap:14px;align-items:center;cursor:pointer;border:1px solid #dee2e6}}
.option input[type=radio]{{width:20px!important;height:20px!important;flex-shrink:0;accent-color:#0f3460}}
.option:has(input:checked){{background:#0f3460!important;color:white!important}}
.badge{{background:#1DA1F2;color:white;padding:3px 8px;border-radius:10px;font-size:0.7rem}}.badge.gold{{background:gold;color:#0f3460;font-weight:bold}}.badge.verified-paid{{background:#28a745;color:white}}
.chat-msg{{display:flex;margin:8px 0;gap:8px}}.chat-msg.me{{justify-content:flex-end}}.chat-msg.other{{justify-content:flex-start}}
.bubble{{padding:10px 14px;border-radius:18px;max-width:70%}}.me.bubble{{background:#2196f3!important;color:white!important}}.other.bubble{{background:#e0e0e0;color:#333}}
.friend-card{{display:flex;align-items:center;gap:10px;padding:12px;background:var(--card);border-radius:10px;margin:8px 0;text-decoration:none;color:var(--text)}}
.friend-avatar{{width:45px;height:45px;border-radius:50%;background:var(--primary);color:white;display:flex;align-items:center;justify-content:center;font-weight:bold}}
.readonly-box{{width:100%;padding:12px;background:#eee;border:1px dashed #999;text-align:center}}
.chat-input-fixed{{position:fixed;bottom:62px;left:5px;right:5px;display:flex;flex-direction:column;gap:5px;background:var(--card);padding:8px 10px;border-radius:25px;z-index:999;box-shadow:0 -1px 5px rgba(0,0,0,0.1)}}
.chat-input-fixed input{{flex:1;border-radius:25px!important;padding:12px 15px!important}}
.send-img-btn{{background:transparent;border:none;flex-shrink:0}}.send-img-btn img{{height:42px;width:42px}}
#fixedAdBar{{position:fixed;bottom:0;left:0;width:100%;height:60px;background:white;z-index:99999;border-top:1px solid #ddd;display:flex;justify-content:center;align-items:center}}
.cbt-btn-fix{{display:block;width:95%;max-width:340px;white-space:normal;line-height:1.3;padding:10px;font-size:0.85rem;margin:8px auto}}
.calc-float{{position:fixed;bottom:85px;right:10px;background:#222;color:white;padding:10px;border-radius:10px;z-index:9998;width:240px;display:none;border:2px solid #ff9800}}
.community-bg-post{{padding:30px 15px;text-align:center;border-radius:15px;color:white;font-size:1.4rem;font-weight:bold;min-height:120px;display:flex;align-items:center;justify-content:center}}
.bg-option{{width:35px;height:35px;border-radius:50%;display:inline-block;margin:4px;border:2px solid #fff;cursor:pointer}}
.bg-option.selected{{border:3px solid #0f3460;transform:scale(1.2)}}
.dm-top-actions{{position:fixed;top:82px;left:0;right:0;background:var(--card);padding:6px 10px;display:flex;gap:8px;justify-content:center;z-index:998;border-bottom:1px solid #ddd}}
#cbt_form{{padding-bottom:80px}}
</style></head><body>
{{{{header}}}}<div class="container">{{{{content}}}}</div>
<div id="fixedAdBar"><button onclick="document.getElementById('fixedAdBar').style.display='none'" style="position:absolute;top:2px;right:5px;background:#000;color:#fff;border:none;border-radius:50%;width:20px;height:20px">X</button><div id="adContainer" style="width:728px;max-width:100%;height:60px;display:flex;align-items:center;justify-content:center;"><script>atOptions = {{'key' : '{FIXED_AD_KEY}','format' : 'iframe','height' : 60,'width' : 728,'params' : {{}} }};</script><script src="https://www.highrevenueformat.com/{FIXED_AD_KEY}/invoke.js"></script></div></div>
<div id="calcFloat" class="calc-float"><div style="display:flex;justify-content:space-between"><b>🧮 Calculator</b><button onclick="document.getElementById('calcFloat').style.display='none'" style="background:red;color:white;border:none;border-radius:50%;width:20px">X</button></div><input id="calcDisplay" readonly style="background:#111;color:#0f0;text-align:right"><div style="display:grid;grid-template-columns:repeat(4,1fr);gap:5px;margin-top:5px"><button class="btn gray" onclick="calcPress('7')">7</button><button class="btn gray" onclick="calcPress('8')">8</button><button class="btn gray" onclick="calcPress('9')">9</button><button class="btn orange" onclick="calcPress('/')">/</button><button class="btn gray" onclick="calcPress('4')">4</button><button class="btn gray" onclick="calcPress('5')">5</button><button class="btn gray" onclick="calcPress('6')">6</button><button class="btn orange" onclick="calcPress('*')">*</button><button class="btn gray" onclick="calcPress('1')">1</button><button class="btn gray" onclick="calcPress('2')">2</button><button class="btn gray" onclick="calcPress('3')">3</button><button class="btn orange" onclick="calcPress('-')">-</button><button class="btn gray" onclick="calcPress('0')">0</button><button class="btn gray" onclick="calcPress('.')">.</button><button class="btn blue" onclick="calcEval()">=</button><button class="btn orange" onclick="calcPress('+')">+</button><button class="btn red" onclick="calcClear()" style="grid-column:span 4">Clear</button></div></div>
<button id="calcBtn" onclick="document.getElementById('calcFloat').style.display='block'" style="position:fixed;bottom:85px;right:15px;background:#ff9800;color:white;border:none;border-radius:50%;width:55px;height:55px;font-size:1.5rem;z-index:9997;display:none">🧮</button>
<script>
{{{{timer_script}}}}
let mainAdInterval = {AD_REFRESH_MAIN} * 1000;
setInterval(function(){{ let adBar=document.getElementById('fixedAdBar'); if(adBar && adBar.style.display!=='none' &&!document.hidden){{ try{{ let ns=document.createElement('script'); ns.src='https://www.highrevenueformat.com/{FIXED_AD_KEY}/invoke.js'; document.getElementById('adContainer').appendChild(ns); }}catch(e){{}} }} }}, mainAdInterval);
function calcPress(v){{ document.getElementById('calcDisplay').value += v; }}
function calcClear(){{ document.getElementById('calcDisplay').value = ''; }}
function calcEval(){{ try{{ document.getElementById('calcDisplay').value = eval(document.getElementById('calcDisplay').value); }}catch(e){{ document.getElementById('calcDisplay').value='Error'; }} }}
(function(){{ let saved = localStorage.getItem('motiz_theme') || 'dark'; document.body.classList.remove('light','dark'); document.body.classList.add(saved); }})();
function toggleTheme(){{ let isLight = document.body.classList.contains('light'); document.body.classList.remove('light','dark'); if(isLight){{ document.body.classList.add('dark'); localStorage.setItem('motiz_theme','dark'); }} else {{ document.body.classList.add('light'); localStorage.setItem('motiz_theme','light'); }} }}
</script>
</body></html>"""

def get_header(nickname,user, show_nav=True, show_favicon=False, is_home=False):
    if not user: return ""
    exit_html = "" if is_home else f'<button onclick="location.href=\'/main\'" class="exit-btn">⬅️</button>'
    favicon_html = f'<img src="{FAVICON_URL}" class="logo">' if show_favicon else ""
    theme_html = f'<button class="theme-btn" id="themeToggle" onclick="toggleTheme()">🌙</button>'
    unread = get_unread_count(nickname) if nickname!='motiz_support' else 0
    bell = f" 🔔({unread})" if unread>0 else ""
    verified = '<span class=badge gold>✓ MOTIZ SUPPORT</span>' if nickname=='motiz_support' else ('<span class=badge verified-paid>✓ Verified Paid</span>' if is_user_paid(user) else "")
    nav_html = f"""<div class="nav"><a href="/main">🏠 Home</a><a href="/exam">✍️ CBT</a><a href="/daily">🏆 Daily</a><a href="/lessons">🎓 Lessons</a><a href="/community">🌍 Community</a><a href="/chat">💬 Chat{bell}</a><a href="/me">👤 Me</a><a href="/complain">📩 Complain</a></div>""" if show_nav else ""
    return f"""<div class="header">{favicon_html}{exit_html}<h1 style="color:white!important">MOTIZ {verified}</h1>{theme_html}</div>{nav_html}"""

@app.route('/manifest.json')
def manifest():
    return Response(json.dumps({"name":"MOTIZ","short_name":"MOTIZ","start_url":"/main","display":"standalone","background_color":"#0f3460","theme_color":"#0f3460","icons":[{"src":FAVICON_URL,"sizes":"192x192","type":"image/png"}]}), mimetype='application/json')
@app.route('/sw.js')
def sw():
    return Response("self.addEventListener('install', e=>self.skipWaiting());", mimetype='application/javascript')
@app.route('/save-subscription', methods=["POST"])
@login_required
def save_sub(nickname, user):
    try:
        sub = request.get_json()
        with DBSession() as db:
            db.execute(sa.text("UPDATE users SET push_sub=:s WHERE nickname=:u"), {"s": json.dumps(sub), "u": nickname}); db.commit()
        return {"ok": True}
    except: return {"ok": False}
@app.route('/check_unread')
@login_required
def check_unread(nickname, user):
    return Response(json.dumps({"count": get_unread_count(nickname)}), mimetype="application/json")
@app.route('/')
def splash():
    return render_template_string(f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Welcome</title>
<meta http-equiv="refresh" content="3;url=/login">
<style>body{{margin:0;background:linear-gradient(135deg,#0f3460,#16213e);color:white;display:flex;justify-content:center;align-items:center;height:100vh;flex-direction:column}}
#barWrap{{width:80%;max-width:300px;height:6px;background:rgba(255,255,255,0.3);border-radius:10px;margin-top:20px;overflow:hidden}}
#bar{{height:100%;width:0%;background:white;border-radius:10px;transition:width 2.5s linear}}</style>
</head><body>
<div style="font-size:2.2rem;font-weight:bold;text-align:center;line-height:1.2">MOTIZ<br>E-LEARNING<br>INSTITUTION</div>
<div id="barWrap"><div id="bar"></div></div>
<p style="margin-top:15px;opacity:0.8">Loading...</p>
<script>setTimeout(function(){{document.getElementById('bar').style.width='100%';}},100);</script>
</body></html>""")

@app.route('/register', methods=["GET","POST"])
def register():
    if get_user()[1]: return redirect("/main")
    error = ""; ref = request.args.get('ref')
    if request.method == "POST":
        nickname = request.form.get("nickname","").strip().lower()
        if nickname == 'motiz_support': error = "<div class=error>Nickname reserved</div>"
        else:
            with DBSession() as db:
                exists = db.execute(sa.text("SELECT nickname FROM users WHERE nickname=:u"), {"u": nickname}).scalar()
                if exists: error = "<div class=error>Nickname taken</div>"
                else:
                    name = f"{request.form['surname']} {request.form['other']}"
                    db.execute(sa.text("INSERT INTO users (nickname,name,password,class,dept,referred_by,last_seen) VALUES (:u,:n,:p,:c,:d,:r,NOW())"), {"u": nickname, "n": name, "p": request.form['password'], "c": request.form['class'], "d": request.form.get('dept',''), "r": ref})
                    if ref: db.execute(sa.text("INSERT INTO referrals (referrer, referred) VALUES (:r, :ref)"), {"r": ref, "ref": nickname})
                    db.commit()
                    session["nickname"] = nickname; return redirect("/main")
    js = """<script>function d(){let c=document.getElementById('class').value;let x=document.getElementById('deptBox');x.innerHTML='';if(['SS1','SS2','SS3'].includes(c)){x.innerHTML='<label>Department *</label><select name=dept required><option value="">Select Department</option><option>Science</option><option>Commercial</option><option>Art</option></select>'}else{x.innerHTML='<input type=hidden name=dept value=>';}}</script>"""
    form = f"<div class='card'><h2>Register</h2>{error}<form method=POST><input name=nickname placeholder='Nickname' required><input name=surname placeholder='Surname' required><input name=other placeholder='Other Name' required><input type=password name=password placeholder='Password' required><select name=class id=class onchange=d() required><option value=''>Select Class</option>{''.join([f'<option>{c}</option>' for c in CLASSES])}</select><div id=deptBox></div><button class=btn>Register</button><p>Already have account? <a href=/login>Login</a></p></form></div>{js}"
    return render_template_string(BASE, title="Register", header="", content=Markup(form), timer_script="")

@app.route('/login', methods=["GET","POST"])
def login():
    if get_user()[1]: return redirect("/main")
    error = ""
    if request.method == "POST":
        nickname = request.form["nickname"].strip().lower()
        pwd = request.form["password"]
        with DBSession() as db:
            u = db.execute(sa.text("SELECT * FROM users WHERE nickname=:u"), {"u": nickname}).mappings().first()
            if u and u["password"] == pwd: session["nickname"] = nickname; return redirect("/main")
            else: error = "<div class=error>Invalid</div>"
    return render_template_string(BASE, title="Login", header="", content=Markup(f"<div class='card'><h2>Login</h2>{error}<form method=POST><input name=nickname placeholder='Enter your Nickname' required><input type=password name=password placeholder='Enter your Password' required><button class=btn>Login</button><p style='text-align:center;margin-top:10px'>Don't have an account? <a href=/register>Click to Register</a></p></form></div>"), timer_script="")

@app.route('/main')
@login_required
def main(nickname, user):
    with DBSession() as db: db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
    pinned_html = ""
    if PINNED_NOTICE:
        try: pin = json.loads(PINNED_NOTICE); pinned_html = f"<div class='card' style='border:2px solid gold'>📌 {pin['title']}</div>"
        except: pinned_html = f"<div class='card'>{PINNED_NOTICE}</div>"
    notices_html = "".join([f"<div class='card'>📢 {n['title']}<br>{n['text']}</div>" for n in NOTICES])
    return render_template_string(BASE, title="Home", header=Markup(get_header(nickname,user, show_nav=True, show_favicon=True, is_home=True)), content=Markup(f"<div class='card'><h2>Welcome {user['name']}</h2></div>{pinned_html}{notices_html}<a class=btn href=/exam>Start CBT</a>"), timer_script="")

@app.route('/logout')
def logout():
    session.clear(); return redirect("/login")
@app.route('/exam')
@login_required
def exam(nickname, user):
    key = f"{user['class']}_{user['dept']}" if user['dept'] else user['class']
    subs = SUBJECTS.get(key, [])
    if not subs:
        return render_template_string(BASE, title="Error", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup("<div class=error>No subjects for your class yet</div>"), timer_script="")
    if user.get('payment_verified_date'):
        try:
            verified_date = datetime.strptime(user['payment_verified_date'], "%Y-%m-%d").date()
            if date.today() > verified_date + timedelta(days=30):
                with DBSession() as db:
                    db.execute(sa.text("UPDATE users SET is_verified=FALSE, q_cycle='free' WHERE nickname=:u"), {"u": nickname})
                    db.commit()
                user['is_verified'] = False
        except: pass
    sub_btns = ""
    with DBSession() as db:
        for s in subs:
            full_key = f"{key}_{s}"
            prog = db.execute(sa.text("SELECT used FROM cbt_progress WHERE nickname=:u AND subject_key=:k"), {"u": nickname, "k": full_key}).scalar()
            if prog is None: prog = 0
            total_q = db.execute(sa.text("SELECT COUNT(*) FROM questions WHERE key=:k"), {"k": full_key}).scalar() or 0
            limit = FREE_Q if not is_user_paid(user) else FREE_Q + PAID_Q
            done = min(prog, total_q, limit)
            emoji = subj_emoji(s)
            if done >= limit or (total_q>0 and done >= total_q):
                btn = f"<div class='card' style='border:2px solid #28a745'><b>{emoji} {s}</b><br><small>✅ Completed {done}/{min(limit,total_q)}</small><br><a class='btn blue cbt-btn-fix' href='/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(s)}?redo=1'>🔄 Redo / Reset</a></div>"
            else:
                if not is_user_paid(user) and prog >= FREE_Q:
                    btn = f"<div class='card cbt-btn-fix' style='border:2px solid #e94560'><b>{emoji} {s}</b><br><small>🔒 Pay to continue (10/{FREE_Q} free done)</small><br><a class='btn red cbt-btn-fix' href='/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(s)}'>Unlock - Pay ₦{QUESTION_PRICE}</a></div>"
                else:
                    btn = f"<a class='btn blue cbt-btn-fix' href='/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(s)}'><span>{emoji} {s}</span><br><small>{done}/{min(limit,total_q)} done</small></a>"
            sub_btns += btn
    content = f"<div class='card'><h2>Subjects for {user['class']} {user.get('dept','')}</h2>{sub_btns}</div>"
    return render_template_string(BASE, title="CBT", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")

@app.route('/cbt/<path:key>/<path:sub>', methods=["GET","POST"])
@login_required
def cbt_exam(nickname, user, key, sub):
    key = urllib.parse.unquote(key); sub = urllib.parse.unquote(sub)
    full_key = f"{key}_{sub}"
    redo = request.args.get('redo')
    with DBSession() as db:
        if redo:
            db.execute(sa.text("UPDATE cbt_progress SET used=0 WHERE nickname=:u AND subject_key=:k"), {"u": nickname, "k": full_key})
            db.commit()
            return redirect(f"/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(sub)}")
        all_count = db.execute(sa.text("SELECT COUNT(*) FROM questions WHERE key=:k"), {"k": full_key}).scalar() or 0
        if all_count == 0:
            return render_template_string(BASE, title="Error", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>😕 No Questions Yet for {subj_emoji(sub)} {sub}</h2><p>Admin will upload 100 questions</p></div>"), timer_script="")
        prog = db.execute(sa.text("SELECT used FROM cbt_progress WHERE nickname=:u AND subject_key=:k"), {"u": nickname, "k": full_key}).scalar()
        if prog is None:
            db.execute(sa.text("INSERT INTO cbt_progress (nickname, subject_key, used) VALUES (:u, :k, 0) ON CONFLICT (nickname, subject_key) DO NOTHING"), {"u": nickname, "k": full_key})
            db.commit()
            prog = 0
    total_limit = FREE_Q + PAID_Q if is_user_paid(user) else FREE_Q
    if prog >= total_limit or prog >= all_count:
        if not is_user_paid(user) and prog >= FREE_Q:
            with DBSession() as db: pending = db.execute(sa.text("SELECT * FROM payments WHERE nickname=:u AND type='questions' AND status='Pending'"), {"u": nickname}).scalar()
            if pending:
                content = "<div class=card><h2>⏳ Payment Under Review</h2><p>Admin verifying.</p></div>"
            else:
                content = f'<div class=card><h2>🔒 Unlock 90 More for {subj_emoji(sub)} {sub}</h2><p>Total 100 Qs: 10 free + 90 paid</p><p><b>Pay ₦{QUESTION_PRICE} for 30 days</b></p><p><b>Bank:</b> {PALMPAY_BANK}<br><b>Account:</b><input class=readonly-box readonly value="{PALMPAY_ACCOUNT}"><br><b>Name:</b> {PALMPAY_NAME}</p><form method=POST action=/confirm/questions><input name=bank_used placeholder="Bank you used" required><input name=account_name placeholder="Account Name" required><button class=btn>Submit</button></form><a class=btn blue href="/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(sub)}?redo=1">🔄 Redo Free 10</a></div>'
            return render_template_string(BASE, title="Paywall", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")
    start_index = prog
    end_index = min(start_index + BATCH_SIZE, total_limit, all_count)
    with DBSession() as db:
        batch_q = db.execute(sa.text(f"SELECT * FROM questions WHERE key=:k ORDER BY id ASC LIMIT :limit OFFSET :off"), {"k": full_key, "limit": end_index-start_index, "off": start_index}).mappings().all()
    questions = [dict(q) for q in batch_q]
    for q in questions:
        try: q['options'] = json.loads(q['options'])
        except: q['options'] = []
    if not questions:
        return render_template_string(BASE, title="Done", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>✅ Completed {sub}</h2><a class=btn href=/exam>Back to Subjects</a><a class=btn blue href='/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(sub)}?redo=1'>🔄 Redo</a></div>"), timer_script="")
    time_per_q = 60 if sub in CALC_SUBJECTS else 30
    batch_time = len(questions) * time_per_q
    q_html_pages = ""
    for i,q in enumerate(questions):
        opts = "".join([f"<label class=option style='padding:7px 10px!important;margin:5px 0!important;font-size:0.92rem'><input type=radio name=q{i} value=\"{opt}\"><span>{opt}</span></label>" for opt in q["options"]])
        q_html_pages += f"<div class='cbt-q-page' id='qpage-{i}' style='display:{'block' if i==0 else 'none'}'><div class=card style='margin-top:16px!important; padding:10px 12px!important; min-height:30vh!important; display:flex; flex-direction:column; justify-content:flex-start'><p style='margin:4px 0 10px 0; font-size:0.95rem'><b>Q{start_index+i+1}/{end_index}</b> {q['q']}</p>{opts}</div></div>"
    timer_header = f"""
    <div id=cbtTimerHeader style='position:fixed;top:0;left:0;right:0;z-index:10002;background:var(--card);border-bottom:3px solid #0f3460;padding:4px 8px;display:flex;justify-content:space-between;align-items:center;height:42px'>
      <div style='display:flex;gap:8px;align-items:center'>
        <button onclick="location.replace('/exam')" style='background:#e94560;color:white;border:none;width:42px;height:36px;border-radius:8px;font-size:1.2rem;display:flex;align-items:center;justify-content:center'>⬅️</button>
        <button onclick="document.body.classList.toggle('dark');localStorage.setItem('motiz_theme', document.body.classList.contains('dark')?'dark':'light')" style='background:#eee;border:1px solid #ccc;width:42px;height:36px;border-radius:8px;font-size:1.2rem;display:flex;align-items:center;justify-content:center'>🌙</button>
      </div>
      <div id=timerText style='font-weight:bold;color:#0f3460;font-size:1.15rem;background:#fff3;padding:5px 12px;border-radius:8px'>⏰ {batch_time//60}:{batch_time%60:02d}</div>
      <div style='font-size:0.65rem;opacity:0.7'>{subj_emoji(sub)} {sub}</div>
    </div>
    <style>
      body {{ overflow:hidden!important; height:100vh!important; }}
   .container {{ margin-top:46px!important; padding-top:2px!important; height:calc(100vh - 110px)!important; overflow:hidden!important; display:flex; flex-direction:column; }}
      #cbtNavRow {{ position:fixed; bottom:60px; left:0; right:0; z-index:10001; background:var(--card); padding:8px; display:flex; gap:12px; justify-content:center; border-top:2px solid #0f3460; }}
      #cbtNavRow.btn {{ flex:1!important; max-width:165px!important; height:46px!important; font-size:1rem!important; display:flex!important; align-items:center; justify-content:center; margin:0!important; }}
      #fixedAdBar {{ display:flex!important; }}
    </style>
    """
    if request.method == "POST":
        score = 0; result_html = ""
        for i,q in enumerate(questions):
            user_ans = request.form.get(f"q{i}")
            if not user_ans:
                result_html += f"<div class='card' style='border-left:5px solid red'><p><b>Q{start_index+i+1}:</b> {q['q']}</p><p style='color:red'><b>Your:</b> Not Answered</p><p style='color:green'><b>Correct:</b> {q['ans']}</p></div>"
            elif user_ans == q["ans"]:
                score += 1
            else:
                result_html += f"<div class='card' style='border-left:5px solid red'><p><b>Q{start_index+i+1}:</b> {q['q']}</p><p style='color:red'><b>Your:</b> {user_ans}</p><p style='color:green'><b>Correct:</b> {q['ans']}</p></div>"
        total = len(questions); wrong = total - score
        new_done = prog + total
        with DBSession() as db:
            db.execute(sa.text("UPDATE cbt_progress SET used=:u WHERE nickname=:n AND subject_key=:k"), {"u": new_done, "n": nickname, "k": full_key})
            db.execute(sa.text("UPDATE users SET q_used=q_used+:t, correct=correct+:c, wrong=wrong+:w WHERE nickname=:u"), {"t": total, "c": score, "w": wrong, "u": nickname})
            db.commit()
        remaining = min(total_limit, all_count) - new_done
        next_btn = f"<a class=btn href=/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(sub)}>Next 10 - {remaining} left ➡️</a>" if remaining>0 else f"<a class=btn blue href='/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(sub)}?redo=1'>🔄 Redo {sub}</a>"
        content = f"<div class='card' style='text-align:center'><h2>Result {subj_emoji(sub)} {sub}</h2><p><b>Score: {score}/{total}</b></p></div>{next_btn}<a class=btn blue href=/exam>Back</a>{result_html}"
        return render_template_string(BASE, title="Result", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")
    timer_js = Markup(f"""
    var timeLeft = {batch_time};
    var currentQ = 0;
    var totalQ = {len(questions)};
    function showQ(idx){{
      if(idx<0) idx=0;
      if(idx>=totalQ) idx=totalQ-1;
      var pages = document.querySelectorAll('.cbt-q-page');
      for(var i=0;i<pages.length;i++){{ pages[i].style.display = (i===idx? 'block' : 'none'); }}
      currentQ = idx;
      var prevBtn = document.getElementById('prevBtn');
      var nextBtn = document.getElementById('nextBtn');
      if(prevBtn) {{ prevBtn.style.display = 'flex'; prevBtn.style.opacity = idx===0? '0.45' : '1'; }}
      if(nextBtn) {{ nextBtn.innerHTML = idx===totalQ-1? 'SUBMIT ✅' : 'NEXT ➡️'; }}
    }}
    function nextQ(){{ if(currentQ===totalQ-1){{ document.getElementById('cbt_form').submit(); }} else {{ showQ(currentQ+1); }} }}
    function prevQ(){{ if(currentQ>0) showQ(currentQ-1); }}
    function startTimer(){{
      var timerEl = document.getElementById('timerText'); if(!timerEl) return;
      function tick(){{ if(timeLeft <= 0){{ timerEl.innerHTML = '⏰ 0:00 Submitting...'; document.getElementById('cbt_form').submit(); return; }} var m = Math.floor(timeLeft/60); var s = timeLeft%60; timerEl.innerHTML = '⏰ ' + m + ':' + (s<10? '0'+s : s); timeLeft--; }}
      tick(); setInterval(tick, 1000);
    }}
    showQ(0); startTimer();
    var cb=document.getElementById('calcBtn'); if(cb) cb.style.display = '""" + ("block" if sub in CALC_SUBJECTS else "none") + """';
    """)
    nav_html = """
    <div id=cbtNavRow>
      <button type=button id=prevBtn class='btn gray' onclick='prevQ()'>⬅️ PREV</button>
      <button type=button id=nextBtn class='btn' onclick='nextQ()'>NEXT ➡️</button>
    </div>
    """
    content = f"{timer_header}<form method=POST id=cbt_form style='flex:1;display:flex;flex-direction:column'>{q_html_pages}</form>{nav_html}"
    return render_template_string(BASE, title=f"{sub}", header="", content=Markup(content), timer_script=timer_js)

@app.route('/confirm/<t>', methods=["POST"])
@login_required
def confirm(nickname, user, t):
    with DBSession() as db:
        db.execute(sa.text("INSERT INTO payments (nickname, name, type, status, bank_used, account_name, date_paid) VALUES (:u, :n, :t, 'Pending', :b, :a, :d)"),
        {"u": nickname, "n": user["name"], "t": t, "b": request.form["bank_used"], "a": request.form["account_name"], "d": str(date.today())});
        db.commit()
    return render_template_string(BASE, title="Sent", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup("<div class='card'><h2>✅ Request Sent</h2><p>Admin will verify within 24hrs</p></div>"), timer_script="")

@app.route('/lessons')
@login_required
def lessons(nickname, user):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        if user.get('lesson_expiry'):
            try:
                exp = datetime.strptime(str(user['lesson_expiry']), "%Y-%m-%d").date()
                if date.today() > exp:
                    db.execute(sa.text("UPDATE users SET lesson_expiry=NULL WHERE nickname=:u"), {"u": nickname}); db.commit()
                    user['lesson_expiry']=None
            except: pass
        if is_user_paid(user) or user.get('lesson_expiry'):
            all_lessons = db.execute(sa.text("SELECT * FROM lessons WHERE class=:c AND (dept=:d OR dept='' OR dept IS NULL) ORDER BY subject ASC"), {"c": user['class'], "d": user.get('dept','')}).mappings().all()
            if not all_lessons:
                return render_template_string(BASE, title="Lessons", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>🎓 No lessons yet for {user['class']} {user.get('dept','')}</h2></div>"), timer_script="")
            by_subject = {}
            for l in all_lessons:
                if l['subject'] not in by_subject: by_subject[l['subject']] = l
            html = f"<div class=card><h2>🎓 Lessons for {user['class']} {user.get('dept','')} - {len(by_subject)} Subjects</h2></div>"
            for subj, l in by_subject.items():
                media = ""
                if l.get('media_link'):
                    link = l['media_link']
                    if any(x in link.lower() for x in ['.mp4','.webm','video']):
                        media = f"<video src='{link}' controls style='width:100%;border-radius:8px;max-height:300px'></video>"
                    else:
                        media = f"<img src='{link}' style='width:100%;border-radius:8px;max-height:300px'>"
                d12 = format_12h(l['date'])
                html += f"<div class=card style='border-left:5px solid #0f3460'><h3>{subj_emoji(l['subject'])} {l['subject']}</h3><h4>{l['title']}</h4><p>{l['notes']}</p>{media}<small>📅 {d12}</small></div>"
            return render_template_string(BASE, title="Lessons", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html), timer_script="")
        pending = db.execute(sa.text("SELECT * FROM payments WHERE nickname=:u AND type='lessons' AND status='Pending'"), {"u": nickname}).scalar()
        if pending:
            return render_template_string(BASE, title="Lessons", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup("<div class=card><h2>⏳ Payment Under Review</h2></div>"), timer_script="")
    return render_template_string(BASE, title="Pay Lesson", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>🔒 Unlock Lessons - ₦{LESSON_PRICE}/30days</h2><p><b>Bank:</b> {PALMPAY_BANK}<br><b>Acct:</b><input class=readonly-box readonly value={PALMPAY_ACCOUNT}><br><b>Name:</b> {PALMPAY_NAME}</p><form method=POST action=/confirm/lessons><input name=bank_used placeholder='Bank you used' required><input name=account_name placeholder='Account Name' required><button class=btn>Submit</button></form></div>"), timer_script="")

@app.route('/daily', methods=["GET","POST"])
@login_required
def daily_challenge_page(nickname, user):
    today = date.today()
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        todays = db.execute(sa.text("SELECT * FROM daily_challenge WHERE day=:d ORDER BY id ASC LIMIT 10"), {"d": str(today)}).mappings().all()
        leaderboard = db.execute(sa.text("SELECT nickname, name, score FROM daily_scores WHERE day=:d ORDER BY score DESC, created_at ASC LIMIT 10"), {"d": str(today)}).mappings().all()
        leader_html = "<div class=card style='border:2px solid gold'><h3>🏆 Leaderboard Today</h3>"
        if not leaderboard: leader_html += "<p>No scores today yet.</p>"
        else:
            for i, lb in enumerate(leaderboard, 1):
                medal = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}."
                leader_html += f"<p>{medal} <b>{lb['name']}</b> - {lb['score']}/10</p>"
        leader_html += "</div>"
        if not todays:
            return render_template_string(BASE, title="Daily Challenge", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>🏆 Daily Challenge</h2><p>Math, English, Civic - 10 Questions</p></div>{leader_html}"), timer_script="")
        if request.method == "POST":
            score = 0
            for i, q in enumerate(todays):
                ans = request.form.get(f"q{i}")
                if ans == q['ans']: score += 1
            exists = db.execute(sa.text("SELECT id FROM daily_scores WHERE nickname=:u AND day=:d"), {"u": nickname, "d": str(today)}).scalar()
            if exists: db.execute(sa.text("UPDATE daily_scores SET score=:s, created_at=NOW() WHERE nickname=:u AND day=:d"), {"s": score, "u": nickname, "d": str(today)})
            else: db.execute(sa.text("INSERT INTO daily_scores (nickname, name, score, day) VALUES (:u, :n, :s, :d)"), {"u": nickname, "n": user['name'], "s": score, "d": str(today)})
            db.commit()
            return render_template_string(BASE, title="Daily Result", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>🎉 Daily Score: {score}/10</h2></div>{leader_html}"), timer_script="")
        q_html = ""
        for i, q in enumerate(todays):
            try: opts = json.loads(q['options'])
            except: opts = []
            options = "".join([f"<label class=option><input type=radio name=q{i} value=\"{opt}\" required><span>{opt}</span></label>" for opt in opts])
            q_html += f"<div class=card><p><b>Q{i+1} [{q['subject']}]</b> {q['q']}</p>{options}</div>"
        content = f"<div class=card><h2>🏆 Daily Challenge FREE - {today}</h2></div>{leader_html}<form method=POST>{q_html}<button class=btn orange>Submit Daily Challenge</button></form>"
        return render_template_string(BASE, title="Daily Challenge", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")

@app.route('/complain', methods=["GET","POST"])
@login_required
def complain_page(nickname, user):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        if request.method=="POST" and request.form.get("text"):
            cnt = db.execute(sa.text("SELECT COUNT(*) FROM complaints WHERE nickname=:u AND created_at > NOW() - INTERVAL '7 days'"), {"u": nickname}).scalar() or 0
            if cnt >= 3:
                return render_template_string(BASE, title="Complain Limit", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup("<div class=card><div class=error>❌ You don reach limit - 3 complains per week only.</div></div>"), timer_script="")
            db.execute(sa.text("INSERT INTO complaints (nickname, name, text) VALUES (:u,:n,:t)"), {"u": nickname, "n": user["name"], "t": request.form["text"][:700]})
            db.commit()
            return redirect("/complain")
        my = db.execute(sa.text("SELECT * FROM complaints WHERE nickname=:u ORDER BY id DESC LIMIT 20"), {"u": nickname}).mappings().all()
    html = "<div class=card><h2>📩 Complain to Admin (3 per week)</h2><form method=POST><textarea name=text placeholder='Write your complaint...' required maxlength=700></textarea><button class=btn>Send Complaint</button></form></div><h3>My Complaints</h3>"
    for c in my:
        ct12 = format_12h(str(c['created_at']))
        reply = f"<div style='background:#d4edda;padding:8px;margin-top:5px;border-radius:5px'><b>Admin Reply:</b> {c['reply']}</div>" if c['reply'] else "<small>⏳ Pending...</small>"
        html+=f"<div class=card><b>📝 {c['text']}</b><br><small>{ct12} - {c['status']}</small>{reply}</div>"
    return render_template_string(BASE, title="Complain", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html), timer_script="")

@app.route('/community', methods=["GET","POST"])
@login_required
def community(nickname, user):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        del_id = request.args.get('del_post')
        if del_id:
            p = db.execute(sa.text("SELECT nickname FROM posts WHERE id=:i"), {"i": int(del_id)}).scalar()
            if p == nickname or nickname == 'motiz_support':
                db.execute(sa.text("DELETE FROM posts WHERE id=:i"), {"i": int(del_id)}); db.commit()
            return redirect("/community")
        if request.method=="POST" and request.form.get("text"):
            txt = request.form["text"][:700]
            bg = request.form.get("bg","").strip()[:100]
            if nickname!= 'motiz_support' and ('http://' in txt.lower() or 'https://' in txt.lower() or 'www.' in txt.lower()):
                txt = txt.replace('http://','').replace('https://','').replace('www.','')
            db.execute(sa.text("INSERT INTO posts (nickname, name, text, bg) VALUES (:u,:n,:t,:bg)"), {"u": nickname, "n": user["name"], "t": txt, "bg": bg})
            db.commit(); return redirect("/community")
        posts = db.execute(sa.text("SELECT * FROM posts ORDER BY created_at DESC LIMIT 50")).mappings().all()
    bg_options = ["", "linear-gradient(135deg,#ff9a9e,#fecfef)", "linear-gradient(135deg,#a18cd1,#fbc2eb)", "linear-gradient(135deg,#ff6a00,#ee0979)", "linear-gradient(135deg,#667eea,#764ba2)", "linear-gradient(135deg,#f7971e,#ffd200)", "linear-gradient(135deg,#000000,#434343)", "linear-gradient(135deg,#11998e,#38ef7d)", "linear-gradient(135deg,#fc5c7d,#6a82fb)", "linear-gradient(135deg,#0f3460,#e94560)"]
    bg_html = ""
    for b in bg_options:
        if b == "":
            bg_html += f"<div class='bg-option' data-bg='' style='background:white;border:1px solid #ccc' onclick=\"selectBg(this,'')\"></div>"
        else:
            safe_b = b.replace('"', '&quot;')
            bg_html += f"<div class='bg-option' data-bg=\"{safe_b}\" style='background:{b}' onclick=\"selectBg(this, '{b}')\"></div>"
    html = f"""<div class=card>
    <form method=POST id=communityForm>
    <textarea name=text id=communityText placeholder='What is on your mind........' required maxlength=700 oninput="previewBg()"></textarea>
    <input type=hidden name=bg id=selectedBg value=''>
    <div style='margin:8px 0'><small>🎨 Choose background:</small><br>{bg_html}</div>
    <div id=bgPreview style='display:none;margin:8px 0;border-radius:12px;padding:20px;text-align:center;color:white;font-weight:bold;min-height:60px;align-items:center;justify-content:center'></div>
    <button class=btn>Post</button>
    </form>
    <script>
    function selectBg(el, bg){{
        document.querySelectorAll('.bg-option').forEach(x=>x.classList.remove('selected'));
        el.classList.add('selected');
        document.getElementById('selectedBg').value = bg;
        previewBg();
    }}
    function previewBg(){{
        let txt=document.getElementById('communityText').value;
        let bg=document.getElementById('selectedBg').value;
        let prev=document.getElementById('bgPreview');
        if(bg && txt){{ prev.style.display='flex'; prev.style.background=bg; prev.innerText=txt; }}
        else {{ prev.style.display='none'; }}
    }}
    </script>
    </div>"""
    for p in posts:
        try: likes = json.loads(p['likes'] or '[]')
        except: likes=[]
        try: comments = json.loads(p['comments'] or '[]')
        except: comments=[]
        is_motiz = p['nickname']=='motiz_support'
        if is_motiz:
            style = "style='border:3px solid gold;background:linear-gradient(135deg,#fff8e1,#ffe082)'"
            badge_html = " <span class=badge gold>✓ MOTIZ SUPPORT VERIFIED</span>"
        else:
            style = ""
            badge_html = ""
        bg_val = p.get('bg','')
        t12 = format_12h(str(p['created_at']))
        del_btn = f"<a class=btn red href='/community?del_post={p['id']}' onclick=\"return confirm('Delete this post?')\" style='padding:6px;font-size:0.8rem;margin:5px 0;width:90%;max-width:280px'>🗑️ Delete</a>" if (p['nickname']==nickname or nickname=='motiz_support') else ""
        text_html = f"<div class='community-bg-post' style='background:{bg_val}'>{p['text']}</div>" if bg_val else f"<p>{p['text']}</p>"
        html+=f"<div class=card {style}><b>{p['name']}</b>{badge_html}<br><small>{t12}</small>{text_html}{del_btn}<div class=like-row><a class='btn gray' href='/like/{p['id']}' style='flex:1;padding:6px 8px;font-size:0.8rem;margin:0'>👍 Like ({len(likes)})</a><a class='btn gray' href='/post/{p['id']}' style='flex:1;padding:6px 8px;font-size:0.8rem;margin:0'>💬 Comment ({len(comments)})</a></div></div>"
    return render_template_string(BASE, title="Community", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html), timer_script="")

@app.route('/like/<int:pid>')
@login_required
def like_post(nickname, user, pid):
    with DBSession() as db:
        p = db.execute(sa.text("SELECT likes FROM posts WHERE id=:i"), {"i": pid}).scalar()
        if p is not None:
            try: likes=json.loads(p or '[]')
            except: likes=[]
            if nickname in likes: likes.remove(nickname)
            else: likes.append(nickname)
            db.execute(sa.text("UPDATE posts SET likes=:l WHERE id=:i"), {"l": json.dumps(likes), "i": pid}); db.commit()
    return redirect("/community")

@app.route('/post/<int:pid>', methods=["GET","POST"])
@login_required
def post_detail(nickname, user, pid):
    with DBSession() as db:
        p = db.execute(sa.text("SELECT * FROM posts WHERE id=:i"), {"i": pid}).mappings().first()
        if not p: return redirect("/community")
        if request.method=="POST" and request.form.get("comment"):
            try: comments=json.loads(p['comments'] or '[]')
            except: comments=[]
            comments.append({"user": nickname, "name": user["name"], "text": request.form["comment"][:300], "time": str(datetime.now(NIGERIA_TZ))})
            db.execute(sa.text("UPDATE posts SET comments=:c WHERE id=:i"), {"c": json.dumps(comments), "i": pid}); db.commit()
            return redirect(f"/post/{pid}")
        try: comments=json.loads(p['comments'] or '[]')
        except: comments=[]
        bg_val = p.get('bg','')
        t12 = format_12h(str(p['created_at']))
        post_display = f"<div class='community-bg-post' style='background:{bg_val}'>{p['text']}</div>" if bg_val else f"<p>{p['text']}</p>"
        html = f"<div class=card><b>{p['name']}</b><br><small>{t12}</small>{post_display}</div><h3>Comments ({len(comments)})</h3>"
        for c in comments:
            ct12 = format_12h(c.get('time',''))
            html+=f"<div class=card><b>{c['name']}</b><p>{c['text']}</p><small>{ct12}</small></div>"
        html+=f"<div class=card><form method=POST><textarea name=comment placeholder='Add comment' required></textarea><button class=btn>Comment</button></form></div>"
    return render_template_string(BASE, title="Post", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html), timer_script="")

@app.route('/chat')
@login_required
def chat(nickname, user):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        friends = user.get('friends', [])
        blocked = user.get('blocked', [])
        friend_cards = ""
        for f in friends:
            if f in blocked: continue
            if f == 'motiz_support':
                friend_cards+=f"<a href=/dm/{f} class=friend-card style='border:3px solid gold;background:linear-gradient(135deg,#fff8e1,#ffe082)'><div class=friend-avatar style='background:gold;color:#0f3460'>✓</div><div><b>MOTIZ SUPPORT</b> <span class=badge style='background:gold;color:#0f3460;white-space:nowrap'>✓ VERIFIED SUPPORT</span><br><small>Official Support</small></div></a>"
                continue
            u = db.execute(sa.text("SELECT name,last_seen FROM users WHERE nickname=:u"), {"u": f}).mappings().first()
            if u:
                last = format_last_seen(u['last_seen']) if u.get('last_seen') else "Unknown"
                unread = get_unread_per_friend(nickname, f)
                bell = f" <span style='background:red;color:white;padding:2px 6px;border-radius:10px;font-size:0.7rem'>🔔{unread}</span>" if unread>0 else ""
                friend_cards+=f"<a href=/dm/{f} class=friend-card><div class=friend-avatar>{f[0].upper()}</div><div><b>{u['name']}</b>{bell}<br><small>{last}</small></div></a>"
        blocked_html = ""
        for b in blocked:
            if b in MOTIZ_PROTECTED: continue
            blocked_html += f"<div class=friend-card><div class=friend-avatar>🚫</div><div style='flex:1'><b>{b}</b><br><small>Blocked - Tap Unblock to Chat Again</small></div><a class='btn orange' href=/unblock/{b} style='width:auto;padding:6px 12px'>Unblock</a></div>"
        if blocked_html:
            friend_cards += f"<h3>🚫 Blocked Users - Unblock to Continue Chat</h3>{blocked_html}"
        groups = db.execute(sa.text("SELECT * FROM groups")).mappings().all()
        group_html = ""
        for g in groups:
            try: members=json.loads(g['members'] or '[]')
            except: members=[]
            if nickname in members:
                group_html+=f"<a href=/group/{g['id']} class=friend-card><div class=friend-avatar>👥</div><div><b>{g['name']}</b><br><small>{len(members)} members</small></div></a>"
    content = f"<h3>Friends ({len([x for x in friends if x!='motiz_support' and x not in blocked])})</h3>{friend_cards or '<div class=card><p>No friends yet</p><a class=btn blue href=/me>👤 Go to Me to Add Friends</a></div>'}<h3>Groups</h3>{group_html or '<p>No groups</p>'}<a class=btn blue href=/create_group>➕ Create Group</a>"
    return render_template_string(BASE, title="Chat", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")

@app.route('/block/<f>')
@login_required
def block_friend(nickname, user, f):
    if f in MOTIZ_PROTECTED or f == nickname:
        return render_template_string(BASE, title="Protected", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>❌ Cannot block MOTIZ Official Support</h2><p>{f} is protected — you cannot block/unfriend support account.</p><a class=btn href=/chat>Back</a></div>"), timer_script="")
    with DBSession() as db:
        u = db.execute(sa.text("SELECT friends, blocked FROM users WHERE nickname=:u"), {"u": nickname}).mappings().first()
        try: friends = json.loads(u['friends'] or '[]')
        except: friends = []
        try: blocked = json.loads(u['blocked'] or '[]')
        except: blocked = []
        if f in friends: friends.remove(f)
        if f not in blocked: blocked.append(f)
        db.execute(sa.text("UPDATE users SET friends=:f, blocked=:b WHERE nickname=:u"), {"f": json.dumps(friends), "b": json.dumps(blocked), "u": nickname})
        other = db.execute(sa.text("SELECT friends FROM users WHERE nickname=:u"), {"u": f}).mappings().first()
        if other:
            try: of = json.loads(other['friends'] or '[]')
            except: of = []
            if nickname in of: of.remove(nickname)
            db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(of), "u": f})
        db.commit()
    return redirect("/chat")

@app.route('/unblock/<f>')
@login_required
def unblock_friend(nickname, user, f):
    with DBSession() as db:
        u = db.execute(sa.text("SELECT friends, blocked FROM users WHERE nickname=:u"), {"u": nickname}).mappings().first()
        try: blocked = json.loads(u['blocked'] or '[]')
        except: blocked = []
        try: friends = json.loads(u['friends'] or '[]')
        except: friends = []
        if f in blocked: blocked.remove(f)
        if f not in friends: friends.append(f)
        db.execute(sa.text("UPDATE users SET friends=:f, blocked=:b WHERE nickname=:u"), {"f": json.dumps(friends), "b": json.dumps(blocked), "u": nickname})
        db.commit()
    return redirect(f"/dm/{f}")

@app.route('/unfriend/<f>')
@login_required
def unfriend(nickname, user, f):
    if f in MOTIZ_PROTECTED:
        return render_template_string(BASE, title="Protected", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>❌ Cannot unfriend MOTIZ Support</h2><p>Support account is permanent friend.</p><a class=btn href=/chat>Back</a></div>"), timer_script="")
    with DBSession() as db:
        u = db.execute(sa.text("SELECT friends FROM users WHERE nickname=:u"), {"u": nickname}).mappings().first()
        try: friends = json.loads(u['friends'] or '[]')
        except: friends = []
        if f in friends: friends.remove(f)
        db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(friends), "u": nickname})
        other = db.execute(sa.text("SELECT friends FROM users WHERE nickname=:u"), {"u": f}).mappings().first()
        if other:
            try: of = json.loads(other['friends'] or '[]')
            except: of = []
            if nickname in of: of.remove(nickname)
            db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(of), "u": f})
        db.commit()
    return redirect("/chat")

@app.route('/me')
@login_required
def me_page(nickname, user):
    offset = int(request.args.get('offset', 0))
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        reqs = db.execute(sa.text("SELECT * FROM friend_requests WHERE to_nickname=:u AND status='Pending'"), {"u": nickname}).mappings().all()
        req_html = ""
        for r in reqs:
            req_html+=f"<div class=card><b>{r['from_nickname']}</b> sent you friend request<br><div style='display:flex;gap:8px;justify-content:center'><a class=btn blue href=/accept/{r['from_nickname']} style='width:44%;max-width:160px'>✅ Accept</a><a class=btn red href=/reject/{r['from_nickname']} style='width:44%;max-width:160px'>❌ Reject</a></div></div>"
        all_users = db.execute(sa.text("SELECT nickname, name, class, is_verified FROM users WHERE nickname!=:u AND nickname!='motiz_support' ORDER BY RANDOM()"), {"u": nickname}).mappings().all()
        friends = user.get('friends', [])
        blocked = user.get('blocked', [])
        pending_to = [r['to_nickname'] for r in db.execute(sa.text("SELECT to_nickname FROM friend_requests WHERE from_nickname=:u AND status='Pending'"), {"u": nickname}).mappings().all()]
        filtered = [u for u in all_users if u['nickname'] not in friends and u['nickname'] not in blocked and u['nickname'] not in pending_to]
        batch = filtered[offset:offset+FRIENDS_BATCH]
        is_verified_badge = " <span class=badge style='background:#28a745;white-space:nowrap'>✓ Verified Paid</span>" if is_user_paid(user) else ""
        html = f"{req_html}<div class=card style='border:2px solid #28a745'><h2>{user['name']}{is_verified_badge} - {subj_emoji(user['class'])}</h2><p><b>Nickname:</b> {nickname}</p><p><b>Class:</b> {user['class']} {user.get('dept','')}</p><p><b>Referral Link:</b><input class=readonly-box readonly value='{BASE_URL}/register?ref={nickname}'></p><p><b>Referral Bonus:</b> 5 days free per paid referral</p><p><b>Blocked Users:</b> {len(blocked)}</p></div><h3>🔍 Add Friends (Scout 5)</h3>"
        for u in batch:
            html+=f"<div class=friend-card><div class=friend-avatar>{u['nickname'][0].upper()}</div><div style='flex:1'><b>{u['name']}</b><br><small>{u['nickname']} - {u['class']}</small></div><a class=btn blue href=/add_friend/{u['nickname']}?offset={offset} style='width:auto;padding:8px 15px;max-width:80px'>Add</a></div>"
        next_offset = offset + FRIENDS_BATCH
        if next_offset < len(filtered):
            html+=f"<a class='btn orange' href=/me?offset={next_offset}>🔍 Scout - Show Next 5</a>"
        else:
            html+=f"<a class=btn gray href=/me?offset=0>🔄 Scout Again From Start</a>"
        html+=f"<a class=btn red href=/logout style='margin-top:20px'>🚪 Logout</a>"
    return render_template_string(BASE, title="Me", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html), timer_script="")

@app.route('/accept/<f>')
@login_required
def accept_friend(nickname, user, f):
    with DBSession() as db:
        req = db.execute(sa.text("SELECT * FROM friend_requests WHERE from_nickname=:f AND to_nickname=:u AND status='Pending'"), {"f": f, "u": nickname}).mappings().first()
        if req:
            db.execute(sa.text("UPDATE friend_requests SET status='Accepted' WHERE id=:i"), {"i": req['id']})
            u1 = db.execute(sa.text("SELECT friends FROM users WHERE nickname=:u"), {"u": nickname}).scalar()
            u2 = db.execute(sa.text("SELECT friends FROM users WHERE nickname=:u"), {"u": f}).scalar()
            try: f1=json.loads(u1 or '[]')
            except: f1=[]
            try: f2=json.loads(u2 or '[]')
            except: f2=[]
            if f not in f1: f1.append(f)
            if nickname not in f2: f2.append(nickname)
            db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(f1), "u": nickname})
            db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(f2), "u": f})
            db.commit()
    return redirect("/me")

@app.route('/reject/<f>')
@login_required
def reject_friend(nickname, user, f):
    with DBSession() as db:
        db.execute(sa.text("UPDATE friend_requests SET status='Rejected' WHERE from_nickname=:f AND to_nickname=:u AND status='Pending'"), {"f": f, "u": nickname})
        db.commit()
    return redirect("/me")

@app.route('/add_friend/<f>')
@login_required
def add_friend(nickname, user, f):
    if f == nickname or f=='motiz_support': return redirect("/me")
    if f in user.get('blocked', []): return redirect("/me")
    with DBSession() as db:
        if f in user.get('friends', []): return redirect("/me")
        exists = db.execute(sa.text("SELECT * FROM friend_requests WHERE from_nickname=:u AND to_nickname=:f AND status='Pending'"), {"u": nickname, "f": f}).scalar()
        if not exists:
            db.execute(sa.text("INSERT INTO friend_requests (from_nickname, to_nickname) VALUES (:u,:f)"), {"u": nickname, "f": f})
            db.commit()
    return redirect("/me?offset="+request.args.get('offset','0'))

@app.route('/dm/<other>', methods=["GET","POST"])
@login_required
def dm_page(nickname, user, other):
    with DBSession() as db:
        if other in user.get('blocked', []):
            return render_template_string(BASE, title="Blocked", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>🚫 You blocked {other}</h2><p>Unblock from chat page to message again</p><a class=btn orange href=/unblock/{other}>Unblock & Chat Again</a><br><a class=btn href=/chat>Back to Chat</a></div>"), timer_script="")
        other_user = db.execute(sa.text("SELECT * FROM users WHERE nickname=:o"), {"o": other}).mappings().first()
        if not other_user: return redirect("/chat")
        try: other_blocked = json.loads(other_user.get('blocked','[]') or '[]')
        except: other_blocked = []
        if nickname in other_blocked:
            return render_template_string(BASE, title="Blocked", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>🚫 {other} blocked you</h2><p>You cannot send message to this user</p><a class=btn href=/chat>Back to Chat</a></div>"), timer_script="")
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        del_id = request.args.get('del_msg')
        if del_id:
            msg = db.execute(sa.text("SELECT from_nickname FROM dms WHERE id=:i"), {"i": int(del_id)}).scalar()
            if msg == nickname or nickname == 'motiz_support':
                db.execute(sa.text("DELETE FROM dms WHERE id=:i"), {"i": int(del_id)}); db.commit()
            return redirect(f"/dm/{other}")
        all_dms = db.execute(sa.text("SELECT * FROM dms WHERE (from_nickname=:u AND to_nickname=:o) OR (from_nickname=:o AND to_nickname=:u) ORDER BY id ASC"), {"u": nickname, "o": other}).mappings().all()
        for m in all_dms:
            if m['to_nickname']==nickname:
                try: read_by=json.loads(m['read_by'] or '[]')
                except: read_by=[]
                try: delivered=json.loads(m['delivered_to'] or '[]')
                except: delivered=[]
                changed=False
                if nickname not in delivered: delivered.append(nickname); changed=True
                if nickname not in read_by: read_by.append(nickname); changed=True
                if changed:
                    db.execute(sa.text("UPDATE dms SET read_by=:r, delivered_to=:d WHERE id=:i"), {"r": json.dumps(read_by), "d": json.dumps(delivered), "i": m['id']})
        db.commit()
        if request.method=="POST" and request.form.get("text"):
            txt = request.form["text"][:700]
            reply_to = request.form.get("reply_to","")[:200]
            full_text = f"Reply to: {reply_to}\n{txt}" if reply_to else txt
            db.execute(sa.text("INSERT INTO dms (from_nickname, to_nickname, text, time) VALUES (:f,:t,:txt,:tm)"), {"f": nickname, "t": other, "txt": full_text, "tm": str(datetime.now(NIGERIA_TZ))})
            db.commit()
            return redirect(f"/dm/{other}")
        dms = db.execute(sa.text("SELECT * FROM dms WHERE (from_nickname=:u AND to_nickname=:o) OR (from_nickname=:o AND to_nickname=:u) ORDER BY id ASC"), {"u": nickname, "o": other}).mappings().all()

    chat_html = ""
    for m in dms:
        is_me = m['from_nickname']==nickname
        try: read_by=json.loads(m['read_by'] or '[]')
        except: read_by=[]
        try: delivered=json.loads(m['delivered_to'] or '[]')
        except: delivered=[]
        if is_me:
            if m['to_nickname'] in read_by: tick = f"<span class=tick-seen>{TICK_SEEN}</span>"
            elif m['to_nickname'] in delivered: tick = f"<span class=tick-delivered>{TICK_DELIVERED}</span>"
            else: tick = f"<span class=tick-sent>{TICK_SENT}</span>"
        else: tick = ""
        cls = "me" if is_me else "other"
        t12 = format_12h(m['time'])
        text_display = m['text'].replace("\n","<br>")
        if "Reply to:" in m['text']:
            parts = m['text'].split("\n",1)
            text_display = f"<div style='background:rgba(0,0,0,0.1);padding:5px;border-radius:5px;margin-bottom:5px;font-size:0.8rem;border-left:3px solid #0f3460'>{parts[0]}</div>{parts[1] if len(parts)>1 else ''}"
        safe_text = m['text'][:80].replace("'","").replace('"',"").replace("\n"," ")
        chat_html+=f"""<div class='chat-msg {cls}' oncontextmenu="showMenu(event,{m['id']},'{safe_text}'); return false;" onclick="showMenu(event,{m['id']},'{safe_text}')">
        <div class='bubble {cls}' id='msg-{m['id']}'><div class='bubble-text'>{text_display}</div><div class='bubble-time'>{t12} {tick}</div></div></div>"""

    timer_js = Markup(f"""
    setTimeout(()=>{{ window.scrollTo(0, document.body.scrollHeight); }}, 300);
    let exitBtn = document.querySelector('.exit-btn');
    if(exitBtn) exitBtn.setAttribute('onclick', "location.replace('/chat')");
    let lastCount = {len(dms)};
    setInterval(()=>{{
        fetch('/check_dm/{other}').then(r=>r.json()).then(data=>{{
            if(data.count > lastCount){{ location.reload(); }}
        }});
    }}, 3000);
    let replyText = '';
    function showMenu(e, id, text){{
        e.preventDefault();
        let menu = document.getElementById('msgMenu');
        if(!menu){{
            menu = document.createElement('div');
            menu.id='msgMenu';
            menu.style='position:fixed;background:white;border:1px solid #ccc;border-radius:8px;padding:5px;z-index:10000;box-shadow:0 4px 10px rgba(0,0,0,0.2)';
            document.body.appendChild(menu);
        }}
        menu.innerHTML = `<button onclick="doReply(${{id}},'${{text}}')" class=btn blue style='padding:5px;margin:2px'>↩️ Reply</button><button onclick="doCopy('${{text}}')" class=btn gray style='padding:5px;margin:2px'>📋 Copy</button><button onclick="doDelete(${{id}})" class=btn red style='padding:5px;margin:2px'>🗑️ Delete</button><button onclick="this.parentElement.style.display='none'" class=btn gray style='padding:5px;margin:2px'>X</button>`;
        menu.style.left = e.pageX+'px'; menu.style.top = e.pageY+'px'; menu.style.display='block';
    }}
    function doReply(id, text){{ document.getElementById('replyPreview').style.display='flex'; document.getElementById('replyPreviewText').innerText=text.substring(0,50); document.getElementById('replyToInput').value=text; document.getElementById('msgMenu').style.display='none'; }}
    function doCopy(text){{ navigator.clipboard.writeText(text); document.getElementById('msgMenu').style.display='none'; }}
    function doDelete(id){{ if(confirm('Delete this message?')){{ window.location.href='/dm/{other}?del_msg='+id; }} }}
    function cancelReply(){{ document.getElementById('replyPreview').style.display='none'; document.getElementById('replyToInput').value=''; }}
    document.addEventListener('click', function(e){{ if(!e.target.closest('#msgMenu') &&!e.target.closest('.bubble')){{ let m=document.getElementById('msgMenu'); if(m) m.style.display='none'; }} }});
    """)

    verified_badge = ""
    if other == 'motiz_support':
        verified_badge = " <span class=badge style='background:gold;color:#0f3460;white-space:nowrap'>✓ VERIFIED SUPPORT</span>"
    top_bar = f"<div style='height:45px'></div><div class=dm-top-actions><a class='btn red' href='/block/{other}' style='background:#e94560'>🚫 Block</a><a class='btn gray' href='/unfriend/{other}' style='background:#555'>👋 Unfriend</a></div>" if other not in MOTIZ_PROTECTED else ""

    content = f"<h3>💬 {other_user['name']}{verified_badge} ({format_last_seen(other_user.get('last_seen'))})</h3>{top_bar}<div id=chatBox>{chat_html}</div><form method=POST class=chat-input-fixed><div id=replyPreview class=reply-preview style='display:none'><span id=replyPreviewText></span><button type=button onclick='cancelReply()' style='background:red;color:white;border:none;border-radius:50%;width:20px'>X</button></div><input type=hidden name=reply_to id=replyToInput><div style='display:flex;gap:5px;align-items:center;width:100%'><input name=text id=chatInput placeholder='Type message... (max 700)' required autocomplete=off maxlength=700 style='flex:1'><button class=send-img-btn><img src={SEND_BTN_URL}></button></div></form><div id=msgMenu style='display:none'></div>"
    return render_template_string(BASE, title=f"Chat {other}", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script=timer_js)

@app.route('/check_dm/<other>')
@login_required
def check_dm(nickname, user, other):
    with DBSession() as db:
        cnt = db.execute(sa.text("SELECT COUNT(*) FROM dms WHERE (from_nickname=:u AND to_nickname=:o) OR (from_nickname=:o AND to_nickname=:u)"), {"u": nickname, "o": other}).scalar()
    return Response(json.dumps({"count": cnt}), mimetype="application/json")

@app.route('/create_group', methods=["GET","POST"])
@login_required
def create_group(nickname, user):
    if request.method=="POST":
        name = request.form.get("name","").strip()[:50]
        if name:
            with DBSession() as db:
                db.execute(sa.text("INSERT INTO groups (name, creator, members) VALUES (:n,:c,:m)"), {"n": name, "c": nickname, "m": json.dumps([nickname])})
                db.commit()
            return redirect("/chat")
    return render_template_string(BASE, title="Create Group", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup("<div class=card><h2>Create Group</h2><form method=POST><input name=name placeholder='Group Name' required maxlength=50><button class=btn>Create Group</button></form></div>"), timer_script="")

@app.route('/group/<int:gid>', methods=["GET","POST"])
@login_required
def group_page(nickname, user, gid):
    with DBSession() as db:
        g = db.execute(sa.text("SELECT * FROM groups WHERE id=:i"), {"i": gid}).mappings().first()
        if not g: return redirect("/chat")
        try: members=json.loads(g['members'] or '[]')
        except: members=[]
        if nickname not in members: return redirect("/chat")
        if request.args.get('add_member'):
            new_member = request.args.get('add_member')
            if new_member!= 'motiz_support' and new_member not in members:
                members.append(new_member)
                db.execute(sa.text("UPDATE groups SET members=:m WHERE id=:i"), {"m": json.dumps(members), "i": gid}); db.commit()
            return redirect(f"/group/{gid}")
        if request.args.get('remove_member') and g['creator']==nickname:
            rem = request.args.get('remove_member')
            if rem in members and rem!= nickname and rem!= 'motiz_support':
                members.remove(rem)
                db.execute(sa.text("UPDATE groups SET members=:m WHERE id=:i"), {"m": json.dumps(members), "i": gid}); db.commit()
            return redirect(f"/group/{gid}")
        if request.method=="POST" and request.form.get("text"):
            try: msgs=json.loads(g['messages'] or '[]')
            except: msgs=[]
            msgs.append({"from": nickname, "name": user['name'], "text": request.form["text"][:700], "time": str(datetime.now(NIGERIA_TZ))})
            db.execute(sa.text("UPDATE groups SET messages=:m WHERE id=:i"), {"m": json.dumps(msgs), "i": gid}); db.commit()
            return redirect(f"/group/{gid}")
        try: msgs=json.loads(g['messages'] or '[]')
        except: msgs=[]
        friends_to_add = [f for f in user.get('friends', []) if f not in members and f!= 'motiz_support']
        friends_options = "".join([f"<a class=btn blue href=/group/{gid}?add_member={f} style='margin:3px;width:auto;padding:6px 10px;font-size:0.8rem;display:inline-block;max-width:120px'>➕ Add {f}</a>" for f in friends_to_add])
    html = f"<div class=card><h3>👥 {g['name']}</h3><p>Creator: {g['creator']} | Members: {len(members)} <small>(hidden for privacy)</small></p></div>"
    if friends_to_add:
        html+=f"<div class=card><h4>Add Members (Friends only):</h4>{friends_options}</div>"
    for m in msgs:
        is_me = m['from']==nickname
        cls = "me" if is_me else "other"
        t12 = format_12h(m.get('time',''))
        html+=f"<div class='chat-msg {cls}'><div class='bubble {cls}'><b>{m['name']}</b><br>{m['text']}<div class='bubble-time'>{t12}</div></div></div>"
    html+=f"<form method=POST class=chat-input-fixed><div style='display:flex;gap:5px;width:100%'><input name=text placeholder='Type message... (max 700)' required maxlength=700 style='flex:1'><button class=send-img-btn><img src={SEND_BTN_URL}></button></div></form>"
    timer_js = Markup("""
    let exitBtn = document.querySelector('.exit-btn');
    if(exitBtn) exitBtn.setAttribute('onclick', "location.replace('/chat')");
    """)
    return render_template_string(BASE, title=g['name'], header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html), timer_script=timer_js)
def check_admin_level(level):
    return session.get(f"admin_{level}_logged_in") or session.get("admin_logged_in")

@app.route('/admin/<level>', methods=["GET","POST"])
def admin_level(level):
    global ADMIN_PASS
    if level not in ADMIN_LEVELS and level!= "super":
        return redirect("/admin")
    if not check_admin_level(level):
        error = ""
        if request.method=="POST" and "login_pass" in request.form:
            if request.form.get("login_pass")== ADMIN_PASS or request.form.get("login_pass")== f"{ADMIN_PASS}_{level}":
                session[f"admin_{level}_logged_in"] = True
                return redirect(f"/admin/{level}")
            else: error = "<div class=error>Wrong Password for "+level+"</div>"
        return render_template_string(BASE, title=f"Admin {level.upper()}", header="", content=Markup(f"<div class='card'><h2>🔒 {level.upper()} Admin Login</h2><p>Use main pass or {level} pass</p>{error}<form method=POST><input type=password name=login_pass placeholder='Enter {level} Admin Password' required><button class=btn>Login</button></form></div>"), timer_script="")
    return redirect(f"/admin?level={level}")

@app.route('/admin/clear_questions/<path:cls_key>')
def clear_questions_admin(cls_key):
    if not session.get("admin_logged_in") and not any(session.get(f"admin_{l}_logged_in") for l in ADMIN_LEVELS):
        return redirect("/admin")
    with DBSession() as db:
        db.execute(sa.text("DELETE FROM questions WHERE key LIKE :k"), {"k": f"{cls_key}%"})
        db.execute(sa.text("DELETE FROM cbt_progress WHERE subject_key LIKE :k"), {"k": f"{cls_key}%"})
        db.commit()
    return redirect(f"/admin?level={request.args.get('level','')}")

@app.route('/admin/clear_lessons/<path:cls_key>')
def clear_lessons_admin(cls_key):
    if not session.get("admin_logged_in") and not any(session.get(f"admin_{l}_logged_in") for l in ADMIN_LEVELS):
        return redirect("/admin")
    with DBSession() as db:
        db.execute(sa.text("DELETE FROM lessons WHERE class=:c OR class LIKE :k"), {"c": cls_key, "k": f"{cls_key}%"})
        db.commit()
    return redirect(f"/admin?level={request.args.get('level','')}")

@app.route('/admin', methods=["GET","POST"])
def admin():
    global ADMIN_PASS, NOTICES, PINNED_NOTICE
    nickname, user = get_user()
    if not user:
        return redirect("/login")
    level_filter = request.args.get('level')
    allowed_keys = None
    if level_filter and level_filter in ADMIN_LEVELS:
        if not check_admin_level(level_filter) and not session.get("admin_logged_in"):
            return redirect(f"/admin/{level_filter}")
        allowed_keys = ADMIN_LEVELS[level_filter]
    elif not session.get("admin_logged_in"):
        error = ""
        if request.method=="POST" and "login_pass" in request.form:
            if request.form.get("login_pass")== ADMIN_PASS: session["admin_logged_in"] = True; return redirect("/admin")
            else: error = "<div class=error>Wrong Password</div>"
        return render_template_string(BASE, title="Admin", header="", content=Markup(f"<div class='card'><h2>🔒 Super Admin Login</h2>{error}<form method=POST><input type=password name=login_pass placeholder='Enter Admin Password' required><button class=btn>Login</button></form><p><a href=/admin/jss1>JSS1 Admin</a> | <a href=/admin/jss2>JSS2</a> | <a href=/admin/jss3>JSS3</a> | <a href=/admin/sss1>SS1 Admin</a> | <a href=/admin/sss2>SS2 Admin</a> | <a href=/admin/sss3>SS3 Admin</a></p></div>"), timer_script="")
    error = ""; bulk_result = ""
    q_target = request.args.get('q_target')
    l_target = request.args.get('l_target')
    with DBSession() as db:
        pending_reqs = db.execute(sa.text("SELECT * FROM payments WHERE status='Pending' ORDER BY id DESC")).mappings().all()
        complaints_pending = db.execute(sa.text("SELECT * FROM complaints ORDER BY id DESC LIMIT 50")).mappings().all()
        complaints_count = db.execute(sa.text("SELECT COUNT(*) FROM complaints WHERE status='Pending'")).scalar() or 0
    if request.method=="POST":
        with DBSession() as db:
            try:
                if "verify_id" in request.form:
                    req = db.execute(sa.text("SELECT * FROM payments WHERE id=:id"), {"id": request.form["verify_id"]}).mappings().first()
                    if req:
                        if req["type"] == "questions":
                            db.execute(sa.text("UPDATE users SET q_cycle='paid', is_verified=TRUE, payment_verified_date=:today WHERE nickname=:u"), {"today": str(date.today()), "u": req["nickname"]})
                        if req["type"] == "lessons":
                            db.execute(sa.text("UPDATE users SET lesson_expiry=:d, is_verified=TRUE, payment_verified_date=:today WHERE nickname=:u"), {"d": str(date.today() + timedelta(days=30)), "today": str(date.today()), "u": req["nickname"]})
                        db.execute(sa.text("UPDATE payments SET status='Verified' WHERE id=:id"), {"id": request.form["verify_id"]})
                        db.commit(); error = "<div class=success>✅ Verified - 30 Days</div>"
                if "deny_id" in request.form:
                    db.execute(sa.text("UPDATE payments SET status='Denied' WHERE id=:id"), {"id": request.form["deny_id"]}); db.commit()
                if "reply_complaint" in request.form:
                    db.execute(sa.text("UPDATE complaints SET reply=:r, status='Replied' WHERE id=:i"), {"r": request.form["reply_text"], "i": int(request.form["complaint_id"])}); db.commit()
                if "delete_complaint" in request.form:
                    db.execute(sa.text("DELETE FROM complaints WHERE id=:i"), {"i": int(request.form["complaint_id"])}); db.commit()
                if "add_question" in request.form:
                    key = f"{request.form['q_key']}_{request.form['admin_subject']}"
                    if allowed_keys and not any(k in key for k in allowed_keys):
                        error = f"<div class=error>Not allowed for {level_filter} admin</div>"
                    else:
                        options = [request.form["a"],request.form["b"],request.form["c"],request.form["d"]]
                        correct_ans = options[int(request.form["correct_ans"])]
                        db.execute(sa.text("INSERT INTO questions (key, q, options, ans) VALUES (:k, :q, :o, :a)"),{"k": key, "q": request.form["q"], "o": json.dumps(options), "a": correct_ans}); db.commit()
                if "bulk_upload" in request.form:
                    key = f"{request.form['bulk_key']}_{request.form['bulk_subject']}"
                    if allowed_keys and not any(k in key for k in allowed_keys):
                        error = f"<div class=error>Not allowed for {level_filter} admin</div>"
                    else:
                        db.execute(sa.text("DELETE FROM questions WHERE key=:k"), {"k": key}); db.commit()
                        data = request.form['bulk_data'].strip()
                        f_io = StringIO(data); reader = csv.reader(f_io); success = 0
                        for i, parts in enumerate(reader, 1):
                            try:
                                if len(parts)!= 6: continue
                                q, a, b, c, d, ans = [x.strip() for x in parts]
                                db.execute(sa.text("INSERT INTO questions (key, q, options, ans) VALUES (:k, :q, :o, :a)"),{"k": key, "q": q, "o": json.dumps([a,b,c,d]), "a": ans}); success += 1
                            except: pass
                        db.commit()
                        bulk_result = f"<div class=success>✅ {success} Added for {key}</div>"
                if "add_lesson" in request.form:
                    parts = request.form['l_key'].split("_"); cls = parts[0]; dept = parts[1] if len(parts) > 1 else ""
                    subject = request.form['lesson_subject']
                    if allowed_keys and not any(k in request.form['l_key'] for k in allowed_keys):
                        error = f"<div class=error>Not allowed for {level_filter} admin</div>"
                    else:
                        db.execute(sa.text("DELETE FROM lessons WHERE class=:c AND subject=:s"), {"c": cls, "s": subject}); db.commit()
                        db.execute(sa.text("INSERT INTO lessons (class, dept, subject, title, notes, date, media_link) VALUES (:c, :d, :s, :t, :n, :date, :m)"),
                                   {"c": cls, "d": dept, "s": subject, "t": request.form['lesson_title'], "n": request.form['lesson_notes'], "date": str(date.today()), "m": request.form.get('media_link','')}); db.commit()
                if "post_notice" in request.form:
                    NOTICES.insert(0, {"id": int(datetime.now().timestamp()), "title": request.form["notice_title"], "text": request.form["notice_text"], "media_link": request.form.get("media_link",""), "created_at": str(datetime.now(NIGERIA_TZ))})
                    set_setting("notices", json.dumps(NOTICES))
            except Exception as e:
                error = f"<div class=error>Error: {str(e)}</div>"
                try: db.rollback()
                except: pass
    pending_html = "".join([f"<div class='card'><b>{r['name']} (@{r['nickname']})</b> for {r['type']}<br><small>Bank: {r['bank_used']} | Acc: {r['account_name']}</small><div style='display:flex;gap:8px;justify-content:center'><form method=POST style='flex:1'><input type=hidden name=verify_id value={r['id']}><button class='btn' style='width:95%;max-width:150px'>✅ Verify</button></form><form method=POST style='flex:1'><input type=hidden name=deny_id value={r['id']}><button class='btn red' style='width:95%;max-width:150px'>❌ Deny</button></form></div></div>" for r in pending_reqs])
    complaints_html = ""
    for c in complaints_pending:
        ct12 = format_12h(str(c['created_at']))
        if c['status']=='Pending':
            reply_form = f"<form method=POST><input type=hidden name=complaint_id value={c['id']}><textarea name=reply_text placeholder='Reply...' required>{c['reply'] or ''}</textarea><button name=reply_complaint class='btn blue'>Reply</button></form>"
        else:
            reply_form = f"<div style='background:#d4edda;padding:5px'><b>Replied:</b> {c['reply']}</div>"
        complaints_html+=f"<div class=card><b>{c['name']} (@{c['nickname']}) - {c['status']}</b><p>{c['text']}</p><small>{ct12}</small>{reply_form}</div>"
    keys = ["JSS1","JSS2","JSS3","SS1_Science","SS1_Commercial","SS1_Art","SS2_Science","SS2_Commercial","SS2_Art","SS3_Science","SS3_Commercial","SS3_Art"]
    if allowed_keys: keys = [k for k in keys if k in allowed_keys]
    labels = {"JSS1":"JSS1","JSS2":"JSS2","JSS3":"JSS3","SS1_Science":"SS1 Science","SS1_Commercial":"SS1 Commercial","SS1_Art":"SS1 Art","SS2_Science":"SS2 Science","SS2_Commercial":"SS2 Commercial","SS2_Art":"SS2 Art","SS3_Science":"SS3 Science","SS3_Commercial":"SS3 Commercial","SS3_Art":"SS3 Art"}
    group1 = ""; group2 = ""
    for k in keys:
        l = labels.get(k,k)
        group1 += f"<a href=/admin?q_target={k}&level={level_filter or ''} class='btn blue cbt-btn-fix'>➕ Add Q: {l}</a>"
        group1 += f"<a href=/admin?q_target={k}&bulk=1&level={level_filter or ''} class='btn orange cbt-btn-fix'>📦 Bulk Q: {l}</a>"
        group1 += f"<a href=/admin/clear_questions/{k}?level={level_filter or ''} class='btn red cbt-btn-fix' onclick=\"return confirm('Clear ALL {l} questions? This go reset progress too')\">🗑️ Clear Qs: {l}</a>"
        group2 += f"<a href=/admin?l_target={k}&level={level_filter or ''} class='btn blue cbt-btn-fix'>➕ Add Lesson: {l}</a>"
        group2 += f"<a href=/admin/clear_lessons/{k}?level={level_filter or ''} class='btn red cbt-btn-fix' onclick=\"return confirm('Clear ALL {l} lessons?')\">🗑️ Clear Lessons: {l}</a>"
    add_q_form = ""; bulk_form = ""
    if q_target:
        subs = SUBJECTS.get(q_target, [])
        sub_options = "".join([f"<option>{s}</option>" for s in subs])
        add_q_form = f"<div class=card><h3>Add Q for {q_target} - Full Answer Text</h3><form method=POST><input type=hidden name=q_key value='{q_target}'><select name=admin_subject required><option value=''>Select Subject</option>{sub_options}</select><textarea name=q placeholder='Question' required></textarea><input name=a placeholder='Option A' required><input name=b placeholder='Option B' required><input name=c placeholder='Option C' required><input name=d placeholder='Option D' required><select name=correct_ans required><option value=0>A is Correct</option><option value=1>B is Correct</option><option value=2>C is Correct</option><option value=3>D is Correct</option></select><button name=add_question class='btn'>➕ Add Question</button></form></div>"
        if request.args.get('bulk'):
            bulk_form = f"<div class=card><h3>📦 Bulk for {q_target}</h3><p>Format: Question,A,B,C,D,FullCorrectAnswer</p>{bulk_result}<form method=POST><input type=hidden name=bulk_key value='{q_target}'><select name=bulk_subject required><option value=''>Select Subject</option>{sub_options}</select><textarea name=bulk_data placeholder='What is 2+2?,2,3,4,5,4' rows=10 required></textarea><button name=bulk_upload class='btn orange'>Upload Bulk - Old Auto-Delete</button></form></div>"
    add_l_form = ""
    if l_target:
        subs = SUBJECTS.get(l_target, [])
        sub_options = "".join([f"<option>{s}</option>" for s in subs])
        add_l_form = f"<div class=card><h3>Add Lesson for {l_target} - 1 Per Subject</h3><form method=POST><input type=hidden name=l_key value='{l_target}'><select name=lesson_subject required><option value=''>Select Subject</option>{sub_options}</select><input name=lesson_title placeholder='Title' required><textarea name=lesson_notes placeholder='Notes' rows=6 required></textarea><input name=media_link placeholder='Img/Video link'><button name=add_lesson class='btn'>➕ Add Lesson - Replace Old</button></form></div>"
    level_info = f"<div class=card style='border:3px solid gold'><h2>👑 {level_filter.upper() if level_filter else 'SUPER'} ADMIN</h2><p>Managing: {', '.join(allowed_keys) if allowed_keys else 'ALL'}</p></div>" if level_filter else f"<div class=card style='border:3px solid #0f3460'><h2>👑 SUPER ADMIN - All Access</h2></div>"
    html = f'''{level_info}{add_q_form}{bulk_form}{add_l_form}
    <div class="card"><h2>GROUP 1: CBT 100 Qs + CLEAR</h2><div style="display:flex;flex-direction:column;gap:8px">{group1}</div></div>
    <div class="card"><h2>GROUP 2: LESSONS + CLEAR</h2><div style="display:flex;flex-direction:column;gap:8px">{group2}</div></div>
    <div class="card"><h2>GROUP 3: PAYMENTS ({len(pending_reqs)})</h2>{pending_html or "<p>No pending</p>"}<a href=/admin_attendance?level={level_filter or ""} class='btn blue'>Attendance</a></div>
    <div class="card"><h2>GROUP 4: COMPLAINTS ({complaints_count})</h2>{complaints_html or "<p>No complaints</p>"}</div>'''
    return render_template_string(BASE, title="Admin", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"{error}{html}"), timer_script="")

@app.route("/admin_attendance")
def admin_attendance():
    nickname, user = get_user()
    if not user: return redirect("/login")
    if not session.get("admin_logged_in") and not any(session.get(f"admin_{l}_logged_in") for l in ADMIN_LEVELS):
        return redirect("/admin")
    level_filter = request.args.get('level')
    with DBSession() as db:
        users = db.execute(sa.text("SELECT name, nickname, class, dept, q_used, lesson_expiry, is_verified, last_seen, referral_count, free_days, payment_verified_date FROM users WHERE nickname!='motiz_support' ORDER BY last_seen DESC NULLS LAST")).mappings().all()
    table = ""
    for u in users:
        ls_text = format_last_seen(u['last_seen']) if u['last_seen'] else "Never"
        paid_status = "✅ Paid" if is_user_paid(dict(u)) else "Free"
        expiry = u['payment_verified_date'] or 'None'
        table += f"<tr><td>{u['name']}<br><small>@{u['nickname']}</small> {paid_status}</td><td>{u['class']}</td><td>{u['q_used']}</td><td>{paid_status}</td><td style='font-size:0.7rem'>{expiry}</td><td>{ls_text}</td><td>{u['referral_count'] or 0}</td></tr>"
    content = f"<div class=card><h2>Attendance - {level_filter or 'All'}</h2><div style='overflow-x:auto'><table border=1 style='width:100%;font-size:0.75rem;border-collapse:collapse'><tr><th>Name</th><th>Class</th><th>Q Used</th><th>Status</th><th>Expiry</th><th>Last Seen</th><th>Refs</th></tr>{table}</table></div></div>"
    return render_template_string(BASE, title="Attendance", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))