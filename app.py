from flask import Flask, render_template_string, request, redirect, session, Response
from markupsafe import Markup
from datetime import date, datetime, timedelta
import random, json, os, urllib.parse, csv, math
from io import StringIO
from functools import wraps
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import pytz

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', "motiz_secret_key_2026_v32")
app.config['PROPAGATE_EXCEPTIONS'] = True

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise Exception("DATABASE_URL environment variable is not set")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = sa.create_engine(DATABASE_URL)
DBSession = sessionmaker(bind=engine)

# ====== SETTINGS - V32 CRS/IRS SEPARATED + ALL FEATURES ======
PALMPAY_ACCOUNT = "8908025244"
PALMPAY_NAME = "HAMZAT KOLADE AJIMOTI"
PALMPAY_BANK = "PALMPAY"
LESSON_PRICE = 1000
QUESTION_PRICE = 500
ADMIN_PASS = os.environ.get('ADMIN_PASS', "24434")
FREE_Q = 10
PAID_Q = 70
BATCH_SIZE = 10
NIGERIA_TZ = pytz.timezone('Africa/Lagos')
FAVICON_URL = "https://i.imgur.com/5TCBgkN.png"
SEND_BTN_URL = "https://i.imgur.com/ADGwy5l.png"
BASE_URL = "https://motiz-e-learning-institution.onrender.com"

# ADS - 15 SEC REFRESH
FIXED_AD_KEY = "f0869e31689755e244912b438511f4a9"
NATIVE_FEED_SRC = "https://pl31392647.profitableratecpmnetwork.com/1b/30/4d/1b304d26da2adb6df287de5560168dca.js"
AD_REFRESH_SECONDS = 15

# FEATURES
FRIENDS_BATCH = 5
TICK_SENT = "✓ Sent"
TICK_DELIVERED = "✓✓ Delivered"
TICK_SEEN = "✓✓ Seen"

CALC_SUBJECTS = ["Mathematics", "Physics", "Chemistry", "Further Mathematics", "Financial Accounting", "Economics", "Biology"]

# ===== CRS / IRS SEPARATED NOW =====
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

SUBJECT_EMOJI = {
    "Mathematics": "📐", "Further Mathematics": "📏", "Physics": "⚛️", "Chemistry": "🧑‍🔬", "Biology": "🧬",
    "English Language": "📝", "Economics": "📊", "Financial Accounting": "💰", "Commerce": "🏪", "Business Management": "📈",
    "Literature in English": "📚", "Government": "🏛️", "Christian Religious Studies": "✝️", "Christian Religious Studies (CRS)": "✝️",
    "Islamic Religious Studies": "☪️", "Islamic Religious Studies (IRS)": "☪️", "Yoruba": "🗣️", "ICT": "💻", "Computer Studies / ICT": "💻",
    "Agricultural Science": "🌾", "Geography": "🌍", "Basic Science": "🔬", "Basic Technology": "🔧", "Social Studies": "🌐",
    "Civic Education": "⚖️", "Business Studies": "💼", "Physical and Health Education": "⚽", "Marketing": "📢", "History": "📜", "Craft": "🎨"
}
def subj_emoji(s):
    for k,v in SUBJECT_EMOJI.items():
        if k.lower() in s.lower() or s.lower() in k.lower():
            return v
    return "📖"

def init_db():
    with engine.connect() as conn:
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, nickname TEXT UNIQUE, name TEXT, password TEXT, class TEXT, dept TEXT, q_cycle TEXT DEFAULT 'free', q_used INTEGER DEFAULT 0, free_questions_used INTEGER DEFAULT 0, lesson_expiry DATE, correct INTEGER DEFAULT 0, wrong INTEGER DEFAULT 0, friends TEXT DEFAULT '[]', referred_by TEXT DEFAULT NULL, referral_count INTEGER DEFAULT 0, free_days INTEGER DEFAULT 0, is_verified BOOLEAN DEFAULT FALSE, payment_verified_date TEXT, last_seen TIMESTAMP);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS payments (id SERIAL PRIMARY KEY, nickname TEXT, name TEXT, type TEXT, status TEXT, bank_used TEXT, account_name TEXT, date_paid TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS friend_requests (id SERIAL PRIMARY KEY, from_nickname TEXT, to_nickname TEXT, status TEXT DEFAULT 'Pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, nickname TEXT, name TEXT, text TEXT, likes TEXT DEFAULT '[]', comments TEXT DEFAULT '[]', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS dms (id SERIAL PRIMARY KEY, from_nickname TEXT, to_nickname TEXT, text TEXT, time TEXT, read_by TEXT DEFAULT '[]', delivered_to TEXT DEFAULT '[]');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS groups (id SERIAL PRIMARY KEY, name TEXT, creator TEXT, members TEXT DEFAULT '[]', messages TEXT DEFAULT '[]');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS lessons (id SERIAL PRIMARY KEY, class TEXT, dept TEXT, subject TEXT, title TEXT, notes TEXT, date TEXT, media_link TEXT DEFAULT '');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS questions (id SERIAL PRIMARY KEY, key TEXT, q TEXT, options TEXT, ans TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS referrals (id SERIAL PRIMARY KEY, referrer TEXT, referred TEXT, paid BOOLEAN DEFAULT FALSE, bonus_given BOOLEAN DEFAULT FALSE);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS cbt_progress (id SERIAL PRIMARY KEY, nickname TEXT, subject_key TEXT, used INTEGER DEFAULT 0, UNIQUE(nickname, subject_key));"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS notices (id SERIAL PRIMARY KEY, title TEXT, text TEXT, media_link TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS complaints (id SERIAL PRIMARY KEY, nickname TEXT, name TEXT, text TEXT, reply TEXT DEFAULT '', status TEXT DEFAULT 'Pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.commit()
init_db()

def fix_old_users():
    with DBSession() as db:
        cols = [("users","free_questions_used","INTEGER DEFAULT 0"),("users","q_used","INTEGER DEFAULT 0"),("users","correct","INTEGER DEFAULT 0"),("users","wrong","INTEGER DEFAULT 0"),("users","referral_count","INTEGER DEFAULT 0"),("users","free_days","INTEGER DEFAULT 0"),("users","friends","TEXT DEFAULT '[]'"),("users","referred_by","TEXT"),("users","payment_verified_date","TEXT"),("users","lesson_expiry","DATE"),("users","is_verified","BOOLEAN DEFAULT FALSE"),("users","last_seen","TIMESTAMP"),("dms","delivered_to","TEXT DEFAULT '[]'"),("lessons","media_link","TEXT DEFAULT ''")]
        for table,col,typ in cols:
            try:
                db.execute(sa.text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {typ}"))
                db.commit()
            except:
                db.rollback()
        try:
            db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE last_seen IS NULL"))
            db.commit()
        except:
            db.rollback()
fix_old_users()

def ensure_motiz_support():
    with DBSession() as db:
        exists = db.execute(sa.text("SELECT nickname FROM users WHERE nickname='motiz_support'")).scalar()
        if not exists:
            db.execute(sa.text("INSERT INTO users (nickname,name,password,class,dept,friends,is_verified,last_seen) VALUES ('motiz_support','MOTIZ SUPPORT','motiz_support_2026','SS3','Science','[]',TRUE,NOW()) ON CONFLICT (nickname) DO NOTHING"))
            db.commit()
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
        db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname='motiz_support'"), {"f": json.dumps(all_nicks)})
        db.commit()
ensure_motiz_support()

def get_setting(key, default=""):
    with DBSession() as db:
        val = db.execute(sa.text("SELECT value FROM settings WHERE key=:k"), {"k": key}).scalar()
        return val if val is not None else default
def set_setting(key, value):
    with DBSession() as db:
        db.execute(sa.text("INSERT INTO settings (key, value) VALUES (:k, :v) ON CONFLICT (key) DO UPDATE SET value=:v"), {"k": key, "v": value})
        db.commit()

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
        return nickname, user

def delete_old_posts_and_notices():
    global NOTICES
    cutoff = datetime.now(pytz.timezone('Africa/Lagos')) - timedelta(hours=24)
    with DBSession() as db:
        db.execute(sa.text("DELETE FROM posts WHERE created_at < :c"), {"c": cutoff})
        db.commit()
    new_notices = []
    for n in NOTICES:
        try:
            notice_time = datetime.fromisoformat(n.get('created_at').replace('Z','+00:00'))
            if notice_time > cutoff: new_notices.append(n)
        except: new_notices.append(n)
    if len(new_notices)!= len(NOTICES):
        NOTICES = new_notices
        set_setting("notices", json.dumps(NOTICES))

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
        diff = now - dt
        secs = diff.total_seconds()
        if secs < 300: return "<span style='color:green;font-weight:bold'>● Online now</span>"
        mins = int(secs // 60)
        if mins < 60: return f"{mins}m ago"
        hours = mins // 60
        if hours < 24: return f"{hours}h ago"
        days = hours // 24
        return f"{days}d ago"
    except:
        return "Unknown"

BASE = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/png" href="{FAVICON_URL}">
<link rel="manifest" href="/manifest.json">
<title>{{{{title}}}}</title><style>
:root{{--bg:#f0f2f5;--card:white;--text:#333;--primary:#0f3460}} body.dark{{--bg:#121212;--card:#1e1e1e;--text:#eee}}
body{{font-family:Segoe UI;background:var(--bg);color:var(--text);margin:0;padding:0;padding-bottom:70px}}
.header{{background:var(--primary);color:white;padding:6px 10px;text-align:center;position:fixed;top:0;width:100%;z-index:1000;display:flex;justify-content:space-between;align-items:center;height:50px;box-sizing:border-box}}
.header h1{{margin:0;font-size:0.80rem;flex:1;text-align:center;line-height:1.1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.header img.logo{{width:45px;height:45px;border-radius:50%;margin-left:5px}}
.theme-btn{{border:none;background:transparent;color:white;font-size:1.2rem;cursor:pointer;margin-right:10px}}
.exit-btn{{background:transparent;color:white;border:none;padding:5px 10px;text-decoration:none;font-size:1.3rem;margin-left:10px}}
.nav{{display:flex;gap:5px;background:#16213e;padding:5px;flex-wrap:wrap;position:fixed;top:50px;width:100%;overflow-x:auto;z-index:999}}
.nav a{{color:white;text-decoration:none;padding:5px 8px;border-radius:10px;border:1px solid #fff3;font-size:0.8rem}}
.container{{padding:10px;padding-top:105px;padding-bottom:30px}}
.card{{background:var(--card);padding:12px;margin:8px 0;border-radius:10px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}}
.card:last-child{{margin-bottom:80px !important}}
.btn{{background:#28a745;color:white;padding:12px 15px;text-decoration:none;border-radius:8px;display:block;margin:8px 0;text-align:center;font-weight:bold;border:none;width:100%;cursor:pointer}}
.btn.red{{background:#e94560}}.btn.blue{{background:#0f3460;color:white;border:1px solid white}}.btn.orange{{background:#ff9800}}.btn.gray{{background:#0f3460;color:white;font-size:0.9rem;padding:10px;margin:6px 0;border:1px solid #fff2}}
input,select,textarea{{width:100%;padding:10px;margin:5px 0;border-radius:5px;border:1px solid #ccc;box-sizing:border-box;font-size:1rem;background:var(--card);color:var(--text)}}
.success{{color:green;background:#d4edda;padding:10px;border-radius:5px}}.error{{color:red;background:#f8d7da;padding:10px;border-radius:5px}}
.badge{{background:#1DA1F2;color:white;padding:2px 6px;border-radius:10px;font-size:0.7rem;margin-left:5px}}
.notice-title{{font-size:1.1rem;font-weight:bold;color:var(--primary);margin-bottom:5px}}
.timer{{background:#e94560;color:white;padding:12px;text-align:center;border-radius:8px;font-weight:bold;font-size:1.1rem;margin-bottom:10px;position:sticky;top:105px;z-index:998}}
.option{{background:#f0f2f5;padding:14px;margin:10px 0;border-radius:8px;border:1px solid #ddd;color:black;display:flex;align-items:flex-start;gap:10px}}
.option input{{margin-top:4px;flex-shrink:0;width:18px;height:18px}}
.option span{{flex:1;line-height:1.4;word-break:break-word}}
.chat-msg{{display:flex;margin:8px 0;align-items:flex-end;gap:8px}}.chat-msg.me{{justify-content:flex-end}}.chat-msg.other{{justify-content:flex-start}}
.bubble{{display:flex;flex-direction:column;padding:10px 14px;border-radius:18px;max-width:70%;box-shadow:0 1px 1px rgba(0,0,0,0.1)}}
.me.bubble{{background:#2196f3!important;color:white!important;border-bottom-right-radius:4px}}
.other.bubble{{background:#e0e0e0;color:#333;border-bottom-left-radius:4px}}body.dark .other.bubble{{background:#333;color:#eee}}
.bubble-text{{margin-bottom:4px;word-wrap:break-word}}
.bubble-time{{font-size:11px;opacity:0.8;align-self:flex-end;margin-top:2px;display:flex;gap:6px;align-items:center}}
.tick-seen{{color:#4fc3f7;font-weight:bold}} .tick-delivered{{color:#e0e0e0}} .tick-sent{{color:#ccc}}
.chat-avatar{{width:32px;height:32px;border-radius:50%;background:var(--primary);color:white;display:flex;align-items:center;justify-content:center;font-size:0.8rem;font-weight:bold}}
.friend-card{{display:flex;align-items:center;gap:10px;padding:12px;background:var(--card);border-radius:10px;margin:8px 0;text-decoration:none;color:var(--text)}}
.friend-avatar{{width:45px;height:45px;border-radius:50%;background:var(--primary);color:white;display:flex;align-items:center;justify-content:center;font-weight:bold}}
.notification{{position:absolute;top:-5px;right:-5px;background:red;color:white;border-radius:50%;width:18px;height:18px;font-size:0.7rem;display:flex;align-items:center;justify-content:center}}
.readonly-box{{width:100%;padding:12px;background:#eee;border:1px dashed #999;font-size:1.1rem;font-weight:bold;text-align:center;user-select:all}}
.chat-input-fixed{{position:fixed;bottom:65px;left:10px;right:10px;display:flex;gap:5px;background:var(--card);padding:10px;border-radius:15px;box-shadow:0 -2px 10px rgba(0,0,0,0.1);z-index:999}}
.send-img-btn{{background:transparent;border:none;padding:0;cursor:pointer}}
.send-img-btn img{{height:40px;width:40px}}
.lesson-media{{width:100%;border-radius:10px;margin-top:8px;max-height:350px;object-fit:contain}}
.motiz-support{{border:2px solid #1DA1F2;background:#e8f5fe !important;font-weight:bold}}
.motiz-support .bubble-text{{font-family:monospace;font-weight:bold;color:#0f3460}}
#fixedAdBar{{position:fixed;bottom:0;left:0;width:100%;height:60px;background:white;z-index:99999;border-top:1px solid #ddd;display:flex;align-items:center;justify-content:center;overflow:hidden}}
#updateBanner{{display:none;position:fixed;top:0;left:0;width:100%;background:#ff9800;color:white;padding:10px;text-align:center;z-index:100001}}
a{{text-decoration:none;color:#2563eb}} a:visited{{color:#2563eb}}
.cbt-btn-fix{{display:block;width:100%;box-sizing:border-box;white-space:normal;line-height:1.3;padding:10px 8px;font-size:0.85rem;word-break:break-word}}
.cbt-btn-fix small{{display:block;font-size:0.75rem;opacity:0.9;margin-top:3px}}
.calc-float{{position:fixed;bottom:80px;right:10px;background:#0f3460;color:white;padding:10px;border-radius:10px;z-index:9998;width:220px;display:none}}
</style></head><body>
<div id="updateBanner">🔄 New version available - <button onclick="location.reload(true)" style="background:white;color:#ff9800;border:none;padding:5px 10px;border-radius:5px;font-weight:bold;">Update now</button></div>
{{{{header}}}}<div class="container">{{{{content}}}}</div>
<div id="fixedAdBar">
  <button onclick="document.getElementById('fixedAdBar').style.display='none';document.body.style.paddingBottom='0px'" style="position:absolute;top:2px;right:5px;z-index:100000;background:#000;color:#fff;border:none;border-radius:50%;width:20px;height:20px;cursor:pointer;font-size:11px;">X</button>
  <div id="adContainer" style="width:728px;max-width:100%;height:60px;display:flex;align-items:center;justify-content:center;">
    <script>atOptions = {{'key' : 'f0869e31689755e244912b438511f4a9','format' : 'iframe','height' : 60,'width' : 728,'params' : {{}} }};</script>
    <script src="https://www.highrevenueformat.com/f0869e31689755e244912b438511f4a9/invoke.js"></script>
  </div>
</div>
<script>
{{{{timer_script}}}}
if(window.location.pathname.startsWith('/exam') || window.location.pathname.startsWith('/cbt/')){{
  var ad=document.getElementById('fixedAdBar'); if(ad) ad.style.display='none'; document.body.style.paddingBottom='0px';
  var chatInput=document.querySelector('.chat-input-fixed'); if(chatInput) chatInput.style.bottom='10px';
}}
let initialHeight = window.innerHeight;
window.addEventListener('resize', function(){{
  let ad=document.getElementById('fixedAdBar'); if(!ad) return;
  if(window.innerHeight < initialHeight - 150){{ ad.style.display='none'; }}
  else{{
    if(!window.location.pathname.startsWith('/exam') && !window.location.pathname.startsWith('/cbt/')){{
      ad.style.display='flex'; document.body.style.paddingBottom='70px';
    }}
  }}
}});
let adRefreshInterval = {AD_REFRESH_SECONDS} * 1000;
setInterval(function(){{
  let adContainer = document.getElementById('adContainer');
  let adBar = document.getElementById('fixedAdBar');
  if(adBar && adBar.style.display !== 'none' && !document.hidden){{
    try{{
      let newScript = document.createElement('script');
      newScript.src = 'https://www.highrevenueformat.com/{FIXED_AD_KEY}/invoke.js';
      adContainer.appendChild(newScript);
    }}catch(e){{}}
  }}
}}, adRefreshInterval);
if('serviceWorker' in navigator){{ navigator.serviceWorker.register('/sw.js').then(reg=>{{ reg.onupdatefound=()=>{{ document.getElementById('updateBanner').style.display='block'; }} }}); }}
</script>
</body></html>"""

def get_header(nickname,user, show_nav=True, show_favicon=False):
    if not user: return ""
    exit_html = '<a href="/main" class="exit-btn">🔙</a>' if not show_favicon else ""
    favicon_html = f'<img src="{FAVICON_URL}" class="logo">' if show_favicon else ""
    theme_html = '<button class="theme-btn" onclick="document.body.classList.toggle(\'dark\')">🌙</button>'
    is_support = nickname=='motiz_support' or user.get('nickname')=='motiz_support'
    if is_support:
        verified = '<span class=badge>✓ MOTIZ SUPPORT</span>'
    else:
        verified = '<span class=badge>✓ Verified</span>' if user.get('is_verified') else ""
    nav_html = """<div class="nav"><a href="/main">🏠 Home</a><a href="/exam">✍️ CBT</a><a href="/lessons">🎓 Lessons</a><a href="/community">🌍 Community</a><a href="/chat">💬 Chat</a><a href="/me">👤 Me</a><a href="/complain">📩 Complain</a></div>""" if show_nav else ""
    return f"""<div class="header">{favicon_html}{exit_html}<h1>MOTIZ E-LEARNING {verified}</h1>{theme_html}</div>{nav_html}"""
@app.route('/manifest.json')
def manifest():
    return Response(json.dumps({"name":"MOTIZ E-LEARNING","short_name":"MOTIZ","start_url":"/main","display":"standalone","background_color":"#0f3460","theme_color":"#0f3460","icons":[{"src":FAVICON_URL,"sizes":"192x192","type":"image/png"}]}), mimetype='application/json')

@app.route('/sw.js')
def sw():
    return Response("self.addEventListener('install', e=>self.skipWaiting()); self.addEventListener('activate', e=>self.clients.claim()); self.addEventListener('fetch', e=>{e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)))});", mimetype='application/javascript')

@app.route('/')
def splash():
    return render_template_string(f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Welcome</title><link rel="icon" type="image/png" href="{FAVICON_URL}"><meta http-equiv="refresh" content="10;url=/login">
<style>body{{margin:0;background:linear-gradient(135deg,#0f3460,#16213e);color:white;font-family:Segoe UI;display:flex;justify-content:center;align-items:center;height:100vh;flex-direction:column;text-align:center;overflow:hidden;position:relative}}
.logo{{font-size:2.8rem;font-weight:bold;animation:glow 2s ease-in-out infinite alternate;line-height:1.2;z-index:10;margin-top:120px}}
.subtext{{font-size:1.1rem;margin-top:10px;opacity:0.9;z-index:10}}
.progress-bar{{width:200px;height:8px;background:#fff3;border-radius:10px;overflow:hidden;margin-top:20px}}
.progress-fill{{height:100%;width:0%;background:white;animation:load 10s linear forwards}}
@keyframes load{{0%{{width:0%}}100%{{width:100%}}}}
@keyframes glow{{from{{text-shadow:0 0 10px #fff}}to{{text-shadow:0 0 30px #2196f3}}}}
.bulb{{position:absolute;top:35%;left:50%;transform:translate(-50%,-50%);font-size:4rem;z-index:10}}
</style></head><body>
<div class="bulb">📖</div>
<div class="logo">MOTIZ E-LEARNING INSTITUTION</div><div class="subtext">Learn. Practice. Excel.</div><div class="progress-bar"><div class="progress-fill"></div></div></body></html>""")

@app.route('/register', methods=["GET","POST"])
def register():
    if get_user()[1]: return redirect("/main")
    error = ""; ref = request.args.get('ref')
    # BLOCK motiz_support RESERVED
    if request.method == "POST":
        nickname = request.form.get("nickname","").strip().lower()
        if nickname == 'motiz_support':
            error = "<div class=error>Nickname reserved</div>"
        else:
            with DBSession() as db:
                exists = db.execute(sa.text("SELECT nickname FROM users WHERE nickname=:u"), {"u": nickname}).scalar()
                if exists: error = "<div class=error>Nickname taken</div>"
                else:
                    name = f"{request.form['surname']} {request.form['other']}"
                    db.execute(sa.text("INSERT INTO users (nickname,name,password,class,dept,referred_by,last_seen) VALUES (:u,:n,:p,:c,:d,:r,NOW())"),
                               {"u": nickname, "n": name, "p": request.form['password'], "c": request.form['class'], "d": request.form.get('dept',''), "r": ref})
                    if ref: db.execute(sa.text("INSERT INTO referrals (referrer, referred) VALUES (:r, :ref)"), {"r": ref, "ref": nickname})
                    db.commit()
                    session["nickname"] = nickname; return redirect("/main")
    js = """<script>function d(){let c=document.getElementById('class').value;let x=document.getElementById('dept');x.innerHTML='';if(['SS1','SS2','SS3'].includes(c)){x.innerHTML='<label>Department *</label><select name=dept id=dept required><option value="">Select Department</option><option>Science</option><option>Commercial</option><option>Art</option></select>'}else{x.innerHTML='<input type=hidden name=dept value=>';}}</script>"""
    form = f"<div class='card'><h2>Register</h2>{error}<form method=POST><input name=nickname placeholder='Nickname' required><input name=surname placeholder='Surname' required><input name=other placeholder='Other Name' required><input type=password name=password placeholder='Password' required><select name=class id=class onchange=d() required><option value=''>Select Class</option>{''.join([f'<option>{c}</option>' for c in CLASSES])}</select><div id=dept></div><button class=btn>Register</button><p>Already have account? <a href=/login>Login</a></p></form></div>{js}"
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
            else: error = "<div class=error>Invalid Nickname or Password</div>"
    return render_template_string(BASE, title="Login", header="", content=Markup(f"<div class='card'><h2>Login</h2>{error}<form method=POST><input name=nickname placeholder='Nickname' required><input type=password name=password placeholder=Password required><button class=btn>Login</button><a class=btn.blue href=/register>Register</a></form></div>"), timer_script="")

@app.route('/main')
@login_required
def main(nickname, user):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname})
        db.commit()
    pinned_html = ""
    if PINNED_NOTICE:
        try: pin = json.loads(PINNED_NOTICE); pinned_html = f"<div class='card' style='border:2px solid gold'><div class=notice-title>📌 {pin['title']}</div>{pin['text']}</div>"
        except: pinned_html = f"<div class='card' style='border:2px solid gold'><b>📌 PINNED:</b> {PINNED_NOTICE}</div>"
    notices_html = ""
    for n in NOTICES:
        media = ""
        if n.get('media_link'):
            link = n['media_link']
            if any(x in link.lower() for x in ['.mp4','.webm','video']):
                media = f"<video src='{link}' controls class='lesson-media' onerror=\"this.parentElement.innerHTML='<a href={link} target=_blank>📹 Watch Video</a>'\"></video>"
            else:
                media = f"<img src='{link}' class='lesson-media' onerror=\"this.style.display='none'\">"
        notices_html += f"<div class='card'><div class=notice-title>📢 {n['title']}</div>{n['text']}{media}<small style='float:right'>{n.get('created_at','')[:16]}</small></div>"
    return render_template_string(BASE, title="Home", header=Markup(get_header(nickname,user, show_nav=True, show_favicon=True)), content=Markup(f"<div class='card'><h2>Welcome {user['name']}</h2><p><b>Class:</b> {user['class']} {user.get('dept','')}</p></div>{pinned_html}<h3>General Notice</h3>{notices_html}<a class=btn href=/exam>Start CBT Exam</a><a class=btn.blue href=/complain>📩 Complain to Admin (3/week)</a>"), timer_script="")

@app.route('/logout')
def logout():
    session.clear()
    return redirect("/login")

@app.route('/exam')
@login_required
def exam(nickname, user):
    key = f"{user['class']}_{user['dept']}" if user['dept'] else user['class']
    subs = SUBJECTS.get(key, [])
    if not subs: return render_template_string(BASE, title="Error", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup("<div class=error>No subjects for your class yet</div>"), timer_script="")
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
            limit = FREE_Q if not user.get('is_verified') else FREE_Q + PAID_Q
            done = min(prog, total_q, limit)
            emoji = subj_emoji(s)
            if done >= limit or (total_q>0 and done >= total_q):
                btn = f"<div class='card' style='border:2px solid #28a745'><b>{emoji} {s}</b><br><small>✅ Completed {done}/{min(limit,total_q)}</small><br><a class='btn blue cbt-btn-fix' href='/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(s)}?redo=1'>🔄 Redo / Reset</a></div>"
            else:
                remain_free = max(0, FREE_Q - prog) if not user.get('is_verified') else 0
                if not user.get('is_verified') and prog >= FREE_Q:
                    btn = f"<div class='card cbt-btn-fix' style='border:2px solid #e94560'><b>{emoji} {s}</b><br><small>🔒 Pay to continue (10/{FREE_Q} free done)</small><br><a class='btn red cbt-btn-fix' href='/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(s)}'>Unlock - Pay ₦{QUESTION_PRICE}</a></div>"
                else:
                    btn = f"<a class='btn blue cbt-btn-fix' href='/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(s)}'><span>{emoji} {s}</span><small>{done}/{min(limit,total_q)} done | Free left: {remain_free}</small></a>"
            sub_btns += btn
    if not user.get('is_verified'):
        with DBSession() as db:
            pending = db.execute(sa.text("SELECT * FROM payments WHERE nickname=:u AND type='questions' AND status='Pending'"), {"u": nickname}).scalar()
        if pending:
            sub_btns = "<div class='card'><h2>⏳ Payment Under Review</h2><p>Admin verifying - you will get 70 more per subject once approved.</p></div>" + sub_btns
    return render_template_string(BASE, title="CBT", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class='card'><h2>Subjects for {user['class']} {user.get('dept','')}</h2><p>10 FREE per subject. Shuffle + Smart timer. CRS/IRS now separated.</p>{sub_btns}</div>"), timer_script="")

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
            return render_template_string(BASE, title="Error", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>😕 No Questions Yet for {subj_emoji(sub)} {sub}</h2><a class=btn.blue href=/exam>Back</a></div>"), timer_script="")
        prog = db.execute(sa.text("SELECT used FROM cbt_progress WHERE nickname=:u AND subject_key=:k"), {"u": nickname, "k": full_key}).scalar()
        if prog is None:
            db.execute(sa.text("INSERT INTO cbt_progress (nickname, subject_key, used) VALUES (:u, :k, 0) ON CONFLICT (nickname, subject_key) DO NOTHING"), {"u": nickname, "k": full_key})
            db.commit()
            prog = 0
    total_limit = FREE_Q + PAID_Q if user.get('is_verified') else FREE_Q
    if prog >= total_limit or prog >= all_count:
        if not user.get('is_verified') and prog >= FREE_Q:
            with DBSession() as db: pending = db.execute(sa.text("SELECT * FROM payments WHERE nickname=:u AND type='questions' AND status='Pending'"), {"u": nickname}).scalar()
            if pending:
                content = "<div class=card><h2>⏳ Payment Under Review</h2><p>Admin verifying.</p></div>"
            else:
                content = f'<div class=card><h2>🔒 Unlock 70 More Questions for {subj_emoji(sub)} {sub}</h2><p><b>Pay &#8358;{QUESTION_PRICE} for 30 days</b></p><p><b>Bank:</b> {PALMPAY_BANK}<br><b>Account:</b><input class=readonly-box readonly value="{PALMPAY_ACCOUNT}"><br><b>Name:</b> {PALMPAY_NAME}</p><form method=POST action=/confirm/questions><input name=bank_used placeholder="Bank you used" required><input name=account_name placeholder="Account Name" required><button class="send-img-btn"><img src="{SEND_BTN_URL}"></button></form><a class=btn.blue href="/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(sub)}?redo=1">🔄 Redo Free 10</a></div>'
            return render_template_string(BASE, title="Paywall", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")
    start_index = prog
    end_index = min(start_index + BATCH_SIZE, total_limit, all_count)
    with DBSession() as db:
        batch_q = db.execute(sa.text(f"SELECT * FROM questions WHERE key=:k ORDER BY RANDOM() LIMIT :limit OFFSET :off"), {"k": full_key, "limit": end_index-start_index, "off": start_index}).mappings().all()
    questions = [dict(q) for q in batch_q]
    for q in questions: q['options'] = json.loads(q['options'])
    if not questions:
        return render_template_string(BASE, title="Done", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>✅ Completed {sub}</h2><a class=btn href=/exam>Back</a><a class=btn.blue href='/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(sub)}?redo=1'>🔄 Redo</a></div>"), timer_script="")
    time_per_q = 60 if sub in CALC_SUBJECTS else 30
    batch_time = len(questions) * time_per_q
    if request.method == "POST":
        score = 0; result_html = "";
        for i,q in enumerate(questions):
            user_ans = request.form.get(f"q{i}")
            if user_ans == q["ans"]: score += 1
            result_html += f"<div class='card'><h4>Q{start_index + i + 1}: {q['q']}</h4><p><b>Your Answer:</b> {user_ans or 'Not Answered'}</p><p><b>Correct:</b> {q['ans']}</p></div>"
        total = len(questions); wrong = total - score
        new_done = prog + total
        with DBSession() as db:
            db.execute(sa.text("UPDATE cbt_progress SET used=:u WHERE nickname=:n AND subject_key=:k"), {"u": new_done, "n": nickname, "k": full_key})
            db.execute(sa.text("UPDATE users SET q_used=q_used+:t, correct=correct+:c, wrong=wrong+:w WHERE nickname=:u"), {"t": total, "c": score, "w": wrong, "u": nickname})
            db.commit()
        remaining = min(total_limit, all_count) - new_done
        next_btn = f"<a class=btn href=/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(sub)}>Next 10 - {remaining} left</a>" if remaining>0 else f"<a class=btn.blue href='/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(sub)}?redo=1'>🔄 Redo {sub}</a>"
        content = f"<div class='card'><h2>🎉 RESULT {subj_emoji(sub)} {sub}</h2><p><b>Score: {score}/{total}</b></p><p>Completed: {new_done}/{min(total_limit,all_count)}</p></div>{result_html}{next_btn}<a class=btn.blue href=/exam>Back</a>"
        return render_template_string(BASE, title="Result", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")
    q_html = ""
    for i,q in enumerate(questions):
        options = "".join([f"<label class=option><input type=radio name=q{i} value=\"{opt}\" required><span>{opt}</span></label>" for opt in q["options"]])
        q_html += f"<div class=card id=q{i}><p><b>Question {start_index + i + 1}</b></p><p>{q['q']}</p>{options}</div>"
    # CALCULATOR + TIMER
    timer_js = Markup(f"""
    let timeLeft = {batch_time};
    const timerEl = document.createElement('div');
    timerEl.className = 'timer';
    document.querySelector('.container').prepend(timerEl);
    function updateTimer(){{
        let m = Math.floor(timeLeft / 60); let s = timeLeft % 60; s = s < 10? '0' + s : s;
        timerEl.innerHTML = '⏰ TIME LEFT: ' + m + ':' + s + ' | {subj_emoji(sub)} {sub}';
        if(timeLeft <= 0){{ document.getElementById('cbt_form').submit(); }}
        timeLeft--;
    }}
    updateTimer(); setInterval(updateTimer, 1000);
    // FLOATING CALCULATOR
    let calcHtml = `<div id=calcBox class=calc-float><div style='display:flex;justify-content:space-between'><b>🧮 Calculator</b><button onclick="document.getElementById('calcBox').style.display='none'" style='background:red;color:white;border:none;border-radius:50%;width:20px'>X</button></div><input id=calcDisplay style='width:100%;margin:5px 0'><div style='display:grid;grid-template-columns:repeat(4,1fr);gap:3px'><button onclick="calcIn('7')" class=btn gray>7</button><button onclick="calcIn('8')" class=btn gray>8</button><button onclick="calcIn('9')" class=btn gray>9</button><button onclick="calcIn('/')" class=btn orange>/</button><button onclick="calcIn('4')" class=btn gray>4</button><button onclick="calcIn('5')" class=btn gray>5</button><button onclick="calcIn('6')" class=btn gray>6</button><button onclick="calcIn('*')" class=btn orange>*</button><button onclick="calcIn('1')" class=btn gray>1</button><button onclick="calcIn('2')" class=btn gray>2</button><button onclick="calcIn('3')" class=btn gray>3</button><button onclick="calcIn('-')" class=btn orange>-</button><button onclick="calcIn('0')" class=btn gray>0</button><button onclick="calcIn('.')" class=btn gray>.</button><button onclick="calcEval()" class=btn>=</button><button onclick="calcIn('+')" class=btn orange>+</button><button onclick="calcIn('Math.sqrt(')" class=btn blue>√</button><button onclick="calcIn('Math.sin(')" class=btn blue>sin</button><button onclick="calcIn('Math.cos(')" class=btn blue>cos</button><button onclick="document.getElementById('calcDisplay').value=''" class=btn red>C</button></div></div><button onclick="document.getElementById('calcBox').style.display='block'" style='position:fixed;bottom:80px;right:10px;z-index:9997;background:#ff9800;color:white;border:none;border-radius:50%;width:50px;height:50px;font-size:20px'>🧮</button>`;
    document.body.insertAdjacentHTML('beforeend', calcHtml);
    function calcIn(v){{ document.getElementById('calcDisplay').value+=v; }}
    function calcEval(){{ try{{ let r=eval(document.getElementById('calcDisplay').value); document.getElementById('calcDisplay').value=r; }}catch(e){{ document.getElementById('calcDisplay').value='Error'; }} }}
    """)
    content = f"<form method=POST id=cbt_form><h2 style='background:#0f3460;color:white;text-align:center;padding:10px;border-radius:8px'>{subj_emoji(sub)} {sub} - Batch {math.floor(prog/BATCH_SIZE)+1}</h2><p style='text-align:center'>{time_per_q}s per question - CRS/IRS separated</p>{q_html}<button class='btn orange'>Submit</button></form>"
    return render_template_string(BASE, title=f"{sub}", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script=timer_js)

@app.route('/confirm/<t>', methods=["POST"])
@login_required
def confirm(nickname, user, t):
    with DBSession() as db:
        db.execute(sa.text("INSERT INTO payments (nickname, name, type, status, bank_used, account_name, date_paid) VALUES (:u, :n, :t, 'Pending', :b, :a, :d)"),
        {"u": nickname, "n": user["name"], "t": t, "b": request.form["bank_used"], "a": request.form["account_name"], "d": str(date.today())});
        db.commit()
    return render_template_string(BASE, title="Sent", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup("<div class='card'><h2>✅ Request Sent</h2><p>Admin will verify within 24hrs</p><a class=btn href=/exam>Back</a></div>"), timer_script="")

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
        if user.get('lesson_expiry'):
            all_lessons = db.execute(sa.text("SELECT * FROM lessons WHERE class=:c AND (dept=:d OR dept='' OR dept IS NULL) ORDER BY date DESC"), {"c": user['class'], "d": user.get('dept','')}).mappings().all()
            if not all_lessons:
                return render_template_string(BASE, title="Lessons", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>🎓 No lessons yet for {user['class']} {user.get('dept','')}</h2><a class=btn.blue href=/main>Back</a></div>"), timer_script="")
            html = ""
            for l in all_lessons:
                media = ""
                if l.get('media_link'):
                    link = l['media_link']
                    if any(x in link.lower() for x in ['.mp4','.webm','video']):
                        media = f"<video src='{link}' controls class='lesson-media' onerror=\"this.parentElement.innerHTML='<a href={link} target=_blank>📹 Watch Video</a>'\"></video>"
                    else:
                        media = f"<img src='{link}' class='lesson-media' onerror=\"this.style.display='none'\">"
                html += f"<div class=card><h3>{subj_emoji(l['subject'])} {l['title']} - {l['subject']}</h3><p>{l['notes']}</p>{media}<small>{l['date']}</small></div>"
            return render_template_string(BASE, title="Lessons", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html + "<a class=btn.blue href=/main>Back</a>"), timer_script="")
        pending = db.execute(sa.text("SELECT * FROM payments WHERE nickname=:u AND type='lessons' AND status='Pending'"), {"u": nickname}).scalar()
        if pending:
            return render_template_string(BASE, title="Lessons", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup("<div class=card><h2>⏳ Payment Under Review</h2><p>Admin will verify your lesson payment.</p><a class=btn.blue href=/main>Back</a></div>"), timer_script="")
    return render_template_string(BASE, title="Pay Lesson", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>🔒 Unlock Lessons - ₦{LESSON_PRICE}/30days</h2><p><b>Bank:</b> {PALMPAY_BANK}<br><b>Acct:</b><input class=readonly-box readonly value={PALMPAY_ACCOUNT}><br><b>Name:</b> {PALMPAY_NAME}</p><form method=POST action=/confirm/lessons><input name=bank_used placeholder='Bank you used' required><input name=account_name placeholder='Account Name' required><button class=send-img-btn><img src={SEND_BTN_URL}></button></form></div>"), timer_script="")
# ====== COMMUNITY - FIXED DELETE PERMISSION + CRS/IRS SEPARATED ======
@app.route('/community', methods=["GET","POST"])
@login_required
def community(nickname, user):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        # DELETE HANDLER - FIXED
        del_id = request.args.get('del_post')
        if del_id:
            p = db.execute(sa.text("SELECT nickname FROM posts WHERE id=:i"), {"i": int(del_id)}).scalar()
            if p == nickname or nickname == 'motiz_support':
                db.execute(sa.text("DELETE FROM posts WHERE id=:i"), {"i": int(del_id)}); db.commit()
            return redirect("/community")
        if request.method=="POST" and request.form.get("text"):
            txt = request.form["text"][:1000]
            if nickname!= 'motiz_support' and ('http://' in txt.lower() or 'https://' in txt.lower() or 'www.' in txt.lower()):
                txt = txt.replace('http://','').replace('https://','').replace('www.','')
            db.execute(sa.text("INSERT INTO posts (nickname, name, text) VALUES (:u,:n,:t)"), {"u": nickname, "n": user["name"], "t": txt})
            db.commit(); return redirect("/community")
        posts = db.execute(sa.text("SELECT * FROM posts ORDER BY created_at DESC LIMIT 50")).mappings().all()
    html = "<div class=card><form method=POST><textarea name=text placeholder='What is on your mind? (Text only for students - CRS ✝️ / IRS ☪️ separated)' required maxlength=1000></textarea><button class=btn>Post</button></form></div>"
    for p in posts:
        try: likes = json.loads(p['likes'] or '[]')
        except: likes=[]
        try: comments = json.loads(p['comments'] or '[]')
        except: comments=[]
        is_motiz = p['nickname']=='motiz_support'
        is_author = p['nickname']==nickname
        style = "style='border:2px solid gold;background:#fff8e1'" if is_motiz else ""
        del_btn = f"<a class=btn.red href='/community?del_post={p['id']}' onclick=\"return confirm('Delete this post?')\" style='padding:5px;font-size:0.7rem'>🗑️ Delete</a>" if (is_author or nickname=='motiz_support') else ""
        html+=f"<div class=card {style}><b>{p['name']}</b>{' <span class=badge>✓ MOTIZ SUPPORT</span> <span style=background:gold;padding:2px 5px;border-radius:5px;font-size:0.6rem>ADMIN</span>' if is_motiz else ''}<br><small>{p['created_at']}</small><p>{p['text']}</p>{del_btn}<a class=btn.gray href='/like/{p['id']}'>👍 Like ({len(likes)})</a><a class=btn.gray href='/post/{p['id']}'>💬 Comment ({len(comments)})</a></div>"
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
        html = f"<div class=card><b>{p['name']}</b><p>{p['text']}</p></div><h3>Comments ({len(comments)})</h3>"
        for c in comments:
            html+=f"<div class=card><b>{c['name']}</b><p>{c['text']}</p><small>{c['time']}</small></div>"
        html+=f"<div class=card><form method=POST><textarea name=comment placeholder='Add comment' required></textarea><button class=btn>Comment</button></form></div><a class=btn.blue href=/community>Back</a>"
    return render_template_string(BASE, title="Post", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html), timer_script="")

# ====== COMPLAIN - 3 TIMES PER WEEK + 5 DAYS BONUS INFO ======
@app.route('/complain', methods=["GET","POST"])
@login_required
def complain_page(nickname, user):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        if request.method=="POST" and request.form.get("text"):
            cnt = db.execute(sa.text("SELECT COUNT(*) FROM complaints WHERE nickname=:u AND created_at > NOW() - INTERVAL '7 days'"), {"u": nickname}).scalar() or 0
            if cnt >= 3:
                return render_template_string(BASE, title="Complain Limit", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup("<div class=card><div class=error>❌ You don reach limit - 3 complains per week only. Try next week.</div><a class=btn.blue href=/main>Back</a></div>"), timer_script="")
            db.execute(sa.text("INSERT INTO complaints (nickname, name, text) VALUES (:u,:n,:t)"), {"u": nickname, "n": user["name"], "t": request.form["text"][:1000]})
            db.commit()
            return redirect("/complain")
        my = db.execute(sa.text("SELECT * FROM complaints WHERE nickname=:u ORDER BY id DESC LIMIT 20"), {"u": nickname}).mappings().all()
    html = "<div class=card><h2>📩 Complain to Admin (3 per week) - T=5 days referral bonus</h2><form method=POST><textarea name=text placeholder='Write your complaint...' required maxlength=1000></textarea><button class=btn>Send Complaint</button></form></div><h3>My Complaints</h3>"
    for c in my:
        reply = f"<div style='background:#d4edda;padding:8px;margin-top:5px;border-radius:5px'><b>Admin Reply:</b> {c['reply']}</div>" if c['reply'] else "<small>⏳ Pending...</small>"
        html+=f"<div class=card><b>📝 {c['text']}</b><br><small>{c['created_at']} - {c['status']}</small>{reply}</div>"
    return render_template_string(BASE, title="Complain", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html), timer_script="")

# ====== CHAT + DM + GROUPS + SCOUT 5 + REJECT + TICK FIX ======
@app.route('/chat')
@login_required
def chat(nickname, user):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        reqs = db.execute(sa.text("SELECT * FROM friend_requests WHERE to_nickname=:u AND status='Pending'"), {"u": nickname}).mappings().all()
        req_html = ""
        for r in reqs:
            req_html+=f"<div class=card><b>{r['from_nickname']}</b> sent you friend request<br><a class=btn.blue href=/accept/{r['from_nickname']} style='display:inline-block;width:48%'>✅ Accept</a><a class=btn.red href=/reject/{r['from_nickname']} style='display:inline-block;width:48%'>❌ Reject</a></div>"
        friends = user.get('friends', [])
        friend_cards = ""
        for f in friends:
            u = db.execute(sa.text("SELECT name,last_seen FROM users WHERE nickname=:u"), {"u": f}).mappings().first()
            if u:
                last = format_last_seen(u['last_seen']) if u.get('last_seen') else "Unknown"
                badge = " <span class=badge>✓ SUPPORT</span>" if f=='motiz_support' else ""
                friend_cards+=f"<a href=/dm/{f} class=friend-card><div class=friend-avatar>{f[0].upper()}</div><div><b>{u['name']}</b>{badge}<br><small>{last}</small></div></a>"
        groups = db.execute(sa.text("SELECT * FROM groups")).mappings().all()
        group_html = ""
        for g in groups:
            try: members=json.loads(g['members'] or '[]')
            except: members=[]
            if nickname in members:
                group_html+=f"<a href=/group/{g['id']} class=friend-card><div class=friend-avatar>👥</div><div><b>{g['name']}</b><br><small>Group</small></div></a>"
    content = f"{req_html}<h3>Friends ({len(friends)})</h3>{friend_cards or '<p>No friends yet - Go to Me to add</p>'}<h3>Groups</h3>{group_html}<a class=btn.blue href=/create_group>➕ Create Group</a><a class=btn href=/me>👤 My Profile / Add Friends (Scout 5)</a><a class=btn.blue href=/complain>📩 Complain (T=5 days)</a>"
    return render_template_string(BASE, title="Chat", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")

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
    return redirect("/chat")

@app.route('/reject/<f>')
@login_required
def reject_friend(nickname, user, f):
    with DBSession() as db:
        db.execute(sa.text("UPDATE friend_requests SET status='Rejected' WHERE from_nickname=:f AND to_nickname=:u AND status='Pending'"), {"f": f, "u": nickname})
        db.commit()
    return redirect("/chat")

@app.route('/add_friend/<f>')
@login_required
def add_friend(nickname, user, f):
    if f == nickname or f=='motiz_support': return redirect("/me")
    with DBSession() as db:
        if f in user.get('friends', []): return redirect("/me")
        exists = db.execute(sa.text("SELECT * FROM friend_requests WHERE from_nickname=:u AND to_nickname=:f AND status='Pending'"), {"u": nickname, "f": f}).scalar()
        if not exists:
            db.execute(sa.text("INSERT INTO friend_requests (from_nickname, to_nickname) VALUES (:u,:f)"), {"u": nickname, "f": f})
            db.commit()
    return redirect("/me?offset="+request.args.get('offset','0'))

@app.route('/me')
@login_required
def me_page(nickname, user):
    offset = int(request.args.get('offset', 0))
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        all_users = db.execute(sa.text("SELECT nickname, name, class FROM users WHERE nickname!=:u AND nickname!='motiz_support' ORDER BY RANDOM()"), {"u": nickname}).mappings().all()
        friends = user.get('friends', [])
        pending_to = [r['to_nickname'] for r in db.execute(sa.text("SELECT to_nickname FROM friend_requests WHERE from_nickname=:u AND status='Pending'"), {"u": nickname}).mappings().all()]
        filtered = [u for u in all_users if u['nickname'] not in friends and u['nickname'] not in pending_to]
        batch = filtered[offset:offset+FRIENDS_BATCH]
        html = f"<div class=card><h2>{user['name']} - {subj_emoji(user['class'])}</h2><p><b>Nickname:</b> {nickname}</p><p><b>Class:</b> {user['class']} {user.get('dept','')}</p><p><b>Referral Link:</b><input class=readonly-box readonly value='{BASE_URL}/register?ref={nickname}'></p><p><b>Referral Bonus:</b> 5 days free per paid referral (T=5) | CRS ✝️ IRS ☪️ separated</p></div><h3>Add Friends (Scout 5) - CRS/IRS Separated</h3>"
        for u in batch:
            html+=f"<div class=friend-card><div class=friend-avatar>{u['nickname'][0].upper()}</div><div style='flex:1'><b>{u['name']}</b><br><small>{u['nickname']} - {u['class']}</small></div><a class=btn.blue href=/add_friend/{u['nickname']}?offset={offset} style='width:auto;padding:8px 15px'>Add</a></div>"
        next_offset = offset + FRIENDS_BATCH
        if next_offset < len(filtered):
            html+=f"<a class='btn orange' href=/me?offset={next_offset}>🔍 Scout - Show Next 5</a>"
        else:
            html+=f"<a class=btn.gray href=/me?offset=0>🔄 Scout Again From Start</a>"
        html+=f"<a class=btn.red href=/logout>Logout</a><a class=btn.blue href=/chat>Back to Chat</a><a class=btn.blue href=/complain>📩 Complain</a>"
    return render_template_string(BASE, title="Me", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html), timer_script="")

@app.route('/dm/<other>', methods=["GET","POST"])
@login_required
def dm_page(nickname, user, other):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        other_user = db.execute(sa.text("SELECT * FROM users WHERE nickname=:o"), {"o": other}).mappings().first()
        if not other_user: return redirect("/chat")
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
            db.execute(sa.text("INSERT INTO dms (from_nickname, to_nickname, text, time) VALUES (:f,:t,:txt,:tm)"), {"f": nickname, "t": other, "txt": request.form["text"][:1000], "tm": str(datetime.now(NIGERIA_TZ))})
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
            if m['to_nickname'] in read_by:
                tick = f"<span class=tick-seen>{TICK_SEEN}</span>"
            elif m['to_nickname'] in delivered:
                tick = f"<span class=tick-delivered>{TICK_DELIVERED}</span>"
            else:
                tick = f"<span class=tick-sent>{TICK_SENT}</span>"
        else:
            tick = ""
        cls = "me" if is_me else "other"
        chat_html+=f"<div class='chat-msg {cls}'><div class='bubble {cls}'><div class='bubble-text'>{m['text']}</div><div class='bubble-time'>{m['time'][11:16] if len(m['time'])>10 else m['time']} {tick}</div></div></div>"
    timer_js = Markup(f"""
    setTimeout(()=>{{ window.scrollTo(0, document.body.scrollHeight); }}, 300);
    let lastCount = {len(dms)};
    setInterval(()=>{{
        fetch('/check_dm/{other}').then(r=>r.json()).then(data=>{{
            if(data.count > lastCount){{
                let audio = new Audio('https://notificationsounds.com/storage/sounds/file-sounds-1153-pristine.mp3');
                audio.play().catch(()=>{{}});
                location.reload();
            }}
        }});
    }}, 3000);
    """)
    content = f"<h3>💬 {other_user['name']} ({format_last_seen(other_user.get('last_seen'))}) - {subj_emoji(other_user.get('class',''))}</h3><div id=chatBox>{chat_html}</div><form method=POST class=chat-input-fixed><input name=text placeholder='Type message...' required autocomplete=off><button class=send-img-btn><img src={SEND_BTN_URL}></button></form><a class=btn.blue href=/chat style='margin-bottom:100px'>Back</a>"
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
        name = request.form.get("name","").strip()
        if name:
            with DBSession() as db:
                db.execute(sa.text("INSERT INTO groups (name, creator, members) VALUES (:n,:c,:m)"), {"n": name, "c": nickname, "m": json.dumps([nickname])})
                db.commit()
            return redirect("/chat")
    return render_template_string(BASE, title="Create Group", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup("<div class=card><h2>Create Group - motiz_support blocked</h2><form method=POST><input name=name placeholder='Group Name' required><button class=btn>Create</button></form></div>"), timer_script="")

@app.route('/group/<int:gid>', methods=["GET","POST"])
@login_required
def group_page(nickname, user, gid):
    with DBSession() as db:
        g = db.execute(sa.text("SELECT * FROM groups WHERE id=:i"), {"i": gid}).mappings().first()
        if not g: return redirect("/chat")
        try: members=json.loads(g['members'] or '[]')
        except: members=[]
        if nickname not in members: return redirect("/chat")
        if request.method=="POST" and request.form.get("text"):
            try: msgs=json.loads(g['messages'] or '[]')
            except: msgs=[]
            msgs.append({"from": nickname, "name": user['name'], "text": request.form["text"][:1000], "time": str(datetime.now(NIGERIA_TZ))})
            db.execute(sa.text("UPDATE groups SET messages=:m WHERE id=:i"), {"m": json.dumps(msgs), "i": gid}); db.commit()
            return redirect(f"/group/{gid}")
        try: msgs=json.loads(g['messages'] or '[]')
        except: msgs=[]
    html = f"<h3>👥 {g['name']}</h3>"
    for m in msgs:
        is_me = m['from']==nickname
        cls = "me" if is_me else "other"
        html+=f"<div class='chat-msg {cls}'><div class='bubble-text'><b>{m['name']}</b><br>{m['text']}</div><div class='bubble-time'>{m['time'][11:16] if len(m['time'])>10 else m['time']}</div></div></div>"
    html+=f"<form method=POST class=chat-input-fixed><input name=text placeholder='Type...' required><button class=send-img-btn><img src={SEND_BTN_URL}></button></form>"
    return render_template_string(BASE, title=g['name'], header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html), timer_script="")
@app.route('/admin', methods=["GET","POST"])
@login_required
def admin(nickname, user):
    global ADMIN_PASS, NOTICES, PINNED_NOTICE
    if not session.get("admin_logged_in"):
        error = ""
        if request.method=="POST" and "login_pass" in request.form:
            if request.form.get("login_pass")== ADMIN_PASS: session["admin_logged_in"] = True; return redirect("/admin")
            else: error = "<div class=error>Wrong Password</div>"
        return render_template_string(BASE, title="Admin", header="", content=Markup(f"<div class='card'><h2>🔒 Admin Login</h2>{error}<form method=POST><input type=password name=login_pass placeholder='Enter Admin Password' required><button class=btn>Login</button></form></div>"), timer_script="")
    error = ""; bulk_result = ""
    q_target = request.args.get('q_target')
    l_target = request.args.get('l_target')
    manage = request.args.get('manage')
    edit_notice_id = request.args.get('edit_notice')

    with DBSession() as db:
        pending_reqs = db.execute(sa.text("SELECT * FROM payments WHERE status='Pending' ORDER BY id DESC")).mappings().all()
        complaints_pending = db.execute(sa.text("SELECT * FROM complaints ORDER BY id DESC LIMIT 50")).mappings().all()
        complaints_count = db.execute(sa.text("SELECT COUNT(*) FROM complaints WHERE status='Pending'")).scalar() or 0

    if request.method=="POST":
        with DBSession() as db:
            if "verify_id" in request.form:
                req = db.execute(sa.text("SELECT * FROM payments WHERE id=:id"), {"id": request.form["verify_id"]}).mappings().first()
                if req:
                    if req["type"] == "questions":
                        db.execute(sa.text("UPDATE users SET q_cycle='paid', is_verified=TRUE, payment_verified_date=:today WHERE nickname=:u"), {"today": str(date.today()), "u": req["nickname"]})
                    if req["type"] == "lessons":
                        db.execute(sa.text("UPDATE users SET lesson_expiry=:d, is_verified=TRUE, payment_verified_date=:today WHERE nickname=:u"), {"d": str(date.today() + timedelta(days=30)), "today": str(date.today()), "u": req["nickname"]})
                    ref = db.execute(sa.text("SELECT referred_by FROM users WHERE nickname=:u"), {"u": req["nickname"]}).scalar()
                    if ref:
                        ref_user = db.execute(sa.text("SELECT lesson_expiry FROM users WHERE nickname=:r"), {"r": ref}).scalar()
                        try:
                            if ref_user:
                                current_expiry = datetime.strptime(str(ref_user), "%Y-%m-%d").date()
                                if current_expiry < date.today(): current_expiry = date.today()
                            else: current_expiry = date.today()
                            new_expiry = current_expiry + timedelta(days=5) # T = 5 DAYS
                        except: new_expiry = date.today() + timedelta(days=5)
                        db.execute(sa.text("UPDATE users SET lesson_expiry=:d, free_days=free_days+5, referral_count=referral_count+1 WHERE nickname=:r"), {"d": str(new_expiry), "r": ref})
                    db.execute(sa.text("UPDATE payments SET status='Verified' WHERE id=:id"), {"id": request.form["verify_id"]})
                    db.commit(); error = "<div class=success>✅ Payment Verified - 30 Days + Referral +5 Days (T=5)</div>"
            if "deny_id" in request.form:
                db.execute(sa.text("UPDATE payments SET status='Denied' WHERE id=:id"), {"id": request.form["deny_id"]}); db.commit(); error = "<div class=error>Payment Denied</div>"
            if "reply_complaint" in request.form:
                cid = request.form["complaint_id"]
                db.execute(sa.text("UPDATE complaints SET reply=:r, status='Replied' WHERE id=:i"), {"r": request.form["reply_text"], "i": int(cid)}); db.commit(); error = "<div class=success>Complaint Replied</div>"
            if "delete_complaint" in request.form:
                db.execute(sa.text("DELETE FROM complaints WHERE id=:i"), {"i": int(request.form["complaint_id"])}); db.commit(); error = "<div class=error>Complaint Deleted</div>"
            if "add_question" in request.form:
                key = f"{request.form['q_key']}_{request.form['admin_subject']}"
                options = [request.form["a"],request.form["b"],request.form["c"],request.form["d"]]
                correct_ans = options[int(request.form["correct_ans"])]
                db.execute(sa.text("INSERT INTO questions (key, q, options, ans) VALUES (:k, :q, :o, :a)"),{"k": key, "q": request.form["q"], "o": json.dumps(options), "a": correct_ans}); db.commit(); error = f"<div class=success>Question Added for {key} {subj_emoji(request.form['admin_subject'])}</div>"
            if "bulk_upload" in request.form:
                key = f"{request.form['bulk_key']}_{request.form['bulk_subject']}"
                data = request.form['bulk_data'].strip()
                f = StringIO(data)
                reader = csv.reader(f)
                success = 0; failed = []
                for i, parts in enumerate(reader, 1):
                    try:
                        if len(parts)!= 6: raise Exception("Need 6 columns")
                        q, a, b, c, d, ans = [x.strip() for x in parts]
                        options = [a,b,c,d]
                        db.execute(sa.text("INSERT INTO questions (key, q, options, ans) VALUES (:k, :q, :o, :a)"),{"k": key, "q": q, "o": json.dumps(options), "a": ans})
                        success += 1
                    except Exception as e: failed.append(f"Line {i}: {str(e)}")
                db.commit()
                bulk_result = f"<div class=success>✅ {success} Questions Added for {key}</div>"
                if failed: bulk_result += f"<div class=error>❌ Failed: {' | '.join(failed)}</div>"
            if "add_lesson" in request.form:
                full_key = request.form['l_key']
                parts = full_key.split("_")
                cls = parts[0]; dept = parts[1] if len(parts) > 1 else ""
                db.execute(sa.text("INSERT INTO lessons (class, dept, subject, title, notes, date, media_link) VALUES (:c, :d, :s, :t, :n, :date, :m)"),
                           {"c": cls, "d": dept, "s": request.form['lesson_subject'], "t": request.form['lesson_title'], "n": request.form['lesson_notes'], "date": str(date.today()), "m": request.form.get('media_link','')}); db.commit(); error = "<div class=success>Lesson Posted</div>"
            if "edit_question" in request.form:
                options = [request.form["a"],request.form["b"],request.form["c"],request.form["d"]]
                correct_ans = options[int(request.form["correct_ans"])]
                db.execute(sa.text("UPDATE questions SET q=:q, options=:o, ans=:a WHERE id=:id"),{"q": request.form["q"], "o": json.dumps(options), "a": correct_ans, "id": request.form["qid"]}); db.commit(); error = "<div class=success>Question Updated</div>"
            if "delete_question" in request.form:
                db.execute(sa.text("DELETE FROM questions WHERE id=:id"), {"id": request.form["qid"]}); db.commit(); error = "<div class=error>Question Deleted</div>"
            if "edit_lesson" in request.form:
                db.execute(sa.text("UPDATE lessons SET title=:t, notes=:n, media_link=:m WHERE id=:id"),{"t": request.form["lesson_title"], "n": request.form["lesson_notes"], "m": request.form.get("media_link",""), "id": request.form["lid"]}); db.commit(); error = "<div class=success>Lesson Updated</div>"
            if "delete_lesson" in request.form:
                db.execute(sa.text("DELETE FROM lessons WHERE id=:id"), {"id": request.form["lid"]}); db.commit(); error = "<div class=error>Lesson Deleted</div>"
            if "clear_all_data" in request.form:
                db.execute(sa.text("DELETE FROM questions")); db.execute(sa.text("DELETE FROM lessons")); db.execute(sa.text("DELETE FROM payments")); db.commit(); error = "<div class=error>⚠️ All Old Data Deleted</div>"
            if "change_pass" in request.form:
                if request.form["old_pass"]!= ADMIN_PASS: error = "<div class=error>Old password wrong</div>"
                else: ADMIN_PASS = request.form["new_pass"]; set_setting("admin_pass", ADMIN_PASS); error = "<div class=success>Password Changed</div>"
            if "post_notice" in request.form:
                NOTICES.insert(0, {"id": int(datetime.now().timestamp()), "title": request.form["notice_title"], "text": request.form["notice_text"], "media_link": request.form.get("media_link",""), "created_at": str(datetime.now(NIGERIA_TZ))})
                set_setting("notices", json.dumps(NOTICES)); error = "<div class=success>Notice Posted</div>"
            if "edit_notice" in request.form:
                nid = int(request.form["notice_id"])
                for n in NOTICES:
                    if n.get('id')==nid or n.get('title')==request.form.get('old_title'):
                        n['title']=request.form["notice_title"]; n['text']=request.form["notice_text"]; n['media_link']=request.form.get("media_link","")
                set_setting("notices", json.dumps(NOTICES)); error = "<div class=success>Notice Updated</div>"
                        if "delete_notice" in request.form:
                nid = int(request.form["notice_id"])
                NOTICES = [n for n in NOTICES if n.get('id')!=nid]
                set_setting("notices", json.dumps(NOTICES)); error = "<div class=error>Notice Deleted</div>"
            if "pin_notice" in request.form:
                set_setting("pinned_notice", json.dumps({"title": request.form["notice_title"], "text": request.form["notice_text"]}))
                PINNED_NOTICE = get_setting("pinned_notice",""); error = "<div class=success>Pinned</div>"

    pending_html = "".join([f"<div class='card'><b>{r['name']} (@{r['nickname']})</b> for {r['type']}<br><small>Bank: {r.get('bank_used','N/A')} | Acc: {r.get('account_name','N/A')}</small><div style='display:flex;gap:5px'><form method=POST style='flex:1'><input type=hidden name=verify_id value={r['id']}><button class=btn>Verify 30 Days +5 Referral (T=5)</button></form><form method=POST style='flex:1'><input type=hidden name=deny_id value={r['id']}><button class='btn red'>Deny</button></form></div></div>" for r in pending_reqs])

    # COMPLAINTS INBOX FOR ADMIN
    complaints_html = ""
    for c in complaints_pending:
        reply_form = f"<form method=POST><input type=hidden name=complaint_id value={c['id']}><textarea name=reply_text placeholder='Reply...' required>{c['reply'] or ''}</textarea><button name=reply_complaint class=btn.blue>Reply</button></form><form method=POST><input type=hidden name=complaint_id value={c['id']}><button name=delete_complaint class='btn red'>Delete Complaint</button></form>" if c['status']=='Pending' else f"<div style='background:#d4edda;padding:5px'><b>Replied:</b> {c['reply']}</div><form method=POST><input type=hidden name=complaint_id value={c['id']}><button name=delete_complaint class='btn red'>Delete</button></form>"
        complaints_html+=f"<div class=card><b>{c['name']} (@{c['nickname']}) - {c['status']}</b><p>{c['text']}</p><small>{c['created_at']}</small>{reply_form}</div>"
    if not complaints_html: complaints_html="<p>No complaints</p>"

    # MANAGE NOTICE - EDIT/DELETE
    manage_notice_html = ""
    for n in NOTICES:
        nid = n.get('id', 0)
        manage_notice_html+=f"<div class=card><b>📢 {n['title']}</b><p>{n['text'][:100]}...</p><a class=btn.blue href=/admin?edit_notice={nid}>✏️ Edit</a><form method=POST style='display:inline'><input type=hidden name=notice_id value={nid}><button name=delete_notice class='btn red'>Delete</button></form><form method=POST style='display:inline'><input type=hidden name=notice_title value='{n['title']}'><input type=hidden name=notice_text value='{n['text']}'><button name=pin_notice class=btn.orange>📌 Pin</button></form></div>"

    keys = ["JSS1","JSS2","JSS3","SS1_Science","SS1_Commercial","SS1_Art","SS2_Science","SS2_Commercial","SS2_Art","SS3_Science","SS3_Commercial","SS3_Art"]
    labels = ["JSS1","JSS2","JSS3","SS1 Science","SS1 Commercial","SS1 Art (CRS ✝️/IRS ☪️ separated)","SS2 Science","SS2 Commercial","SS2 Art (CRS ✝️/IRS ☪️ separated)","SS3 Science","SS3 Commercial","SS3 Art (CRS ✝️/IRS ☪️ separated)"]

    group1 = ""; group2 = ""
    for k,l in zip(keys,labels):
        group1 += f"<a href=/admin?q_target={k} class=btn.gray>➕ Add Q: {l}</a>"
        group1 += f"<a href=/admin?q_target={k}&bulk=1 class=btn.orange>📦 Bulk Q: {l}</a>"
        group2 += f"<a href=/admin?l_target={k} class=btn.gray>➕ Add Lesson: {l}</a>"

    add_q_form = ""; bulk_form = ""
    if q_target:
        subs = SUBJECTS.get(q_target, [])
        sub_options = "".join([f"<option>{s}</option>" for s in subs])
        add_q_form = f"<div class=card><h3>Add Question for {q_target.replace('_',' ')} - CRS/IRS Separated {subj_emoji(q_target)}</h3><form method=POST><input type=hidden name=q_key value='{q_target}'><select name=admin_subject required><option value=''>Select Subject</option>{sub_options}</select><textarea name=q placeholder='Question' required></textarea><input name=a placeholder='Option A' required><input name=b placeholder='Option B' required><input name=c placeholder='Option C' required><input name=d placeholder='Option D' required><select name=correct_ans required><option value=0>A</option><option value=1>B</option><option value=2>C</option><option value=3>D</option></select><button name=add_question class='send-img-btn'><img src='{SEND_BTN_URL}'></button></form></div>"
        if request.args.get('bulk'):
            bulk_form = f"<div class=card><h3>📦 Bulk Upload for {q_target.replace('_',' ')} - CRS ✝️ IRS ☪️ separated</h3>{bulk_result}<form method=POST><input type=hidden name=bulk_key value='{q_target}'><select name=bulk_subject required><option value=''>Select Subject</option>{sub_options}</select><textarea name=bulk_data placeholder='Paste CSV: Question,A,B,C,D,CorrectAnswer' rows=10 required></textarea><button name=bulk_upload class=btn.orange>Upload</button></form></div>"

    add_l_form = ""
    if l_target:
        subs = SUBJECTS.get(l_target, [])
        sub_options = "".join([f"<option>{s}</option>" for s in subs])
        add_l_form = f"<div class=card><h3>Add Lesson for {l_target.replace('_',' ')} - {subj_emoji(l_target)}</h3><form method=POST><input type=hidden name=l_key value='{l_target}'><select name=lesson_subject required><option value=''>Select Subject</option>{sub_options}</select><input name=lesson_title placeholder='Lesson Title' required><textarea name=lesson_notes placeholder='Lesson Notes' rows=6 required></textarea><input name=media_link placeholder='Image/Video Link.jpg.mp4 optional (imgur)'><button name=add_lesson class='send-img-btn'><img src='{SEND_BTN_URL}'></button></form></div>"

    edit_notice_form = ""
    if edit_notice_id:
        try:
            nid = int(edit_notice_id)
            note = next((n for n in NOTICES if n.get('id')==nid), None)
            if note:
                edit_notice_form = f"<div class=card><h3>✏️ Edit Notice</h3><form method=POST><input type=hidden name=notice_id value={note['id']}><input type=hidden name=old_title value='{note['title']}'><input name=notice_title value='{note['title']}' required><textarea name=notice_text required>{note['text']}</textarea><input name=media_link value='{note.get('media_link','')}'><button name=edit_notice class=btn.blue>Update Notice</button></form></div>"
        except: pass

    manage_html = ""
    if manage == "questions":
        with DBSession() as db: questions = db.execute(sa.text("SELECT * FROM questions ORDER BY id DESC LIMIT 100")).mappings().all()
        q_list = ""
        for q in questions:
            opts = json.loads(q['options'])
            q_list += f"<div class=card><b>{q['key']} {subj_emoji(q['key'])}</b><p>{q['q']}</p><p><small>A:{opts[0]} B:{opts[1]} C:{opts[2]} D:{opts[3]} | Ans:{q['ans']}</small></p><form method=POST><input type=hidden name=qid value={q['id']}><input name=q value='{q['q']}'><input name=a value='{opts[0]}'><input name=b value='{opts[1]}'><input name=c value='{opts[2]}'><input name=d value='{opts[3]}'><select name=correct_ans><option value=0 {'selected' if q['ans']==opts[0] else ''}>A</option><option value=1 {'selected' if q['ans']==opts[1] else ''}>B</option><option value=2 {'selected' if q['ans']==opts[2] else ''}>C</option><option value=3 {'selected' if q['ans']==opts[3] else ''}>D</option></select><button name=edit_question class=btn.blue>Edit</button></form><form method=POST><input type=hidden name=qid value={q['id']}><button name=delete_question class='btn red'>Delete</button></form></div>"
        manage_html = f"<div class=card><h2>📝 Manage Questions - CRS/IRS Separated</h2>{q_list or '<p>No questions</p>'}</div>"
    elif manage == "lessons":
        with DBSession() as db: lessons = db.execute(sa.text("SELECT * FROM lessons ORDER BY id DESC")).mappings().all()
        l_list = ""
        for l in lessons:
            l_list += f"<div class=card><b>{l['class']} {l['dept']} - {l['subject']} {subj_emoji(l['subject'])}</b><p>{l['title']}</p><form method=POST><input type=hidden name=lid value={l['id']}><input name=lesson_title value='{l['title']}'><textarea name=lesson_notes>{l['notes']}</textarea><input name=media_link value='{l.get('media_link','')}'><button name=edit_lesson class=btn.blue>Edit</button></form><form method=POST><input type=hidden name=lid value={l['id']}><button name=delete_lesson class='btn red'>Delete</button></form></div>"
        manage_html = f"<div class=card><h2>📚 Manage Lessons</h2>{l_list or '<p>No lessons</p>'}</div>"
    elif manage == "notices":
        manage_html = f"<div class=card><h2>📢 Manage Notices - Edit/Delete/Pin</h2>{manage_notice_html or '<p>No notices</p>'}</div>"
    elif manage == "complaints":
        manage_html = f"<div class=card><h2>📩 Complaints Inbox ({complaints_count} Pending) - T=5 days</h2>{complaints_html}</div>"

    form = f"""<div class="card"><h2>Admin Panel V32 FINAL - CRS ✝️/IRS ☪️ Separated - T=5 Days Referral</h2>{error}{bulk_result}</div>
{edit_notice_form}{add_q_form}{bulk_form}{add_l_form}{manage_html}
<div class="card"><h2>📝 GROUP 1: CBT QUESTIONS (CRS/IRS Separated)</h2><div style="display:flex;flex-direction:column;gap:10px">{group1}</div></div>
<div class="card"><h2>🎓 GROUP 2: LESSONS</h2><div style="display:flex;flex-direction:column;gap:10px">{group2}</div></div>
<div class="card"><h2>⚙️ GROUP 3: MANAGE - CRS/IRS + T=5</h2><a href=/admin?manage=questions class=btn.blue>Manage Questions (CRS/IRS separated)</a><a href=/admin?manage=lessons class=btn.blue>Manage Lessons</a><a href=/admin?manage=notices class=btn.orange>📢 Manage Notices (Edit/Delete/Pin)</a><a href=/admin?manage=complaints class=btn.red>📩 Complaints Inbox ({complaints_count} Pending) - 3/week limit</a></div>
<div class="card"><h2>👥 GROUP 4: STUDENTS + COMPLAINTS</h2><h3>Confirm Payment - 30 Days + 5 Days Referral (T=5)</h3>{pending_html or "<p>No pending</p>"}<h3>📩 Recent Complaints (5 Latest)</h3>{complaints_html[:2000]}<a href=/admin_attendance class=btn.blue>View Attendance + Last Seen + Referrals</a><form method=POST><h3>Post Notice (CRS/IRS separated info)</h3><input name=notice_title placeholder="Notice Title" required><textarea name=notice_text placeholder="Message" required></textarea><input name=media_link placeholder="Imgur Link optional.jpg.mp4"><button name=post_notice class="send-img-btn"><img src="{SEND_BTN_URL}"></button></form></div>
<div class="card"><h2>🛑 DANGER ZONE</h2><form method=POST onsubmit="return confirm('Delete ALL?')"><button name=clear_all_data class="btn red">Clear All Old Data</button></form></div>
<div class="card"><h2>🔒 GROUP 5: ADMIN SETTINGS</h2><form method="POST"><input type="password" name="old_pass" placeholder="Current Password" required><input type="password" name="new_pass" placeholder="New Password" required><button name="change_pass" class="btn orange">Change Password</button></form></div>"""
    return render_template_string(BASE, title="Admin V32", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(form), timer_script="")

@app.route('/admin_attendance')
@login_required
def admin_attendance(nickname, user):
    if not session.get("admin_logged_in"): return redirect("/admin")
    with DBSession() as db:
        users = db.execute(sa.text("SELECT name, nickname, class, dept, q_used, lesson_expiry, is_verified, last_seen, referral_count, free_days FROM users WHERE nickname!='motiz_support' ORDER BY last_seen DESC NULLS LAST")).mappings().all()
    table = ""
    for u in users:
        ls_text = format_last_seen(u['last_seen']) if u['last_seen'] else "Never"
        table += f"<tr><td>{u['name']}<br><small>@{u['nickname']}</small></td><td>{u['class']} {u.get('dept','') or ''} {subj_emoji(u['class'])}</td><td>{u['q_used']}</td><td>{'Verified' if u['is_verified'] else 'Free'}</td><td>{u['lesson_expiry'] or 'None'}</td><td>{ls_text}</td><td>{u['referral_count'] or 0}</td><td>{u['free_days'] or 0} (T=5)</td></tr>"
    content = f"<div class=card><h2>View Attendance + Last Seen + Referrals (T=5) - V32 CRS/IRS Separated</h2><p>Total Students: {len(users)} | Referral Bonus: 5 days per paid referral</p><div style='overflow-x:auto'><table style='width:100%;font-size:0.75rem;border-collapse:collapse' border=1><tr><th>Name</th><th>Class</th><th>Q Used</th><th>Status</th><th>Lesson Expiry</th><th>Last Seen</th><th>Referrals</th><th>Free Days (T=5)</th></tr>{table}</table></div><a class=btn.blue href=/admin>Back to Admin</a></div>"
    return render_template_string(BASE, title="Attendance V32", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
