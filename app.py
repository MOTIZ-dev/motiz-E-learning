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

# FIXED BASE: 1 AD ONLY + NO CLICK SOUND + WHATSAPP CHAT INPUT DOWNWARD
BASE = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/png" href="{FAVICON_URL}"><link rel="manifest" href="/manifest.json"><title>{{{{title}}}}</title><style>
:root{{--bg:#f0f2f5;--card:white;--text:#333;--primary:#0f3460}} body{{font-family:Segoe UI;background:var(--bg);color:var(--text);margin:0;padding:0;padding-bottom:90px}}
body.dark{{--bg:#121212;--card:#1e1e1e;--text:#eee}} body.light{{--bg:#f0f2f5;--card:white;--text:#333}}
.header{{background:var(--primary);color:white;padding:6px 10px;text-align:center;position:fixed;top:0;width:100%;z-index:1000;display:flex;justify-content:space-between;align-items:center;height:70px;box-sizing:border-box}}
.header h1{{margin:0;font-size:0.80rem;flex:1;text-align:center;color:white!important;display:flex;align-items:center;justify-content:center;gap:6px;white-space:nowrap;overflow:hidden}}
.header img.logo{{width:75px!important;height:75px!important;border-radius:50%;object-fit:contain;max-height:70px}}
.theme-btn{{border:none;background:transparent;color:white;font-size:1.2rem;cursor:pointer}}
.exit-btn{{background:transparent;color:white;border:none;padding:5px 10px;font-size:1.3rem;cursor:pointer}}
.nav{{display:flex;gap:5px;background:#16213e;padding:6px 5px;flex-wrap:wrap;position:fixed;top:70px;width:100%;z-index:999}}
.nav a{{color:white!important;text-decoration:none;padding:5px 8px;border-radius:10px;border:1px solid #fff3;font-size:0.8rem;white-space:nowrap}}
.container{{padding:10px;padding-top:145px;padding-bottom:90px}}
.card{{background:var(--card);padding:12px;margin:8px 0;border-radius:10px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}}
.card:last-child{{margin-bottom:90px!important}}
.btn{{background:#28a745;color:white!important;padding:10px;display:block;margin:8px auto;text-align:center;font-weight:bold;border:none;width:95%;max-width:350px;border-radius:8px;cursor:pointer}}
.btn.red{{background:#e94560!important}}.btn.blue{{background:#0f3460!important;border:1px solid white}}.btn.orange{{background:#ff9800!important}}.btn.gray{{background:#555!important;width:90%;max-width:300px;font-size:0.85rem}}
input:not([type=radio]),select,textarea{{width:100%;padding:10px;margin:5px 0;border-radius:5px;border:1px solid #ccc;box-sizing:border-box;background:var(--card);color:var(--text)}}
.option{{background:#f0f2f5;padding:14px 16px;margin:10px 0;border-radius:10px;color:black;display:flex;gap:14px;align-items:center;cursor:pointer;border:1px solid #dee2e6}}
.option input[type=radio]{{width:20px!important;height:20px!important;flex-shrink:0;margin:0!important;accent-color:#0f3460}}
.option:has(input:checked){{background:#0f3460!important;color:white!important}}
.badge{{background:#1DA1F2;color:white;padding:3px 8px;border-radius:10px;font-size:0.7rem}}.badge.gold{{background:gold;color:#0f3460;font-weight:bold}}.badge.verified-paid{{background:#28a745;color:white}}
.chat-msg{{display:flex;margin:8px 0;gap:8px}}.chat-msg.me{{justify-content:flex-end}}.chat-msg.other{{justify-content:flex-start}}
.bubble{{padding:10px 14px;border-radius:18px;max-width:70%}}.me.bubble{{background:#2196f3!important;color:white!important}}.other.bubble{{background:#e0e0e0;color:#333}}
.friend-card{{display:flex;align-items:center;gap:10px;padding:12px;background:var(--card);border-radius:10px;margin:8px 0;text-decoration:none;color:var(--text)}}
.friend-avatar{{width:45px;height:45px;border-radius:50%;background:var(--primary);color:white;display:flex;align-items:center;justify-content:center;font-weight:bold}}
.readonly-box{{width:100%;padding:12px;background:#eee;border:1px dashed #999;text-align:center}}
.chat-input-fixed{{position:fixed;bottom:62px;left:0;right:0;display:flex;flex-direction:column;gap:5px;background:var(--card);padding:8px 10px;z-index:999;border-top:1px solid #ddd}}
.chat-input-row{{display:flex;gap:8px;align-items:center;width:100%}}
.chat-input-row input{{flex:1;border-radius:25px!important;padding:12px 15px!important;background:#f0f2f5!important}}
.reply-preview{{background:#f0f2f5;border-left:4px solid #2196f3;padding:6px 10px;border-radius:5px;display:flex;justify-content:space-between;color:#333}}
.send-img-btn{{background:#0f3460;border:none;border-radius:50%;width:45px;height:45px;display:flex;align-items:center;justify-content:center;flex-shrink:0}}
.send-img-btn img{{height:28px;width:28px}}
#fixedAdBar{{position:fixed;bottom:0;left:0;width:100%;height:60px;background:white;z-index:99999;border-top:1px solid #ddd;display:flex;justify-content:center;align-items:center}}
#updateBanner{{display:none;position:fixed;top:0;left:0;width:100%;background:#ff9800;color:white;padding:10px;text-align:center;z-index:100001}}
.cbt-btn-fix{{display:block;width:95%;max-width:340px;white-space:normal;line-height:1.3;padding:10px;font-size:0.85rem;margin:8px auto}}
.calc-float{{position:fixed;bottom:85px;right:10px;background:#222;color:white;padding:10px;border-radius:10px;z-index:9998;width:240px;display:none;border:2px solid #ff9800}}
.community-bg-post{{padding:30px 15px;text-align:center;border-radius:15px;color:white;font-size:1.4rem;font-weight:bold;min-height:120px;display:flex;align-items:center;justify-content:center}}
.bg-option{{width:35px;height:35px;border-radius:50%;display:inline-block;margin:4px;border:2px solid #fff;cursor:pointer}}
.bg-option.selected{{border:3px solid #0f3460;transform:scale(1.2)}}
.like-row{{display:flex;gap:8px;justify-content:flex-start;align-items:center;margin-top:8px}}
.dm-top-actions{{position:fixed;top:82px;left:0;right:0;background:var(--card);padding:6px 10px;display:flex;gap:8px;justify-content:center;z-index:998;border-bottom:1px solid #ddd}}
#cbt_form{{padding-bottom:80px}}
</style></head><body>
<div id="updateBanner">🔄 New version - <button onclick="location.reload(true)" style="background:white;color:#ff9800;border:none;padding:5px 10px;border-radius:5px">Update now</button></div>
{{{{header}}}}<div class="container">{{{{content}}}}</div>
<div id="fixedAdBar"><button onclick="document.getElementById('fixedAdBar').style.display='none'" style="position:absolute;top:2px;right:5px;background:#000;color:#fff;border:none;border-radius:50%;width:20px;height:20px">X</button><div id="adContainer" style="width:728px;max-width:100%;height:60px;display:flex;align-items:center;justify-content:center;"><script>atOptions = {{'key' : '{FIXED_AD_KEY}','format' : 'iframe','height' : 60,'width' : 728,'params' : {{}} }};</script><script src="https://www.highrevenueformat.com/{FIXED_AD_KEY}/invoke.js"></script></div></div>
<div id="calcFloat" class="calc-float"><div style="display:flex;justify-content:space-between"><b>🧮 Calculator</b><button onclick="document.getElementById('calcFloat').style.display='none'" style="background:red;color:white;border:none;border-radius:50%;width:20px">X</button></div><input id="calcDisplay" readonly style="background:#111;color:#0f0;text-align:right;font-size:1.2rem"><div style="display:grid;grid-template-columns:repeat(4,1fr);gap:5px;margin-top:5px"><button class="btn gray" onclick="calcPress('7')">7</button><button class="btn gray" onclick="calcPress('8')">8</button><button class="btn gray" onclick="calcPress('9')">9</button><button class="btn orange" onclick="calcPress('/')">/</button><button class="btn gray" onclick="calcPress('4')">4</button><button class="btn gray" onclick="calcPress('5')">5</button><button class="btn gray" onclick="calcPress('6')">6</button><button class="btn orange" onclick="calcPress('*')">*</button><button class="btn gray" onclick="calcPress('1')">1</button><button class="btn gray" onclick="calcPress('2')">2</button><button class="btn gray" onclick="calcPress('3')">3</button><button class="btn orange" onclick="calcPress('-')">-</button><button class="btn gray" onclick="calcPress('0')">0</button><button class="btn gray" onclick="calcPress('.')">.</button><button class="btn blue" onclick="calcEval()">=</button><button class="btn orange" onclick="calcPress('+')">+</button><button class="btn red" onclick="calcClear()" style="grid-column:span 4">Clear</button></div></div>
<button id="calcBtn" onclick="document.getElementById('calcFloat').style.display='block'" style="position:fixed;bottom:85px;right:15px;background:#ff9800;color:white;border:none;border-radius:50%;width:55px;height:55px;font-size:1.5rem;z-index:9997;display:none;box-shadow:0 4px 10px rgba(0,0,0,0.3)">🧮</button>
<script>
{{{{timer_script}}}}
let mainAdInterval = {AD_REFRESH_MAIN} * 1000;
setInterval(function(){{ let adBar=document.getElementById('fixedAdBar'); if(adBar && adBar.style.display!=='none' &&!document.hidden){{ try{{ let ns=document.createElement('script'); ns.src='https://www.highrevenueformat.com/{FIXED_AD_KEY}/invoke.js'; document.getElementById('adContainer').appendChild(ns); }}catch(e){{}} }} }}, mainAdInterval);
function calcPress(v){{ document.getElementById('calcDisplay').value += v; }}
function calcClear(){{ document.getElementById('calcDisplay').value = ''; }}
function calcEval(){{ try{{ document.getElementById('calcDisplay').value = eval(document.getElementById('calcDisplay').value); }}catch(e){{ document.getElementById('calcDisplay').value='Error'; }} }}
(function(){{ let saved = localStorage.getItem('motiz_theme') || 'dark'; document.body.classList.remove('light','dark'); document.body.classList.add(saved); let btn=document.getElementById('themeToggle'); if(btn) btn.innerText = saved==='light'? '☀️ Light' : '🌙 Dark'; }})();
function toggleTheme(){{ let isLight = document.body.classList.contains('light'); document.body.classList.remove('light','dark'); if(isLight){{ document.body.classList.add('dark'); localStorage.setItem('motiz_theme','dark'); document.getElementById('themeToggle').innerText='🌙 Dark'; }} else {{ document.body.classList.add('light'); localStorage.setItem('motiz_theme','light'); document.getElementById('themeToggle').innerText='☀️ Light'; }} }}
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
    return Response(json.dumps({"name":"MOTIZ E-LEARNING","short_name":"MOTIZ","start_url":"/main","display":"standalone","background_color":"#0f3460","theme_color":"#0f3460","icons":[{"src":FAVICON_URL,"sizes":"192x192","type":"image/png"}]}), mimetype='application/json')
@app.route('/sw.js')
def sw():
    return Response("""
self.addEventListener('install', e=>self.skipWaiting());
self.addEventListener('activate', e=>self.clients.claim());
self.addEventListener('fetch', e=>{ e.respondWith(fetch(e.request).catch(()=>caches.match(e.request))) });
""", mimetype='application/javascript')
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

# FIXED: MOTIZ E-LEARNING INSTITUTION - PROGRESS BAR - NO SOUND
@app.route('/')
def splash():
    return render_template_string(f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Welcome</title><link rel="icon" type="image/png" href="{FAVICON_URL}"><meta http-equiv="refresh" content="10;url=/login">
<style>body{{margin:0;background:linear-gradient(135deg,#0f3460,#16213e);color:white;font-family:Segoe UI;display:flex;justify-content:center;align-items:center;height:100vh;flex-direction:column;text-align:center}}.logo{{font-size:2.4rem;font-weight:bold;line-height:1.2}}.progress-bar{{width:220px;height:10px;background:#fff3;border-radius:10px;overflow:hidden;margin-top:25px}}.progress-fill{{height:100%;width:0%;background:white;animation:load 10s linear forwards}} @keyframes load{{0%{{width:0%}}100%{{width:100%}}}} </style></head><body>
<div class="logo">MOTIZ<br>E-LEARNING<br>INSTITUTION</div><div class="subtext" style="margin-top:12px;opacity:0.9">Learn. Practice. Excel.</div><div class="progress-bar"><div class="progress-fill"></div></div><p style="font-size:12px;margin-top:15px">Loading…</p></body></html>""")

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
    form = f"<div class='card'><h2>Register</h2>{error}<form method=POST><input name=nickname placeholder='Enter Nickname - e.g motiz123' required><input name=surname placeholder='Enter Surname - e.g Hamzat' required><input name=other placeholder='Enter Other Name - e.g Kolade' required><input type=password name=password placeholder='Create Password - min 4 chars' required><select name=class id=class onchange=d() required><option value=''>Select Class</option>{''.join([f'<option>{c}</option>' for c in CLASSES])}</select><div id=deptBox></div><button class=btn>Register</button><p>Already have account? <a href=/login>Login</a></p></form></div>{js}"
    return render_template_string(BASE, title="Register", header="", content=Markup(form), timer_script="")

# FIXED: PLACEHOLDER + REGISTER LINK RETURNED
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
            else: error = "<div class=error>Invalid Nickname or Password</div>"
    return render_template_string(BASE, title="Login", header="", content=Markup(f"<div class='card'><h2>Login</h2>{error}<form method=POST><input name=nickname placeholder='Enter your Nickname' required><input type=password name=password placeholder='Enter your Password' required><button class=btn>Login</button><p style='text-align:center;margin-top:15px;font-size:0.9rem'>Don't have an account? <a href=/register style='color:#0f3460;font-weight:bold;text-decoration:underline'>Click to Register</a></p></form></div>"), timer_script="")

@app.route('/main')
@login_required
def main(nickname, user):
    with DBSession() as db: db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
    pinned_html = ""
    if PINNED_NOTICE:
        try: pin = json.loads(PINNED_NOTICE); pinned_html = f"<div class='card' style='border:2px solid gold'><div class=notice-title>📌 {pin['title']}</div>{pin['text']}</div>"
        except: pinned_html = f"<div class=card style='border:2px solid gold'><b>📌 PINNED:</b> {PINNED_NOTICE}</div>"
    notices_html = ""
    for n in NOTICES:
        media = ""
        if n.get('media_link'):
            link = n['media_link']
            if any(x in link.lower() for x in ['.mp4','.webm','video']):
                media = f"<video src='{link}' controls class='lesson-media'></video>"
            else:
                media = f"<img src='{link}' class='lesson-media'>"
        time_12 = format_12h(n.get('created_at',''))
        notices_html += f"<div class='card'><div class=notice-title>📢 {n['title']}</div>{n['text']}{media}<small style='float:right'>{time_12}</small></div>"
    return render_template_string(BASE, title="Home", header=Markup(get_header(nickname,user, show_nav=True, show_favicon=True, is_home=True)), content=Markup(f"<div class='card'><h2>Welcome {user['name']}</h2><p><b>Class:</b> {user['class']} {user.get('dept','')}</p></div>{pinned_html}<h3>General Notice</h3>{notices_html}<a class=btn href=/exam>Start CBT Exam</a><a class=btn orange href=/daily>🏆 Daily Challenge (FREE)</a>"), timer_script="")

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
BG_COLORS = ["#0f3460","#e94560","#28a745","#ff9800","#6f42c1","#20c997","#fd7e14","#1DA1F2","#333","linear-gradient(135deg,#0f3460,#16213e)"]
@app.route('/community', methods=["GET","POST"])
@login_required
def community(nickname, user):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        if request.method == "POST":
            text = request.form.get("text","").strip()
            bg = request.form.get("bg", BG_COLORS[0])
            if text and len(text) <= 500:
                db.execute(sa.text("INSERT INTO posts (nickname, name, text, likes, comments, bg) VALUES (:u, :n, :t, '[]', '[]', :bg)"), {"u": nickname, "n": user['name'], "t": text, "bg": bg}); db.commit()
            return redirect("/community")
        posts = db.execute(sa.text("SELECT * FROM posts ORDER BY created_at DESC LIMIT 50")).mappings().all()
        posts_html = ""
        for p in posts:
            try: likes = json.loads(p['likes'] or '[]')
            except: likes = []
            try: comments = json.loads(p['comments'] or '[]')
            except: comments = []
            like_count = len(likes)
            is_liked = nickname in likes
            bg = p.get('bg') or "#0f3460"
            if "gradient" in bg: bg_style = f"background:{bg}"
            else: bg_style = f"background:{bg}"
            comments_html = ""
            for c in comments[-3:]:
                comments_html += f"<div style='background:#f0f2f5;padding:6px 10px;border-radius:10px;margin:5px 0;color:#333'><b>{c.get('name','')}:</b> {c.get('text','')}</div>"
            posts_html += f"<div class=card><div class=community-bg-post style='{bg_style}'><span>{p['text']}</span></div><p><b>{p['name']}</b> <small>{format_12h(str(p['created_at']))}</small></p><div class=like-row><button onclick=\"location.href='/like/{p['id']}'\" class='btn blue' style='width:auto;padding:5px 12px;margin:0'>{ '❤️' if is_liked else '🤍' } {like_count}</button><button onclick=\"document.getElementById('comment-{p['id']}').style.display='block'\" class='btn gray' style='width:auto;padding:5px 12px;margin:0'>💬 {len(comments)}</button></div>{comments_html}<div id='comment-{p['id']}' style='display:none;margin-top:8px'><form method=POST action='/comment/{p['id']}'><input name=text placeholder='Write comment... (max 200)' maxlength=200 required><button class=btn blue style='padding:5px'>Reply</button></form></div></div>"
        bg_options = "".join([f"<span class='bg-option' style='background:{c}' onclick=\"setBg('{c}', this)\"></span>" for c in BG_COLORS])
        post_form = f"<div class=card><h3>✍️ Create Post (500 max)</h3><form method=POST><textarea name=text placeholder='What is on your mind?' maxlength=500 required style='min-height:80px'></textarea><div style='margin:8px 0'><small>Choose background:</small><br>{bg_options}</div><input type=hidden name=bg id=selectedBg value='{BG_COLORS[0]}'><button class=btn blue>Post</button></form></div><script>function setBg(c, el){{ document.getElementById('selectedBg').value=c; document.querySelectorAll('.bg-option').forEach(e=>e.classList.remove('selected')); el.classList.add('selected'); }}</script>"
        return render_template_string(BASE, title="Community", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(post_form+posts_html), timer_script="")

@app.route('/like/<int:pid>')
@login_required
def like_post(nickname, user, pid):
    with DBSession() as db:
        post = db.execute(sa.text("SELECT likes FROM posts WHERE id=:i"), {"i": pid}).mappings().first()
        if post:
            try: likes = json.loads(post['likes'] or '[]')
            except: likes = []
            if nickname in likes: likes.remove(nickname)
            else: likes.append(nickname)
            db.execute(sa.text("UPDATE posts SET likes=:l WHERE id=:i"), {"l": json.dumps(likes), "i": pid}); db.commit()
    return redirect("/community")

@app.route('/comment/<int:pid>', methods=["POST"])
@login_required
def comment_post(nickname, user, pid):
    text = request.form.get("text","").strip()[:200]
    if not text: return redirect("/community")
    with DBSession() as db:
        post = db.execute(sa.text("SELECT comments FROM posts WHERE id=:i"), {"i": pid}).mappings().first()
        if post:
            try: comments = json.loads(post['comments'] or '[]')
            except: comments = []
            comments.append({"nickname": nickname, "name": user['name'], "text": text, "time": str(datetime.now(pytz.timezone('Africa/Lagos')))})
            db.execute(sa.text("UPDATE posts SET comments=:c WHERE id=:i"), {"c": json.dumps(comments), "i": pid}); db.commit()
    return redirect("/community")

@app.route('/chat')
@login_required
def chat_list(nickname, user):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        friends = user.get('friends', [])
        groups = db.execute(sa.text("SELECT * FROM groups WHERE :u = ANY(STRING_TO_ARRAY(members, ',')) OR creator=:u"), {"u": nickname}).mappings().all() if False else []
        try:
            groups = db.execute(sa.text("SELECT * FROM groups")).mappings().all()
            my_groups = []
            for g in groups:
                try:
                    mems = json.loads(g['members'] or '[]')
                    if nickname in mems or g['creator']==nickname: my_groups.append(g)
                except: pass
            groups = my_groups
        except: groups=[]
        reqs = db.execute(sa.text("SELECT * FROM friend_requests WHERE to_nickname=:u AND status='Pending'"), {"u": nickname}).mappings().all()
        req_html = ""
        for r in reqs:
            req_html += f"<div class=card><b>{r['from_nickname']}</b> wants to be friends <a class='btn blue' style='width:auto;display:inline-block;padding:5px 10px' href='/friend_accept/{r['id']}'>Accept</a> <a class='btn red' style='width:auto;display:inline-block;padding:5px 10px' href='/friend_reject/{r['id']}'>Reject</a></div>"
        friends_html = ""
        for f in friends[:100]:
            un = get_unread_per_friend(nickname, f)
            badge = f" <span class=badge>{un}</span>" if un>0 else ""
            friends_html += f"<a href='/dm/{f}' class=friend-card><div class=friend-avatar>{f[0].upper()}</div><div><b>{f}</b>{badge}<br><small>{format_last_seen(None)}</small></div></a>"
        groups_html = "".join([f"<a href='/group/{g['id']}' class=friend-card><div class=friend-avatar>👥</div><div><b>{g['name']}</b></div></a>" for g in groups])
        search_html = f"<div class=card><h3>🔍 Find Friends</h3><form method=GET action=/search><input name=q placeholder='Search nickname...' required><button class=btn blue>Search</button></form></div><div class=card><h3>👥 Create Group</h3><form method=POST action=/create_group><input name=name placeholder='Group name' required><button class=btn orange>Create</button></form></div>"
        content = f"{search_html}{req_html}<h3>👥 My Groups</h3>{groups_html if groups_html else '<p>No groups yet</p>'}<h3>💬 Friends {len(friends)}</h3>{friends_html if friends_html else '<p>No friends yet - add MOTIZ SUPPORT auto</p>'}"
        return render_template_string(BASE, title="Chat", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")

@app.route('/search')
@login_required
def search_users(nickname, user):
    q = request.args.get('q','').strip().lower()
    if not q: return redirect("/chat")
    with DBSession() as db:
        results = db.execute(sa.text("SELECT nickname, name FROM users WHERE LOWER(nickname) LIKE :q AND nickname!=:u LIMIT 20"), {"q": f"%{q}%", "u": nickname}).mappings().all()
        html = f"<div class=card><h3>Search: {q}</h3></div>"
        for r in results:
            is_friend = r['nickname'] in user.get('friends', [])
            btn = f"<span class=badge>Friend</span>" if is_friend else f"<a class='btn blue' style='width:auto;padding:5px 10px;display:inline-block' href='/friend_add/{r['nickname']}'>Add Friend</a>"
            html += f"<div class=card><b>{r['nickname']}</b> - {r['name']}<br>{btn}</div>"
        if not results: html += "<div class=card>No users found</div>"
        return render_template_string(BASE, title="Search", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html), timer_script="")

@app.route('/friend_add/<other>')
@login_required
def friend_add(nickname, user, other):
    if other == nickname: return redirect("/chat")
    with DBSession() as db:
        exists = db.execute(sa.text("SELECT id FROM friend_requests WHERE from_nickname=:f AND to_nickname=:t AND status='Pending'"), {"f": nickname, "t": other}).scalar()
        already = other in user.get('friends', [])
        if not exists and not already:
            db.execute(sa.text("INSERT INTO friend_requests (from_nickname, to_nickname) VALUES (:f, :t)"), {"f": nickname, "t": other}); db.commit()
    return redirect("/chat")

@app.route('/friend_accept/<int:rid>')
@login_required
def friend_accept(nickname, user, rid):
    with DBSession() as db:
        req = db.execute(sa.text("SELECT * FROM friend_requests WHERE id=:i AND to_nickname=:u"), {"i": rid, "u": nickname}).mappings().first()
        if req:
            from_nick = req['from_nickname']
            db.execute(sa.text("UPDATE friend_requests SET status='Accepted' WHERE id=:i"), {"i": rid})
            for pair in [(nickname, from_nick), (from_nick, nickname)]:
                u = db.execute(sa.text("SELECT friends FROM users WHERE nickname=:u"), {"u": pair[0]}).mappings().first()
                if u:
                    try: fr = json.loads(u['friends'] or '[]')
                    except: fr = []
                    if pair[1] not in fr:
                        fr.append(pair[1])
                        db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(fr), "u": pair[0]})
            db.commit()
    return redirect("/chat")

@app.route('/friend_reject/<int:rid>')
@login_required
def friend_reject(nickname, user, rid):
    with DBSession() as db:
        db.execute(sa.text("UPDATE friend_requests SET status='Rejected' WHERE id=:i AND to_nickname=:u"), {"i": rid, "u": nickname}); db.commit()
    return redirect("/chat")

@app.route('/create_group', methods=["POST"])
@login_required
def create_group(nickname, user):
    name = request.form.get('name','').strip()[:50]
    if not name: return redirect("/chat")
    with DBSession() as db:
        db.execute(sa.text("INSERT INTO groups (name, creator, members, messages) VALUES (:n, :c, :m, '[]')"), {"n": name, "c": nickname, "m": json.dumps([nickname])}); db.commit()
    return redirect("/chat")

@app.route('/group/<int:gid>', methods=["GET","POST"])
@login_required
def group_chat(nickname, user, gid):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        group = db.execute(sa.text("SELECT * FROM groups WHERE id=:i"), {"i": gid}).mappings().first()
        if not group: return redirect("/chat")
        try: members = json.loads(group['members'] or '[]')
        except: members = []
        if nickname not in members and group['creator']!=nickname: return redirect("/chat")
        if request.method == "POST":
            text = request.form.get("text","").strip()[:700]
            if text:
                try: msgs = json.loads(group['messages'] or '[]')
                except: msgs=[]
                msgs.append({"from": nickname, "text": text, "time": str(datetime.now(pytz.timezone('Africa/Lagos')))})
                db.execute(sa.text("UPDATE groups SET messages=:m WHERE id=:i"), {"m": json.dumps(msgs), "i": gid}); db.commit()
            return redirect(f"/group/{gid}")
        try: messages = json.loads(group['messages'] or '[]')
        except: messages=[]
        msgs_html = ""
        for m in messages[-100:]:
            cls = "me" if m['from']==nickname else "other"
            msgs_html += f"<div class='chat-msg {cls}'><div class='bubble {cls}'><b>{m['from']}</b><br>{m['text']}<br><small>{format_12h(m.get('time',''))}</small></div></div>"
        content = f"<div class=card><h3>👥 {group['name']} - {len(members)} members</h3></div><div style='padding-bottom:80px'>{msgs_html}</div><form method=POST class=chat-input-fixed><div class=chat-input-row><input name=text placeholder='Type message... (max 700)' required maxlength=700 autocomplete=off><button class=send-img-btn><img src={SEND_BTN_URL}></button></div></form>"
        return render_template_string(BASE, title=group['name'], header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")

@app.route('/dm/<other>', methods=["GET","POST"])
@login_required
def dm_chat(nickname, user, other):
    if other not in user.get('friends', []) and other!='motiz_support': return redirect("/chat")
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        other_user = db.execute(sa.text("SELECT last_seen, name FROM users WHERE nickname=:u"), {"u": other}).mappings().first()
        last_seen_html = format_last_seen(other_user['last_seen']) if other_user else "Unknown"
        if request.method == "POST":
            text = request.form.get("text","").strip()[:700]
            reply_to = request.form.get("reply_to","").strip()[:300]
            if text:
                full_text = f"[Reply to: {reply_to}] {text}" if reply_to else text
                db.execute(sa.text("INSERT INTO dms (from_nickname, to_nickname, text, time, read_by, delivered_to) VALUES (:f, :t, :txt, :tm, '[]', '[]')"), {"f": nickname, "t": other, "txt": full_text, "tm": str(datetime.now(pytz.timezone('Africa/Lagos')))}); db.commit()
            return redirect(f"/dm/{other}")
        db.execute(sa.text("UPDATE dms SET delivered_to = CASE WHEN delivered_to IS NULL OR delivered_to='[]' THEN :d ELSE delivered_to END WHERE to_nickname=:u AND from_nickname=:o"), {"d": json.dumps([other]), "u": nickname, "o": other})
        db.execute(sa.text("UPDATE dms SET read_by = CASE WHEN read_by IS NULL OR read_by='[]' THEN :r ELSE read_by END WHERE to_nickname=:u AND from_nickname=:o"), {"r": json.dumps([nickname]), "u": nickname, "o": other})
        try: db.commit()
        except: pass
        all_msgs = db.execute(sa.text("SELECT * FROM dms WHERE (from_nickname=:a AND to_nickname=:b) OR (from_nickname=:b AND to_nickname=:a) ORDER BY id ASC LIMIT 200"), {"a": nickname, "b": other}).mappings().all()
        msgs_html = ""
        for m in all_msgs:
            cls = "me" if m['from_nickname']==nickname else "other"
            is_me = m['from_nickname']==nickname
            try: read_by = json.loads(m['read_by'] or '[]')
            except: read_by=[]
            try: delivered_to = json.loads(m['delivered_to'] or '[]')
            except: delivered_to=[]
            if is_me:
                if other in read_by: tick = f"<small style='color:#0f3460'>{TICK_SEEN}</small>"
                elif other in delivered_to or True: tick = f"<small style='color:gray'>{TICK_DELIVERED}</small>"
                else: tick = f"<small style='color:gray'>{TICK_SENT}</small>"
            else: tick = ""
            reply_html = ""
            if "[Reply to:" in m['text']:
                try:
                    parts = m['text'].split("] ",1)
                    reply_part = parts[0].replace("[Reply to: ","")
                    main_part = parts[1] if len(parts)>1 else ""
                    reply_html = f"<div style='background:rgba(0,0,0,0.1);border-left:3px solid #0f3460;padding:4px 8px;border-radius:5px;margin-bottom:4px;font-size:0.8rem'>{reply_part}</div>"
                    display_text = main_part
                except: display_text = m['text']
            else: display_text = m['text']
            msgs_html += f"<div class='chat-msg {cls}' onclick=\"replyTo('{m['text'][:100].replace(chr(39),'')}')\"><div class='bubble {cls}'>{reply_html}{display_text}<br><small>{format_12h(m['time'])} {tick}</small></div></div>"
        content = f"<div class=dm-top-actions><span>{other} - {last_seen_html}</span><a href='/chat' class='btn gray' style='width:auto;padding:4px 10px;margin:0'>Back</a></div><div style='margin-top:50px;padding-bottom:80px'>{msgs_html}</div><form method=POST class=chat-input-fixed><div id=replyPreview class=reply-preview style='display:none'><span id=replyPreviewText></span><button type=button onclick='cancelReply()' style='background:red;color:white;border:none;border-radius:50%;width:20px'>X</button></div><div class=chat-input-row><input name=text id=chatInput placeholder='Type message... (max 700)' required autocomplete=off maxlength=700><button class=send-img-btn><img src={SEND_BTN_URL}></button></div><input type=hidden name=reply_to id=replyToInput></form><script>function replyTo(t){{ document.getElementById('replyToInput').value=t; document.getElementById('replyPreviewText').innerText=t; document.getElementById('replyPreview').style.display='flex'; document.getElementById('chatInput').focus(); }} function cancelReply(){{ document.getElementById('replyToInput').value=''; document.getElementById('replyPreview').style.display='none'; }}</script>"
        return render_template_string(BASE, title=f"DM {other}", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")

@app.route('/me')
@login_required
def me_page(nickname, user):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        referral_link = f"{BASE_URL}/register?ref={nickname}"
        ref_count = db.execute(sa.text("SELECT COUNT(*) FROM referrals WHERE referrer=:u"), {"u": nickname}).scalar() or 0
        html = f"<div class=card><h2>👤 {user['name']}</h2><p><b>Nickname:</b> {nickname}</p><p><b>Class:</b> {user['class']} {user.get('dept','')}</p><p><b>Correct:</b> {user.get('correct',0)} | <b>Wrong:</b> {user.get('wrong',0)}</p><p><b>Friends:</b> {len(user.get('friends',[]))}</p><p><b>Referrals:</b> {ref_count}</p><p><b>Verified:</b> {'✅ Paid' if is_user_paid(user) else '❌ Not Paid'}</p><p><b>Referral Link:</b><br><input class=readonly-box readonly value={referral_link}></p><a class=btn blue href=/me/edit>Edit Profile</a><a class=btn red href=/logout>Logout</a></div>"
        return render_template_string(BASE, title="Me", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html), timer_script="")

@app.route('/me/edit', methods=["GET","POST"])
@login_required
def me_edit(nickname, user):
    if request.method == "POST":
        name = request.form.get("name","").strip()[:100]
        password = request.form.get("password","").strip()
        with DBSession() as db:
            if name: db.execute(sa.text("UPDATE users SET name=:n WHERE nickname=:u"), {"n": name, "u": nickname})
            if password and len(password)>=4: db.execute(sa.text("UPDATE users SET password=:p WHERE nickname=:u"), {"p": password, "u": nickname})
            db.commit()
        return redirect("/me")
    content = f"<div class=card><h2>Edit Profile</h2><form method=POST><input name=name value=\"{user['name']}\" placeholder='Full Name'><input name=password type=password placeholder='New Password (leave empty to keep)'><button class=btn blue>Save</button></form></div>"
    return render_template_string(BASE, title="Edit Me", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")

@app.route('/complain', methods=["GET","POST"])
@login_required
def complain_page(nickname, user):
    with DBSession() as db:
        if request.method == "POST":
            text = request.form.get("text","").strip()[:1000]
            if text:
                db.execute(sa.text("INSERT INTO complaints (nickname, name, text) VALUES (:u, :n, :t)"), {"u": nickname, "n": user['name'], "t": text}); db.commit()
                return redirect("/complain")
        my_complaints = db.execute(sa.text("SELECT * FROM complaints WHERE nickname=:u ORDER BY created_at DESC LIMIT 20"), {"u": nickname}).mappings().all()
        complaints_html = ""
        for c in my_complaints:
            reply = f"<div style='background:#e8f5e9;padding:8px;border-radius:8px;margin-top:5px'><b>Admin Reply:</b> {c['reply']}</div>" if c['reply'] else "<small>⏳ Pending reply</small>"
            complaints_html += f"<div class=card><p>{c['text']}</p><small>{format_12h(str(c['created_at']))} - {c['status']}</small>{reply}</div>"
        content = f"<div class=card><h2>📩 Complaint / Suggestion</h2><form method=POST><textarea name=text placeholder='Write your complaint or suggestion... (max 1000)' maxlength=1000 required style='min-height:100px'></textarea><button class=btn blue>Send</button></form></div><h3>My Complaints</h3>{complaints_html if complaints_html else '<p>No complaints yet</p>'}"
        return render_template_string(BASE, title="Complain", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")
@app.route('/admin', methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASS:
            session["is_admin"] = True
            return redirect("/admin/dashboard")
        else:
            return render_template_string(BASE, title="Admin", header="", content=Markup("<div class=card><h2>Admin Login</h2><p style=color:red>Wrong password</p><form method=POST><input type=password name=password placeholder='Admin Password' required><button class=btn>Login</button></form></div>"), timer_script="")
    return render_template_string(BASE, title="Admin", header="", content=Markup("<div class=card><h2>Admin Login</h2><form method=POST><input type=password name=password placeholder='Admin Password' required><button class=btn>Login</button></form></div>"), timer_script="")

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"): return redirect("/admin")
        return f(*args, **kwargs)
    return wrapper

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    with DBSession() as db:
        users_count = db.execute(sa.text("SELECT COUNT(*) FROM users")).scalar() or 0
        payments_pending = db.execute(sa.text("SELECT COUNT(*) FROM payments WHERE status='Pending'")).scalar() or 0
        complaints_pending = db.execute(sa.text("SELECT COUNT(*) FROM complaints WHERE status='Pending'")).scalar() or 0
        html = f"<div class=card><h2>Admin Dashboard</h2><p>Users: {users_count}</p><p>Pending Payments: {payments_pending}</p><p>Pending Complaints: {complaints_pending}</p><a class=btn blue href=/admin/payments>Payments</a><a class=btn blue href=/admin/questions>Questions</a><a class=btn blue href=/admin/lessons>Lessons</a><a class=btn blue href=/admin/notices>Notices</a><a class=btn blue href=/admin/daily>Daily Challenge</a><a class=btn blue href=/admin/complaints>Complaints</a><a class=btn blue href=/admin/users>Users</a><a class=btn blue href=/admin/settings>Settings</a><a class=btn red href=/admin/logout>Logout Admin</a></div>"
        return render_template_string(BASE, title="Admin Dashboard", header="", content=Markup(html), timer_script="")

@app.route('/admin/logout')
def admin_logout():
    session.pop("is_admin", None)
    return redirect("/admin")

@app.route('/admin/payments')
@admin_required
def admin_payments():
    with DBSession() as db:
        payments = db.execute(sa.text("SELECT * FROM payments WHERE status='Pending' ORDER BY id DESC LIMIT 100")).mappings().all()
        html = "<div class=card><h2>Pending Payments</h2></div>"
        for p in payments:
            html += f"<div class=card><b>{p['nickname']}</b> - {p['name']} - {p['type']} - {p['bank_used']} - {p['account_name']} - {p['date_paid']}<br><a class='btn blue' style='width:auto;display:inline-block;padding:5px 10px' href='/admin/verify/{p['id']}'>Verify</a> <a class='btn red' style='width:auto;display:inline-block;padding:5px 10px' href='/admin/reject/{p['id']}'>Reject</a></div>"
        if not payments: html += "<div class=card>No pending payments</div>"
        return render_template_string(BASE, title="Payments", header="", content=Markup(html), timer_script="")

@app.route('/admin/verify/<int:pid>')
@admin_required
def admin_verify(pid):
    with DBSession() as db:
        pay = db.execute(sa.text("SELECT * FROM payments WHERE id=:i"), {"i": pid}).mappings().first()
        if pay:
            db.execute(sa.text("UPDATE payments SET status='Verified' WHERE id=:i"), {"i": pid})
            if pay['type'] == 'lessons':
                db.execute(sa.text("UPDATE users SET lesson_expiry=:d WHERE nickname=:u"), {"d": date.today() + timedelta(days=30), "u": pay['nickname']})
            else:
                db.execute(sa.text("UPDATE users SET is_verified=TRUE, payment_verified_date=:d WHERE nickname=:u"), {"d": str(date.today()), "u": pay['nickname']})
            ref = db.execute(sa.text("SELECT referred_by FROM users WHERE nickname=:u"), {"u": pay['nickname']}).scalar()
            if ref:
                db.execute(sa.text("UPDATE referrals SET paid=TRUE WHERE referred=:u"), {"u": pay['nickname']})
                bonus = db.execute(sa.text("SELECT COUNT(*) FROM referrals WHERE referrer=:r AND paid=TRUE AND bonus_given=FALSE"), {"r": ref}).scalar() or 0
                if bonus >= 3:
                    db.execute(sa.text("UPDATE users SET free_days=free_days+7 WHERE nickname=:u"), {"u": ref})
                    db.execute(sa.text("UPDATE referrals SET bonus_given=TRUE WHERE referrer=:r AND paid=TRUE AND bonus_given=FALSE"), {"r": ref})
            db.commit()
    return redirect("/admin/payments")

@app.route('/admin/reject/<int:pid>')
@admin_required
def admin_reject(pid):
    with DBSession() as db:
        db.execute(sa.text("UPDATE payments SET status='Rejected' WHERE id=:i"), {"i": pid}); db.commit()
    return redirect("/admin/payments")

@app.route('/admin/questions', methods=["GET","POST"])
@admin_required
def admin_questions():
    msg = ""
    if request.method == "POST":
        key = request.form.get("key","").strip()
        q = request.form.get("q","").strip()
        options = [request.form.get(f"opt{i}","").strip() for i in range(1,5)]
        ans = request.form.get("ans","").strip()
        if key and q and all(options) and ans in options:
            with DBSession() as db:
                db.execute(sa.text("INSERT INTO questions (key, q, options, ans) VALUES (:k, :q, :o, :a)"), {"k": key, "q": q, "o": json.dumps(options), "a": ans}); db.commit()
                msg = "<p style=color:green>Added!</p>"
    with DBSession() as db:
        all_keys = db.execute(sa.text("SELECT key, COUNT(*) as c FROM questions GROUP BY key ORDER BY key")).mappings().all()
        keys_html = "".join([f"<p>{k['key']}: {k['c']} questions</p>" for k in all_keys])
        content = f"<div class=card><h2>Add Question (Manual - No Auto)</h2>{msg}<form method=POST><input name=key placeholder='Key e.g SS3_Science_Physics' required><textarea name=q placeholder='Question' required></textarea><input name=opt1 placeholder='Option A' required><input name=opt2 placeholder='Option B' required><input name=opt3 placeholder='Option C' required><input name=opt4 placeholder='Option D' required><input name=ans placeholder='Correct Answer (must match one option)' required><button class=btn blue>Add Question</button></form></div><div class=card><h3>Existing Keys</h3>{keys_html}</div><div class=card><h3>Bulk Upload CSV</h3><p>Format: key,q,opt1,opt2,opt3,opt4,ans</p><form method=POST action=/admin/questions_csv enctype=multipart/form-data><input type=file name=file accept=.csv required><button class=btn orange>Upload CSV</button></form></div>"
        return render_template_string(BASE, title="Questions", header="", content=Markup(content), timer_script="")

@app.route('/admin/questions_csv', methods=["POST"])
@admin_required
def admin_questions_csv():
    file = request.files.get('file')
    if not file: return redirect("/admin/questions")
    try:
        content = file.read().decode('utf-8')
        reader = csv.DictReader(StringIO(content))
        count = 0
        with DBSession() as db:
            for row in reader:
                try:
                    key = row.get('key','').strip()
                    q = row.get('q','').strip()
                    opts = [row.get('opt1','').strip(), row.get('opt2','').strip(), row.get('opt3','').strip(), row.get('opt4','').strip()]
                    ans = row.get('ans','').strip()
                    if key and q and all(opts) and ans:
                        db.execute(sa.text("INSERT INTO questions (key, q, options, ans) VALUES (:k, :q, :o, :a)"), {"k": key, "q": q, "o": json.dumps(opts), "a": ans})
                        count+=1
                except: continue
            db.commit()
    except: count=0
    return render_template_string(BASE, title="CSV Upload", header="", content=Markup(f"<div class=card><h2>Uploaded {count} questions</h2><a class=btn href=/admin/questions>Back</a></div>"), timer_script="")

@app.route('/admin/lessons', methods=["GET","POST"])
@admin_required
def admin_lessons():
    msg=""
    if request.method=="POST":
        c = request.form.get("class","").strip()
        d = request.form.get("dept","").strip()
        subj = request.form.get("subject","").strip()
        title = request.form.get("title","").strip()
        notes = request.form.get("notes","").strip()
        media = request.form.get("media_link","").strip()
        if c and subj and title:
            with DBSession() as db:
                db.execute(sa.text("INSERT INTO lessons (class, dept, subject, title, notes, date, media_link) VALUES (:c, :d, :s, :t, :n, :dt, :m)"), {"c": c, "d": d, "s": subj, "t": title, "n": notes, "dt": str(date.today()), "m": media}); db.commit()
                msg="<p style=color:green>Lesson added!</p>"
    content = f"<div class=card><h2>Add Lesson</h2>{msg}<form method=POST><select name=class required><option value=''>Class</option>{''.join([f'<option>{cc}</option>' for cc in CLASSES])}</select><input name=dept placeholder='Dept e.g Science (leave empty for JSS)'><input name=subject placeholder='Subject e.g Physics' required><input name=title placeholder='Lesson Title' required><textarea name=notes placeholder='Lesson Notes' style='min-height:120px'></textarea><input name=media_link placeholder='Media Link (img/video url optional)'><button class=btn blue>Add Lesson</button></form></div>"
    return render_template_string(BASE, title="Lessons Admin", header="", content=Markup(content), timer_script="")

@app.route('/admin/notices', methods=["GET","POST"])
@admin_required
def admin_notices():
    global NOTICES, PINNED_NOTICE
    if request.method=="POST":
        action = request.form.get("action","")
        if action=="add":
            title = request.form.get("title","").strip()
            text = request.form.get("text","").strip()
            media = request.form.get("media_link","").strip()
            if title and text:
                NOTICES.append({"title": title, "text": text, "media_link": media, "created_at": str(datetime.now(pytz.timezone('Africa/Lagos')))})
                set_setting("notices", json.dumps(NOTICES))
        elif action=="pin":
            title = request.form.get("title","").strip()
            text = request.form.get("text","").strip()
            if title and text:
                PINNED_NOTICE = json.dumps({"title": title, "text": text})
                set_setting("pinned_notice", PINNED_NOTICE)
        elif action=="unpin":
            PINNED_NOTICE=""; set_setting("pinned_notice","")
        elif action=="clear":
            NOTICES=[]; set_setting("notices", json.dumps(NOTICES))
        return redirect("/admin/notices")
    notices_html = "".join([f"<div class=card><b>{n['title']}</b><br>{n['text']}<br><small>{n.get('created_at','')}</small></div>" for n in NOTICES])
    content = f"<div class=card><h2>Notices - {len(NOTICES)}</h2><form method=POST><input type=hidden name=action value=add><input name=title placeholder='Title' required><textarea name=text placeholder='Notice text' required></textarea><input name=media_link placeholder='Media link optional'><button class=btn blue>Add Notice</button></form><form method=POST style='margin-top:10px'><input type=hidden name=action value=pin><input name=title placeholder='Pinned Title' required><textarea name=text placeholder='Pinned Text' required></textarea><button class=btn orange>Pin Notice</button></form><form method=POST style='margin-top:10px'><input type=hidden name=action value=unpin><button class=btn gray>Unpin</button></form><form method=POST style='margin-top:10px'><input type=hidden name=action value=clear><button class=btn red>Clear All Notices</button></form></div>{notices_html}"
    return render_template_string(BASE, title="Notices", header="", content=Markup(content), timer_script="")

@app.route('/admin/daily', methods=["GET","POST"])
@admin_required
def admin_daily():
    msg=""
    if request.method=="POST":
        subj = request.form.get("subject","").strip()
        q = request.form.get("q","").strip()
        opts = [request.form.get(f"opt{i}","").strip() for i in range(1,5)]
        ans = request.form.get("ans","").strip()
        if subj and q and all(opts) and ans:
            with DBSession() as db:
                db.execute(sa.text("INSERT INTO daily_challenge (day, subject, q, options, ans) VALUES (:d, :s, :q, :o, :a)"), {"d": str(date.today()), "s": subj, "q": q, "o": json.dumps(opts), "a": ans}); db.commit()
                msg="<p style=color:green>Added to today!</p>"
    with DBSession() as db:
        today_q = db.execute(sa.text("SELECT COUNT(*) FROM daily_challenge WHERE day=:d"), {"d": str(date.today())}).scalar() or 0
    content = f"<div class=card><h2>Daily Challenge - Today: {today_q}/10</h2>{msg}<form method=POST><input name=subject placeholder='Subject e.g Mathematics' required><textarea name=q placeholder='Question' required></textarea><input name=opt1 placeholder='Option A' required><input name=opt2 placeholder='Option B' required><input name=opt3 placeholder='Option C' required><input name=opt4 placeholder='Option D' required><input name=ans placeholder='Correct Answer' required><button class=btn orange>Add to Today</button></form></div>"
    return render_template_string(BASE, title="Daily Admin", header="", content=Markup(content), timer_script="")

@app.route('/admin/complaints')
@admin_required
def admin_complaints():
    with DBSession() as db:
        complaints = db.execute(sa.text("SELECT * FROM complaints ORDER BY created_at DESC LIMIT 100")).mappings().all()
        html = "<div class=card><h2>Complaints</h2></div>"
        for c in complaints:
            reply_form = f"<form method=POST action='/admin/complaint_reply/{c['id']}'><textarea name=reply placeholder='Reply...' required>{c['reply'] or ''}</textarea><button class=btn blue style='padding:5px'>Reply</button></form>"
            html += f"<div class=card><b>{c['nickname']}</b> - {c['name']}<br>{c['text']}<br><small>{c['created_at']} - {c['status']}</small>{reply_form}</div>"
        return render_template_string(BASE, title="Complaints", header="", content=Markup(html), timer_script="")

@app.route('/admin/complaint_reply/<int:cid>', methods=["POST"])
@admin_required
def admin_complaint_reply(cid):
    reply = request.form.get("reply","").strip()
    with DBSession() as db:
        db.execute(sa.text("UPDATE complaints SET reply=:r, status='Replied' WHERE id=:i"), {"r": reply, "i": cid}); db.commit()
    return redirect("/admin/complaints")

@app.route('/admin/users')
@admin_required
def admin_users():
    q = request.args.get('q','').strip()
    with DBSession() as db:
        if q:
            users = db.execute(sa.text("SELECT * FROM users WHERE LOWER(nickname) LIKE :qq OR LOWER(name) LIKE :qq ORDER BY id DESC LIMIT 50"), {"qq": f"%{q.lower()}%"}).mappings().all()
        else:
            users = db.execute(sa.text("SELECT * FROM users ORDER BY id DESC LIMIT 100")).mappings().all()
        html = f"<div class=card><h2>Users - {len(users)}</h2><form method=GET><input name=q value='{q}' placeholder='Search nickname/name'><button class=btn blue>Search</button></form></div>"
        for u in users:
            blocked = " - BLOCKED" if u['nickname'] in MOTIZ_PROTECTED else ""
            if u['nickname'] in MOTIZ_PROTECTED:
                action_btn = "<span class=badge gold>Protected</span>"
            else:
                action_btn = f"<a class='btn red' style='width:auto;display:inline-block;padding:5px 10px' href='/admin/block/{u['nickname']}'>Block</a> <a class='btn blue' style='width:auto;display:inline-block;padding:5px 10px' href='/admin/verify_user/{u['nickname']}'>Verify</a> <a class='btn gray' style='width:auto;display:inline-block;padding:5px 10px' href='/admin/delete_user/{u['nickname']}'>Delete</a>"
            html += f"<div class=card><b>{u['nickname']}</b> - {u['name']} - {u['class']} {u.get('dept','')} - Correct:{u.get('correct',0)} {blocked}<br>{action_btn}</div>"
        return render_template_string(BASE, title="Users", header="", content=Markup(html), timer_script="")

@app.route('/admin/block/<nick>')
@admin_required
def admin_block(nick):
    if nick in MOTIZ_PROTECTED: return redirect("/admin/users")
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET is_verified=FALSE WHERE nickname=:u"), {"u": nick}); db.commit()
    return redirect("/admin/users")

@app.route('/admin/verify_user/<nick>')
@admin_required
def admin_verify_user(nick):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET is_verified=TRUE, payment_verified_date=:d WHERE nickname=:u"), {"d": str(date.today()), "u": nick}); db.commit()
    return redirect("/admin/users")

@app.route('/admin/delete_user/<nick>')
@admin_required
def admin_delete_user(nick):
    if nick in MOTIZ_PROTECTED: return redirect("/admin/users")
    with DBSession() as db:
        db.execute(sa.text("DELETE FROM users WHERE nickname=:u"), {"u": nick}); db.commit()
    return redirect("/admin/users")

@app.route('/admin/settings', methods=["GET","POST"])
@admin_required
def admin_settings():
    global ADMIN_PASS
    if request.method=="POST":
        new_pass = request.form.get("admin_pass","").strip()
        if new_pass:
            ADMIN_PASS=new_pass; set_setting("admin_pass", new_pass)
    content = f"<div class=card><h2>Settings</h2><p>Current Admin Pass: {ADMIN_PASS}</p><form method=POST><input name=admin_pass placeholder='New Admin Password' required><button class=btn blue>Change Password</button></form></div>"
    return render_template_string(BASE, title="Settings", header="", content=Markup(content), timer_script="")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))