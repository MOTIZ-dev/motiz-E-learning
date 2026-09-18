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
app.secret_key = os.environ.get('SECRET_KEY', "motiz_secret_key_2026_v33")
app.config['PROPAGATE_EXCEPTIONS'] = True

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise Exception("DATABASE_URL environment variable is not set")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = sa.create_engine(DATABASE_URL)
DBSession = sessionmaker(bind=engine)

# ====== SETTINGS - V33 FINAL + NEW FEATURES ======
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

# ADS - 15 SECONDS (YOUR REQUEST)
FIXED_AD_KEY = "f0869e31689755e244912b438511f4a9"
NATIVE_FEED_SRC = "https://pl31392647.profitableratecpmnetwork.com/1b/30/4d/1b304d26da2adb6df287de5560168dca.js"
AD_REFRESH_SECONDS = 15

# NEW FEATURES SETTINGS
FRIENDS_BATCH = 5  # Scout shows 5 users at a time
TICK_SENT = "✓ Sent"
TICK_DELIVERED = "✓✓ Delivered"
TICK_SEEN = "✓✓ Seen"

CALC_SUBJECTS = ["Mathematics", "Physics", "Chemistry", "Further Mathematics", "Financial Accounting", "Economics", "Biology"]

JSS_SUBJECTS = ["English Language", "Mathematics", "Basic Science", "Basic Technology", "Social Studies", "Civic Education", "Business Studies", "Agricultural Science", "Christian / Islamic Religious Studies (CRS/IRS)", "Physical and Health Education (PHE)"]
CLASSES = ["JSS1", "JSS2", "JSS3", "SS1", "SS2", "SS3"]
SUBJECTS = {
    "JSS1": JSS_SUBJECTS, "JSS2": JSS_SUBJECTS, "JSS3": JSS_SUBJECTS,
    "SS1_Science": ["English Language", "Mathematics", "Civic Education", "Physics", "Chemistry", "Biology", "Further Mathematics", "ICT", "Agricultural Science", "Geography"],
    "SS1_Commercial": ["English Language", "Mathematics", "Civic Education", "Economics", "Financial Accounting", "Commerce", "Business Management", "Government", "Computer Studies / ICT", "Marketing"],
    "SS1_Art": ["English Language", "Mathematics", "Civic Education", "Literature in English", "Government", "Christian / Islamic Religious Studies (CRS/IRS)", "Yoruba", "Economics", "Computer Studies / ICT", "Craft"],
    "SS2_Science": ["English Language", "Mathematics", "Civic Education", "Physics", "Chemistry", "Biology", "Further Mathematics", "ICT", "Agricultural Science", "Geography"],
    "SS2_Commercial": ["English Language", "Mathematics", "Civic Education", "Economics", "Financial Accounting", "Commerce", "Business Management", "History", "Computer Studies / ICT", "Marketing"],
    "SS2_Art": ["English Language", "Mathematics", "Civic Education", "Literature in English", "Government", "Christian / Islamic Religious Studies (CRS/IRS)", "Yoruba", "Economics", "Computer Studies / ICT", "Craft"],
    "SS3_Science": ["English Language", "Mathematics", "Civic Education", "Physics", "Chemistry", "Biology", "Further Mathematics", "ICT", "Agricultural Science", "Geography"],
    "SS3_Commercial": ["English Language", "Mathematics", "Civic Education", "Economics", "Financial Accounting", "Commerce", "Business Management", "Government", "Computer Studies / ICT", "Marketing"],
    "SS3_Art": ["English Language", "Mathematics", "Civic Education", "Literature in English", "Government", "Christian / Islamic Religious Studies (CRS/IRS)", "Yoruba", "Economics", "Computer Studies / ICT", "Craft"]
}

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
NOTICES = json.loads(get_setting("notices", json.dumps([{"title":"Welcome","text":"Welcome to MOTIZ E-LEARNING!","created_at": str(datetime.now(NIGERIA_TZ)), "media_link": ""}])))
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
    cutoff = datetime.now(NIGERIA_TZ) - timedelta(hours=24)
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
        now = datetime.now(pytz.utc) if dt.tzinfo else datetime.now()
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
    nav_html = """<div class="nav"><a href="/main">🏠 Home</a><a href="/exam">✍️ CBT</a><a href="/lessons">🎓 Lessons</a><a href="/community">🌍 Community</a><a href="/chat">💬 Chat</a><a href="/me">👤 Me</a></div>""" if show_nav else ""
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
    if request.method == "POST":
        nickname = request.form.get("nickname","").strip().lower()
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
            if link.endswith('.mp4') or '.mp4' in link or '.webm' in link:
                media = f"<video src='{link}' controls class='lesson-media' onerror=\"this.style.display='none'\"></video>"
            else:
                media = f"<img src='{link}' class='lesson-media' onerror=\"this.style.display='none'\">"
        notices_html += f"<div class='card'><div class=notice-title>📢 {n['title']}</div>{n['text']}{media}<small style='float:right'>{datetime.fromisoformat(n['created_at']).astimezone(NIGERIA_TZ).strftime('%I:%M %p')}</small></div>"
    return render_template_string(BASE, title="Home", header=Markup(get_header(nickname,user, show_nav=True, show_favicon=True)), content=Markup(f"<div class='card'><h2>Welcome {user['name']}</h2><p><b>Class:</b> {user['class']} {user.get('dept','')}</p></div>{pinned_html}<h3>General Notice</h3>{notices_html}<a class=btn href=/exam>Start CBT Exam</a>"), timer_script="")

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
            if done >= limit or (total_q>0 and done >= total_q):
                btn = f"<div class='card' style='border:2px solid #28a745'><b>📚 {s}</b><br><small>✅ Completed {done}/{min(limit,total_q)}</small><br><a class='btn blue cbt-btn-fix' href='/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(s)}?redo=1'>🔄 Redo / Reset</a></div>"
            else:
                remain_free = max(0, FREE_Q - prog) if not user.get('is_verified') else 0
                if not user.get('is_verified') and prog >= FREE_Q:
                    btn = f"<div class='card cbt-btn-fix' style='border:2px solid #e94560'><b>📚 {s}</b><br><small>🔒 Pay to continue (10/{FREE_Q} free done)</small><br><a class='btn red cbt-btn-fix' href='/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(s)}'>Unlock - Pay ₦{QUESTION_PRICE}</a></div>"
                else:
                    btn = f"<a class='btn blue cbt-btn-fix' href='/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(s)}'><span>📚 {s}</span><small>{done}/{min(limit,total_q)} done | Free left: {remain_free}</small></a>"
            sub_btns += btn
    if not user.get('is_verified'):
        with DBSession() as db:
            pending = db.execute(sa.text("SELECT * FROM payments WHERE nickname=:u AND type='questions' AND status='Pending'"), {"u": nickname}).scalar()
        if pending:
            sub_btns = "<div class='card'><h2>⏳ Payment Under Review</h2><p>Admin verifying - you will get 70 more per subject once approved.</p></div>" + sub_btns
    return render_template_string(BASE, title="CBT", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class='card'><h2>Subjects for {user['class']} {user.get('dept','')}</h2><p>10 FREE per subject. Shuffle + Smart timer.</p>{sub_btns}</div>"), timer_script="")

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
            return render_template_string(BASE, title="Error", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>😕 No Questions Yet for {sub}</h2><a class=btn.blue href=/exam>Back</a></div>"), timer_script="")
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
                content = f'<div class=card><h2>🔒 Unlock 70 More Questions for {sub}</h2><p><b>Pay &#8358;{QUESTION_PRICE} for 30 days</b></p><p><b>Bank:</b> {PALMPAY_BANK}<br><b>Account:</b><input class=readonly-box readonly value="{PALMPAY_ACCOUNT}"><br><b>Name:</b> {PALMPAY_NAME}</p><form method=POST action=/confirm/questions><input name=bank_used placeholder="Bank you used" required><input name=account_name placeholder="Account Name" required><button class="send-img-btn"><img src="{SEND_BTN_URL}"></button></form><a class=btn.blue href="/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(sub)}?redo=1">🔄 Redo Free 10</a></div>'
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
        content = f"<div class='card'><h2>🎉 RESULT {sub}</h2><p><b>Score: {score}/{total}</b></p><p>Completed: {new_done}/{min(total_limit,all_count)}</p></div>{result_html}{next_btn}<a class=btn.blue href=/exam>Back</a>"
        return render_template_string(BASE, title="Result", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")
    q_html = ""
    for i,q in enumerate(questions):
        options = "".join([f"<label class=option><input type=radio name=q{i} value=\"{opt}\" required><span>{opt}</span></label>" for opt in q["options"]])
        q_html += f"<div class=card id=q{i}><p><b>Question {start_index + i + 1}</b></p><p>{q['q']}</p>{options}</div>"
    timer_js = Markup(f"""
    let timeLeft = {batch_time};
    const timerEl = document.createElement('div');
    timerEl.className = 'timer';
    document.querySelector('.container').prepend(timerEl);
    function updateTimer(){{
        let m = Math.floor(timeLeft / 60); let s = timeLeft % 60; s = s < 10? '0' + s : s;
        timerEl.innerHTML = '⏰ TIME LEFT: ' + m + ':' + s + ' | {sub}';
        if(timeLeft <= 0){{ document.getElementById('cbt_form').submit(); }}
        timeLeft--;
    }}
    updateTimer(); setInterval(updateTimer, 1000);
    """)
    content = f"<form method=POST id=cbt_form><h2 style=color:white;text-align:center>{sub} - Batch {math.floor(prog/BATCH_SIZE)+1}</h2><p style=color:white;text-align:center>{time_per_q}s per question</p>{q_html}<button class='btn orange'>Submit</button></form>"
    return render_template_string(BASE, title=f"{sub}", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script=timer_js)

@app.route('/confirm/<t>', methods=["POST"])
@login_required
def confirm(nickname, user, t):
    with DBSession() as db:
        db.execute(sa.text("INSERT INTO payments (nickname, name, type, status, bank_used, account_name, date_paid) VALUES (:u, :n, :t, 'Pending', :b, :a, :d)"),
        {"u": nickname, "n": user["name"], "t": t, "b": request.form["bank_used"], "a": request.form["account_name"], "d": str(date.today())});
        db.commit()
    return render_template_string(BASE, title="Sent", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup("<div class='card'><h2>✅ Request Sent</h2><p>Admin will verify within 24hrs</p><a class=btn href=/exam>Back</a></div>"), timer_script="")
# ====== LESSONS ======
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
                html += f"<div class=card><h3>{l['title']} - {l['subject']}</h3><p>{l['notes']}</p>{media}<small>{l['date']}</small></div>"
            return render_template_string(BASE, title="Lessons", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html + "<a class=btn.blue href=/main>Back</a>"), timer_script="")
        pending = db.execute(sa.text("SELECT * FROM payments WHERE nickname=:u AND type='lessons' AND status='Pending'"), {"u": nickname}).scalar()
        if pending:
            return render_template_string(BASE, title="Lessons", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup("<div class=card><h2>⏳ Payment Under Review</h2><p>Admin will verify your lesson payment.</p><a class=btn.blue href=/main>Back</a></div>"), timer_script="")
    return render_template_string(BASE, title="Pay Lesson", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>🔒 Unlock Lessons - ₦{LESSON_PRICE}/30days</h2><p><b>Bank:</b> {PALMPAY_BANK}<br><b>Acct:</b><input class=readonly-box readonly value={PALMPAY_ACCOUNT}><br><b>Name:</b> {PALMPAY_NAME}</p><form method=POST action=/confirm/lessons><input name=bank_used placeholder='Bank you used' required><input name=account_name placeholder='Account Name' required><button class=send-img-btn><img src={SEND_BTN_URL}></button></form></div>"), timer_script="")

# ====== COMMUNITY ======
@app.route('/community', methods=["GET","POST"])
@login_required
def community(nickname, user):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        if request.method=="POST" and request.form.get("text"):
            db.execute(sa.text("INSERT INTO posts (nickname, name, text) VALUES (:u,:n,:t)"), {"u": nickname, "n": user["name"], "t": request.form["text"][:500]})
            db.commit(); return redirect("/community")
        posts = db.execute(sa.text("SELECT * FROM posts ORDER BY created_at DESC LIMIT 50")).mappings().all()
    html = "<div class=card><form method=POST><textarea name=text placeholder='What is on your mind?' required maxlength=500></textarea><button class=btn>Post</button></form></div>"
    for p in posts:
        try: likes = json.loads(p['likes'] or '[]')
        except: likes=[]
        try: comments = json.loads(p['comments'] or '[]')
        except: comments=[]
        is_motiz = p['nickname']=='motiz_support'
        style = "style='border:2px solid #1DA1F2;background:#e8f5fe'" if is_motiz else ""
        html+=f"<div class=card {style}><b>{p['name']}</b>{' <span class=badge>✓ MOTIZ SUPPORT</span>' if is_motiz else ''}<br><small>{p['created_at']}</small><p>{p['text']}</p><a class=btn.gray href='/like/{p['id']}'>👍 Like ({len(likes)})</a><a class=btn.gray href='/post/{p['id']}'>💬 Comment ({len(comments)})</a></div>"
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

# ====== CHAT + DM + GROUPS + TICK FIX + SCOUT + REJECT ======
@app.route('/chat')
@login_required
def chat(nickname, user):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        # Friend requests with REJECT button NEW
        reqs = db.execute(sa.text("SELECT * FROM friend_requests WHERE to_nickname=:u AND status='Pending'"), {"u": nickname}).mappings().all()
        req_html = ""
        for r in reqs:
            req_html+=f"<div class=card><b>{r['from_nickname']}</b> sent you friend request<br><a class=btn.blue href=/accept/{r['from_nickname']} style='display:inline-block;width:48%'>✅ Accept</a><a class=btn.red href=/reject/{r['from_nickname']} style='display:inline-block;width:48%'>❌ Reject</a></div>"
        # Friends list with last seen
        friends = user.get('friends', [])
        friend_cards = ""
        for f in friends:
            u = db.execute(sa.text("SELECT name,last_seen FROM users WHERE nickname=:u"), {"u": f}).mappings().first()
            if u:
                last = format_last_seen(u['last_seen']) if 'last_seen' in u else "Unknown"
                friend_cards+=f"<a href=/dm/{f} class=friend-card><div class=friend-avatar>{f[0].upper()}</div><div><b>{u['name']}</b><br><small>{last}</small></div></a>"
        # Groups
        groups = db.execute(sa.text("SELECT * FROM groups WHERE :u = ANY (string_to_array(members, ',')) OR creator=:u"), {"u": nickname}).mappings().all()
        group_html = ""
        for g in groups:
            group_html+=f"<a href=/group/{g['id']} class=friend-card><div class=friend-avatar>G</div><div><b>{g['name']}</b><br><small>Group</small></div></a>"
    # Scout logic will show in /me page for add friend
    content = f"{req_html}<h3>Friends ({len(friends)})</h3>{friend_cards or '<p>No friends yet - Go to Me to add</p>'}<h3>Groups</h3>{group_html}<a class=btn.blue href=/create_group>➕ Create Group</a><a class=btn href=/me>👤 My Profile / Add Friends</a>"
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

# NEW FEATURE - REJECT BUTTON
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
    if f == nickname: return redirect("/me")
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
        # Scout - only 5 users show
        all_users = db.execute(sa.text("SELECT nickname, name, class FROM users WHERE nickname!=:u AND nickname!='motiz_support' ORDER BY RANDOM()"), {"u": nickname}).mappings().all()
        # filter out already friends and pending
        friends = user.get('friends', [])
        pending_to = [r['to_nickname'] for r in db.execute(sa.text("SELECT to_nickname FROM friend_requests WHERE from_nickname=:u AND status='Pending'"), {"u": nickname}).mappings().all()]
        filtered = [u for u in all_users if u['nickname'] not in friends and u['nickname'] not in pending_to]
        batch = filtered[offset:offset+FRIENDS_BATCH]
        html = f"<div class=card><h2>{user['name']}</h2><p><b>Nickname:</b> {nickname}</p><p><b>Class:</b> {user['class']} {user.get('dept','')}</p><p><b>Correct:</b> {user.get('correct',0)} | <b>Wrong:</b> {user.get('wrong',0)}</p><p><b>Referral Link:</b><input class=readonly-box readonly value='{BASE_URL}/register?ref={nickname}'></p></div><h3>Add Friends (Scout)</h3>"
        for u in batch:
            html+=f"<div class=friend-card><div class=friend-avatar>{u['nickname'][0].upper()}</div><div style='flex:1'><b>{u['name']}</b><br><small>{u['nickname']} - {u['class']}</small></div><a class=btn.blue href=/add_friend/{u['nickname']}?offset={offset} style='width:auto;padding:8px 15px'>Add</a></div>"
        next_offset = offset + FRIENDS_BATCH
        if next_offset < len(filtered):
            html+=f"<a class='btn orange' href=/me?offset={next_offset}>🔍 Scout - Show Next 5</a>"
        else:
            html+=f"<a class=btn.gray href=/me?offset=0>🔄 Scout Again From Start</a>"
        html+=f"<a class=btn.red href=/logout>Logout</a><a class=btn.blue href=/chat>Back to Chat</a>"
    return render_template_string(BASE, title="Me", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html), timer_script="")

@app.route('/dm/<other>', methods=["GET","POST"])
@login_required
def dm_page(nickname, user, other):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        other_user = db.execute(sa.text("SELECT * FROM users WHERE nickname=:o"), {"o": other}).mappings().first()
        if not other_user: return redirect("/chat")
        # TICK FIX - Delivered logic
        # When receiver opens chat, mark all messages from other to me as delivered and read
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
        # Refresh list after marking
        dms = db.execute(sa.text("SELECT * FROM dms WHERE (from_nickname=:u AND to_nickname=:o) OR (from_nickname=:o AND to_nickname=:u) ORDER BY id ASC"), {"u": nickname, "o": other}).mappings().all()
    # Render with fixed tick logic
    chat_html = ""
    for m in dms:
        is_me = m['from_nickname']==nickname
        try: read_by=json.loads(m['read_by'] or '[]')
        except: read_by=[]
        try: delivered=json.loads(m['delivered_to'] or '[]')
        except: delivered=[]
        # TICK FIX - YOUR REQUEST
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
    # Auto scroll + notification sound
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
    content = f"<h3>💬 {other_user['name']} ({format_last_seen(other_user.get('last_seen'))})</h3><div id=chatBox>{chat_html}</div><form method=POST class=chat-input-fixed><input name=text placeholder='Type message...' required autocomplete=off><button class=send-img-btn><img src={SEND_BTN_URL}></button></form><a class=btn.blue href=/chat style='margin-bottom:100px'>Back</a>"
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
                db.execute(sa.text("INSERT INTO groups (name, creator, members) VALUES (:n,:c,:m)"), {"n": name, "c": nickname, "m": nickname})
                db.commit()
            return redirect("/chat")
    return render_template_string(BASE, title="Create Group", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup("<div class=card><h2>Create Group</h2><form method=POST><input name=name placeholder='Group Name' required><button class=btn>Create</button></form></div>"), timer_script="")

@app.route('/group/<int:gid>', methods=["GET","POST"])
@login_required
def group_page(nickname, user, gid):
    with DBSession() as db:
        g = db.execute(sa.text("SELECT * FROM groups WHERE id=:i"), {"i": gid}).mappings().first()
        if not g: return redirect("/chat")
        members = g['members'].split(',') if g['members'] else []
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
        html+=f"<div class='chat-msg {cls}'><div class='bubble {cls}'><div class='bubble-text'><b>{m['name']}</b><br>{m['text']}</div><div class='bubble-time'>{m['time'][11:16] if len(m['time'])>10 else m['time']}</div></div></div>"
    html+=f"<form method=POST class=chat-input-fixed><input name=text placeholder='Type...' required><button class=send-img-btn><img src={SEND_BTN_URL}></button></form>"
    return render_template_string(BASE, title=g['name'], header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html), timer_script="")
# ====== ADMIN ======
@app.route('/admin', methods=["GET","POST"])
def admin():
    global ADMIN_PASS, NOTICES, PINNED_NOTICE
    if request.method=="POST" and request.form.get("password")!=ADMIN_PASS and not session.get("admin"):
        if request.form.get("password"):
            return render_template_string(BASE, title="Admin", header="", content=Markup("<div class=error>Wrong password</div><a class=btn.blue href=/admin>Back</a>"), timer_script="")
    if request.form.get("password")==ADMIN_PASS:
        session["admin"]=True
    if not session.get("admin"):
        return render_template_string(BASE, title="Admin", header="", content=Markup("<div class=card><h2>Admin Login</h2><form method=POST><input type=password name=password placeholder='Admin Password' required><button class=btn>Login</button></form></div>"), timer_script="")

    if request.args.get("del_lesson"):
        with DBSession() as db:
            db.execute(sa.text("DELETE FROM lessons WHERE id=:i"), {"i": int(request.args.get("del_lesson"))})
            db.commit()
        return redirect("/admin")
    if request.args.get("del_notice"):
        idx = int(request.args.get("del_notice"))
        if 0 <= idx < len(NOTICES):
            NOTICES.pop(idx)
            set_setting("notices", json.dumps(NOTICES))
        return redirect("/admin")
    if request.args.get("del_post"):
        with DBSession() as db:
            db.execute(sa.text("DELETE FROM posts WHERE id=:i"), {"i": int(request.args.get("del_post"))})
            db.commit()
        return redirect("/admin")

    with DBSession() as db:
        payments = db.execute(sa.text("SELECT * FROM payments WHERE status='Pending' ORDER BY id DESC")).mappings().all()
        users = db.execute(sa.text("SELECT * FROM users ORDER BY id DESC LIMIT 100")).mappings().all()
        lessons_all = db.execute(sa.text("SELECT * FROM lessons ORDER BY id DESC LIMIT 50")).mappings().all()
        questions_count = db.execute(sa.text("SELECT key, COUNT(*) as c FROM questions GROUP BY key")).mappings().all()
        today_users = db.execute(sa.text("SELECT nickname, name, last_seen FROM users WHERE last_seen::date = CURRENT_DATE")).mappings().all()

    pay_html = ""
    for p in payments:
        pay_html+=f"<div class=card><b>{p['nickname']} - {p['type']}</b><br>Bank: {p['bank_used']} | Name: {p['account_name']}<br><a class=btn.blue href='/admin/approve/{p['id']}' style='display:inline-block;width:48%'>✅ Approve</a><a class=btn.red href='/admin/reject_pay/{p['id']}' style='display:inline-block;width:48%'>❌ Reject</a></div>"

    user_html = ""
    for u in users:
        last = format_last_seen(u['last_seen'])
        verified = "✅ Verified" if u['is_verified'] else "❌ Not Verified"
        user_html+=f"<div class=card><b>{u['nickname']} - {u['name']}</b><br>{u['class']} {u['dept'] or ''} | {verified}<br>Last: {last} | Correct: {u['correct'] or 0}<br><a class=btn.gray href='/admin/reset/{u['nickname']}'>Reset Progress</a></div>"

    lesson_html = ""
    for l in lessons_all:
        lesson_html+=f"<div class=card><b>{l['title']} - {l['subject']} - {l['class']}</b><br>{l['date']}<br><a class=btn.red href='/admin?del_lesson={l['id']}'>Delete Lesson</a></div>"

    q_html = "".join([f"<div class=card><b>{q['key']}</b> - {q['c']} questions</div>" for q in questions_count])

    notice_html = ""
    for i,n in enumerate(NOTICES):
        notice_html+=f"<div class=card><b>{n['title']}</b><br>{n['text'][:100]}<br><a class=btn.red href='/admin?del_notice={i}'>Delete Notice</a></div>"

    attendance_html = "".join([f"<div class=card><b>{u['nickname']} - {u['name']}</b><br>Last seen: {format_last_seen(u['last_seen'])}</div>" for u in today_users])

    content = f"""
    <div class=card><h2>ADMIN PANEL V33 FINAL</h2>
    <p><b>Total Users:</b> {len(users)} | <b>Pending:</b> {len(payments)} | <b>Today Active:</b> {len(today_users)}</p>
    <a class=btn.red href=/admin/logout>Logout Admin</a>
    </div>

    <h3>💰 Pending Payments</h3>{pay_html or '<p>No pending</p>'}

    <div class=card><h3>📚 Upload Lesson</h3>
    <form method=POST action=/admin/upload_lesson>
    <select name=class required><option value="">Select Class</option>{''.join([f'<option>{c}</option>' for c in CLASSES])}</select>
    <input name=dept placeholder='Dept (Science/Commercial/Art) or leave empty for JSS'>
    <input name=subject placeholder='Subject' required>
    <input name=title placeholder='Title' required>
    <textarea name=notes placeholder='Lesson notes' required></textarea>
    <input name=media_link placeholder='Imgur image/video link optional'>
    <button class=btn>Upload Lesson</button>
    </form>
    </div>

    <div class=card><h3>❓ Bulk Upload Questions CSV</h3>
    <p>CSV: key, question, opt1|opt2|opt3|opt4, answer</p>
    <form method=POST action=/admin/upload_questions enctype=multipart/form-data>
    <input type=file name=file accept=.csv required>
    <button class=btn>Upload CSV</button>
    </form>
    </div>

    <div class=card><h3>📢 Add Notice</h3>
    <form method=POST action=/admin/add_notice>
    <input name=title placeholder='Notice Title' required>
    <textarea name=text placeholder='Notice Text' required></textarea>
    <input name=media_link placeholder='Optional Imgur link'>
    <button class=btn>Add Notice</button>
    </form>
    <form method=POST action=/admin/pin_notice style='margin-top:10px'>
    <input name=pinned placeholder='Pinned Notice Text'>
    <button class=btn.blue>Pin Notice</button>
    </form>
    </div>

    <h3>📋 All Notices</h3>{notice_html}

    <h3>📚 Lessons</h3>{lesson_html}

    <h3>❓ Questions Count</h3>{q_html}

    <h3>👥 Today Attendance</h3>{attendance_html or '<p>No one today yet</p>'}

    <h3>👤 Users (100 latest)</h3>{user_html}

    <div class=card><h3>📩 Complaints / Support Inbox</h3>
    <a class=btn.blue href=/admin/support_chats>View Support DMs</a>
    </div>

    <div class=card><h3>⚙️ Change Admin Password</h3>
    <form method=POST action=/admin/change_pass>
    <input name=new_pass placeholder='New Admin Password' required>
    <button class=btn.red>Change Password</button>
    </form>
    </div>
    """
    return render_template_string(BASE, title="Admin", header="", content=Markup(content), timer_script="")

@app.route('/admin/logout')
def admin_logout():
    session.pop("admin", None)
    return redirect("/admin")

@app.route('/admin/approve/<int:pid>')
def approve_pay(pid):
    if not session.get("admin"): return redirect("/admin")
    with DBSession() as db:
        p = db.execute(sa.text("SELECT * FROM payments WHERE id=:i"), {"i": pid}).mappings().first()
        if p:
            if p['type']=='lessons':
                db.execute(sa.text("UPDATE users SET lesson_expiry=:d WHERE nickname=:u"), {"d": date.today() + timedelta(days=30), "u": p['nickname']})
            elif p['type']=='questions':
                db.execute(sa.text("UPDATE users SET is_verified=TRUE, payment_verified_date=:d WHERE nickname=:u"), {"d": str(date.today()), "u": p['nickname']})
            db.execute(sa.text("UPDATE payments SET status='Approved' WHERE id=:i"), {"i": pid})
            db.commit()
    return redirect("/admin")

@app.route('/admin/reject_pay/<int:pid>')
def reject_pay(pid):
    if not session.get("admin"): return redirect("/admin")
    with DBSession() as db:
        db.execute(sa.text("UPDATE payments SET status='Rejected' WHERE id=:i"), {"i": pid})
        db.commit()
    return redirect("/admin")

@app.route('/admin/reset/<nickname>')
def reset_user(nickname):
    if not session.get("admin"): return redirect("/admin")
    with DBSession() as db:
        db.execute(sa.text("DELETE FROM cbt_progress WHERE nickname=:u"), {"u": nickname})
        db.execute(sa.text("UPDATE users SET correct=0, wrong=0, q_used=0, free_questions_used=0 WHERE nickname=:u"), {"u": nickname})
        db.commit()
    return redirect("/admin")

@app.route('/admin/upload_lesson', methods=["POST"])
def upload_lesson():
    if not session.get("admin"): return redirect("/admin")
    with DBSession() as db:
        db.execute(sa.text("INSERT INTO lessons (class, dept, subject, title, notes, date, media_link) VALUES (:c,:d,:s,:t,:n,:dt,:m)"),
                   {"c": request.form['class'], "d": request.form.get('dept',''), "s": request.form['subject'], "t": request.form['title'], "n": request.form['notes'], "dt": str(date.today()), "m": request.form.get('media_link','')})
        db.commit()
    return redirect("/admin")

@app.route('/admin/upload_questions', methods=["POST"])
def upload_questions():
    if not session.get("admin"): return redirect("/admin")
    file = request.files.get('file')
    if file:
        content = file.read().decode('utf-8')
        reader = csv.reader(StringIO(content))
        with DBSession() as db:
            for row in reader:
                if len(row) < 4: continue
                key = row[0].strip()
                q = row[1].strip()
                opts = row[2].split('|')
                ans = row[3].strip()
                if not key or not q: continue
                db.execute(sa.text("INSERT INTO questions (key, q, options, ans) VALUES (:k,:q,:o,:a)"), {"k": key, "q": q, "o": json.dumps(opts), "a": ans})
            db.commit()
    return redirect("/admin")

@app.route('/admin/add_notice', methods=["POST"])
def add_notice():
    global NOTICES
    if not session.get("admin"): return redirect("/admin")
    NOTICES.append({"title": request.form['title'], "text": request.form['text'], "media_link": request.form.get('media_link',''), "created_at": str(datetime.now(NIGERIA_TZ))})
    set_setting("notices", json.dumps(NOTICES))
    return redirect("/admin")

@app.route('/admin/pin_notice', methods=["POST"])
def pin_notice():
    global PINNED_NOTICE
    if not session.get("admin"): return redirect("/admin")
    pinned = request.form.get('pinned','')
    if pinned:
        PINNED_NOTICE = json.dumps({"title": "📌 PINNED", "text": pinned})
        set_setting("pinned_notice", PINNED_NOTICE)
    else:
        PINNED_NOTICE = ""
        set_setting("pinned_notice", "")
    return redirect("/admin")

@app.route('/admin/change_pass', methods=["POST"])
def change_pass():
    global ADMIN_PASS
    if not session.get("admin"): return redirect("/admin")
    new = request.form.get('new_pass')
    if new:
        ADMIN_PASS = new
        set_setting("admin_pass", new)
    return redirect("/admin")

@app.route('/admin/support_chats')
def support_chats():
    if not session.get("admin"): return redirect("/admin")
    with DBSession() as db:
        dms = db.execute(sa.text("SELECT * FROM dms WHERE to_nickname='motiz_support' OR from_nickname='motiz_support' ORDER BY id DESC LIMIT 100")).mappings().all()
    html = ""
    for m in dms:
        html+=f"<div class=card><b>{m['from_nickname']} → {m['to_nickname']}</b><br>{m['text']}<br><small>{m['time']}</small><br><a class=btn.blue href=/admin/reply/{m['from_nickname']}>Reply as Support</a></div>"
    return render_template_string(BASE, title="Support Inbox", header="", content=Markup(html + "<a class=btn.blue href=/admin>Back</a>"), timer_script="")

@app.route('/admin/reply/<user>', methods=["GET","POST"])
def admin_reply(user):
    if not session.get("admin"): return redirect("/admin")
    if request.method=="POST":
        with DBSession() as db:
            db.execute(sa.text("INSERT INTO dms (from_nickname, to_nickname, text, time) VALUES ('motiz_support', :u, :t, :tm)"), {"u": user, "t": request.form['text'], "tm": str(datetime.now(NIGERIA_TZ))})
            db.commit()
        return redirect("/admin/support_chats")
    return render_template_string(BASE, title="Reply", header="", content=Markup(f"<div class=card><h2>Reply to {user} as MOTIZ SUPPORT</h2><form method=POST><textarea name=text required></textarea><button class=btn>Send as Support</button></form></div>"), timer_script="")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
