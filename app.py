from flask import Flask, render_template_string, request, redirect, session, url_for, Response
from markupsafe import Markup
from datetime import date, datetime, timedelta
import random, json, os, urllib.parse
from functools import wraps
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import pytz

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', "motiz_secret_key_2026_v42")
app.config['PROPAGATE_EXCEPTIONS'] = True

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL: raise Exception("DATABASE_URL environment variable is not set")
if DATABASE_URL.startswith("postgres://"): DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = sa.create_engine(DATABASE_URL)
DBSession = sessionmaker(bind=engine)

# ====== SETTINGS ======
PALMPAY_ACCOUNT = "8908025244"; PALMPAY_NAME = "HAMZAT KOLADE AJIMOTI"; PALMPAY_BANK = "PALMPAY"
LESSON_PRICE = 1000; QUESTION_PRICE = 500
ADMIN_PASS = os.environ.get('ADMIN_PASS', "24434"); ADMIN_NICKNAME = "admin"
FREE_Q = 30; PAID_Q = 70; TIMER_PER_QUESTION = 60
NIGERIA_TZ = pytz.timezone('Africa/Lagos')
FAVICON_URL = "https://i.imgur.com/5TCBgkN.png"; SEND_BTN_URL = "https://i.imgur.com/ADGwy5l.png"
BASE_URL = "https://motiz-e-learning-institution.onrender.com"

JSS_SUBJECTS = ["English Language", "Mathematics", "Basic Science", "Basic Technology", "Social Studies", "Civic Education", "Business Studies", "Agricultural Science", "Christian / Islamic Religious Studies (CRS/IRS)", "Physical and Health Education (PHE)"]
CLASSES = ["JSS1", "JSS2", "JSS3", "SS1", "SS2", "SS3"]
SUBJECTS = {"JSS1": JSS_SUBJECTS, "JSS2": JSS_SUBJECTS, "JSS3": JSS_SUBJECTS,"SS1_Science": ["English Language", "Mathematics", "Civic Education", "Physics", "Chemistry", "Biology", "Further Mathematics", "ICT", "Agricultural Science", "Geography"],"SS1_Commercial": ["English Language", "Mathematics", "Civic Education", "Economics", "Financial Accounting", "Commerce", "Business Management", "Government", "Computer Studies / ICT", "Marketing"],"SS1_Art": ["English Language", "Mathematics", "Civic Education", "Literature in English", "Government", "Christian / Islamic Religious Studies (CRS/IRS)", "Yoruba", "Economics", "Computer Studies / ICT", "Craft"],"SS2_Science": ["English Language", "Mathematics", "Civic Education", "Physics", "Chemistry", "Biology", "Further Mathematics", "ICT", "Agricultural Science", "Geography"],"SS2_Commercial": ["English Language", "Mathematics", "Civic Education", "Economics", "Financial Accounting", "Commerce", "Business Management", "History", "Computer Studies / ICT", "Marketing"],"SS2_Art": ["English Language", "Mathematics", "Civic Education", "Literature in English", "Government", "Christian / Islamic Religious Studies (CRS/IRS)", "Yoruba", "Economics", "Computer Studies / ICT", "Craft"],"SS3_Science": ["English Language", "Mathematics", "Civic Education", "Physics", "Chemistry", "Biology", "Further Mathematics", "ICT", "Agricultural Science", "Geography"],"SS3_Commercial": ["English Language", "Mathematics", "Civic Education", "Economics", "Financial Accounting", "Commerce", "Business Management", "Government", "Computer Studies / ICT", "Marketing"],"SS3_Art": ["English Language", "Mathematics", "Civic Education", "Literature in English", "Government", "Christian / Islamic Religious Studies (CRS/IRS)", "Yoruba", "Economics", "Computer Studies / ICT", "Craft"]}

def embed_media(link):
    if not link: return ""
    if '.jpg' in link or '.png' in link or '.gif' in link: return f"<img src='{link}' class='lesson-media'>"
    if '.mp4' in link or '.webm' in link: return f"<video src='{link}' controls class='lesson-media'></video>"
    if 'imgur.com' in link and '/a/' not in link:
        link = link.replace(".gifv", ".mp4").replace(".gif", ".mp4")
        if "imgur.com/" in link and not link.endswith(".mp4"): link = link + ".mp4"
        return f"<video src='{link}' controls autoplay loop muted class='lesson-media'></video>"
    return f"<a href='{link}' target='_blank'>Open Media</a>"

@app.route('/manifest.json')
def manifest(): return Response(json.dumps({"name": "MOTIZ E-LEARNING","short_name": "MOTIZ","start_url": "/","display": "standalone","background_color": "#0f3460","theme_color": "#0f3460","icons": [{"src": FAVICON_URL, "sizes": "512x512", "type": "image/png"}]}), mimetype='application/json')
@app.route('/sw.js')
def service_worker(): return Response("self.addEventListener('fetch', function(event) {event.respondWith(fetch(event.request).catch(function() {return caches.match(event.request);}));});", mimetype='application/javascript')

def init_db():
    with engine.connect() as conn:
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, nickname TEXT UNIQUE, name TEXT, password TEXT, class TEXT, dept TEXT, q_cycle TEXT DEFAULT 'free', q_used INTEGER DEFAULT 0, free_questions_used INTEGER DEFAULT 0, lesson_expiry DATE, correct INTEGER DEFAULT 0, wrong INTEGER DEFAULT 0, friends TEXT DEFAULT '[]', referred_by TEXT DEFAULT NULL, referral_count INTEGER DEFAULT 0, free_days INTEGER DEFAULT 0, is_verified BOOLEAN DEFAULT FALSE, payment_verified_date TEXT, is_admin BOOLEAN DEFAULT FALSE, last_login TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS payments (id SERIAL PRIMARY KEY, nickname TEXT, name TEXT, type TEXT, status TEXT, bank_used TEXT, account_name TEXT, date_paid TEXT, proof_link TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS friend_requests (id SERIAL PRIMARY KEY, from_nickname TEXT, to_nickname TEXT, status TEXT DEFAULT 'Pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(from_nickname, to_nickname));")) # FIXED: Added UNIQUE
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, nickname TEXT, name TEXT, text TEXT, likes TEXT DEFAULT '[]', comments TEXT DEFAULT '[]', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS dms (id SERIAL PRIMARY KEY, from_nickname TEXT, to_nickname TEXT, text TEXT, time TEXT, read_by TEXT DEFAULT '[]');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS groups (id SERIAL PRIMARY KEY, name TEXT, creator TEXT, members TEXT DEFAULT '[]', messages TEXT DEFAULT '[]');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS lessons (id SERIAL PRIMARY KEY, class TEXT, dept TEXT, subject TEXT, title TEXT, notes TEXT, date TEXT, media_link TEXT DEFAULT '');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS questions (id SERIAL PRIMARY KEY, key TEXT, q TEXT, options TEXT, ans TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS referrals (id SERIAL PRIMARY KEY, referrer TEXT, referred TEXT, paid BOOLEAN DEFAULT FALSE, bonus_given BOOLEAN DEFAULT FALSE);"))
        conn.commit()
init_db()

def fix_old_users():
    with DBSession() as db:
        # FIXED: Correct data types instead of making everything TEXT
        cols_int = ["q_used","free_questions_used","correct","wrong","referral_count","free_days"]
        cols_text = ["lesson_expiry","friends","referred_by","payment_verified_date","last_login"]
        cols_bool = ["is_verified","is_admin"]
        for col in cols_int:
            try: db.execute(sa.text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} INTEGER DEFAULT 0")); db.commit()
            except: db.rollback()
        for col in cols_text:
            try: db.execute(sa.text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} TEXT")); db.commit()
            except: db.rollback()
        for col in cols_bool:
            try: db.execute(sa.text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} BOOLEAN DEFAULT FALSE")); db.commit()
            except: db.rollback()
fix_old_users()

def get_setting(key, default=""):
    with DBSession() as db: return db.execute(sa.text("SELECT value FROM settings WHERE key=:k"), {"k": key}).scalar() or default
def set_setting(key, value):
    with DBSession() as db: db.execute(sa.text("INSERT INTO settings (key, value) VALUES (:k, :v) ON CONFLICT (key) DO UPDATE SET value=:v"), {"k": key, "v": value}); db.commit()

ADMIN_PASS = get_setting("admin_pass", ADMIN_PASS)
NOTICES = json.loads(get_setting("notices", json.dumps([{"title":"Welcome","text":"Welcome to MOTIZ E-LEARNING!","created_at": str(datetime.now(NIGERIA_TZ)), "media_link": "", "pinned": False}])))

def get_user():
    nickname = session.get("nickname")
    if not nickname: return None, None
    with DBSession() as db:
        user = db.execute(sa.text("SELECT * FROM users WHERE nickname=:u"), {"u": nickname}).mappings().first()
        if user: user = dict(user); user['friends'] = json.loads(user.get('friends', '[]'))
        return nickname, user

def update_last_login(nickname):
    with DBSession() as db: db.execute(sa.text("UPDATE users SET last_login=:t WHERE nickname=:u"), {"t": datetime.now(NIGERIA_TZ).strftime("%Y-%m-%d %I:%M %p"), "u": nickname}); db.commit()

def delete_old_posts_and_notices():
    global NOTICES; cutoff = datetime.now(NIGERIA_TZ) - timedelta(hours=24)
    with DBSession() as db: db.execute(sa.text("DELETE FROM posts WHERE created_at < :c"), {"c": cutoff}); db.commit()
    new_notices = []
    for n in NOTICES:
        try: notice_time = datetime.fromisoformat(n.get('created_at').replace('Z','+00:00'));
             if notice_time > cutoff: new_notices.append(n)
        except: new_notices.append(n)
    if len(new_notices)!= len(NOTICES): NOTICES = new_notices; set_setting("notices", json.dumps(NOTICES))

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        nickname, user = get_user()
        if not user: return redirect("/login")
        update_last_login(nickname)
        delete_old_posts_and_notices()
        return f(nickname, user, *args, **kwargs)
    return wrapper

BASE = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="manifest" href="/manifest.json"><meta name="theme-color" content="#0f3460"><link rel="icon" type="image/png" href="{FAVICON_URL}">
<title>{{{{title}}}}</title><style>:root{{--bg:#f0f2f5;--card:white;--text:#333;--primary:#0f3460}} body.dark{{--bg:#121212;--card:#1e1e1e;--text:#eee}}
body{{font-family:Segoe UI;background:var(--bg);color:var(--text);margin:0;padding:0;padding-bottom:120px}}
.header{{background:var(--primary);color:white;padding:10px;text-align:center;position:fixed;top:0;width:100%;z-index:1000;display:flex;justify-content:space-between;align-items:center}}
.header h1{{margin:0;font-size:0.85rem;flex:1;text-align:center;line-height:1.1;white-space:nowrap}}
.header img.logo{{width:70px;height:70px;border-radius:50%;margin-left:5px}}.theme-btn{{border:none;background:transparent;color:white;font-size:1.3rem;cursor:pointer;margin-right:10px}}
.exit-btn{{background:transparent;color:white;border:none;padding:5px 10px;text-decoration:none;font-size:1.5rem;margin-left:10px}}
.nav{{display:flex;gap:5px;background:#16213e;padding:5px;flex-wrap:wrap;position:fixed;top:80px;width:100%;overflow-x:auto;z-index:999}}
.nav a{{color:white;text-decoration:none;padding:5px 8px;border-radius:10px;border:1px solid #fff3;font-size:0.8rem}}
.container{{padding:10px;padding-top:135px}}.card{{background:var(--card);padding:12px;margin:8px 0;border-radius:10px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}}
.btn{{background:#28a745;color:white;padding:12px 15px;text-decoration:none;border-radius:8px;display:block;margin:8px 0;text-align:center;font-weight:bold;border:none;width:100%;cursor:pointer}}
.btn.red{{background:#e94560}}.btn.blue{{background:#2196f3}}.btn.orange{{background:#ff9800}}.btn.gray{{background:#6c757d;font-size:0.9rem;padding:8px;margin:6px 0}}
input,select,textarea{{width:100%;padding:10px;margin:5px 0;border-radius:5px;border:1px solid #ccc;box-sizing:border-box;font-size:1rem;background:var(--card);color:var(--text)}}
.success{{color:green;background:#d4edda;padding:10px;border-radius:5px}}.error{{color:red;background:#f8d7da;padding:10px;border-radius:5px}}
.badge{{background:#28a745;color:white;padding:2px 6px;border-radius:10px;font-size:0.7rem;margin-left:5px}}.admin-badge{{color:#1DA1F2; font-weight:bold;}}
.notice-title{{font-size:1.1rem;font-weight:bold;color:var(--primary);margin-bottom:5px}}
.chat-msg{{display:flex;margin:8px 0}}.chat-msg.me{{justify-content:flex-end}}.chat-msg.other{{justify-content:flex-start}}
.bubble{{padding:10px 15px;border-radius:18px;max-width:70%; display:flex; flex-direction:column;}}
.me.bubble{{background:#2196f3!important;color:white!important;border-bottom-right-radius:5px; align-items:flex-end;}}
.other.bubble{{background:#e0e0e0;color:#333;border-bottom-left-radius:5px; align-items:flex-start;}}body.dark.other.bubble{{background:#333;color:#eee}}
.time{{font-size:11px; color:gray; margin-top:4px;}}
.friend-card{{display:flex;align-items:center;gap:10px;padding:12px;background:var(--card);border-radius:10px;margin:8px 0;text-decoration:none;color:var(--text)}}
.friend-avatar{{width:45px;height:45px;border-radius:50%;background:var(--primary);color:white;display:flex;align-items:center;justify-content:center;font-weight:bold}}
.readonly-box{{width:100%;padding:12px;background:#eee;border:1px dashed #999;font-size:1.1rem;font-weight:bold;text-align:center;user-select:all}}
.chat-input-fixed{{position:fixed;bottom:10px;left:10px;right:10px;display:flex;gap:5px;background:var(--card);padding:10px;border-radius:15px;box-shadow:0 -2px 10px rgba(0,0,0,0.1)}}
.send-img-btn{{background:transparent;border:none;padding:0;cursor:pointer}}.send-img-btn img{{height:40px;width:40px}}.lesson-media{{width:100%;border-radius:10px;margin-top:8px}}
.like-btn{{background:transparent;border:none;cursor:pointer;font-size:1.2rem}}
.comment{{background:var(--bg);padding:8px;border-radius:8px;margin:5px 0;font-size:0.9rem}}
</style></head><body>{{{{header}}}}<div class="container">{{{{content}}}}</div><script>if('serviceWorker' in navigator){{ navigator.serviceWorker.register('/sw.js'); }}{{{{timer_script}}}}</script></body></html>"""

def get_header(nickname,user, show_nav=True, show_favicon=False):
    if not user: return ""
    exit_html = '<a href="/main" class="exit-btn">🔙</a>' if not show_favicon else ""
    favicon_html = f'<img src="{FAVICON_URL}" class="logo">' if show_favicon else ""
    theme_html = '<button class="theme-btn" onclick="document.body.classList.toggle(\'dark\')">🌙</button>'
    verified = '<span class=badge>✓ Verified</span>' if user.get('is_verified') else ""
    nav_html = """<div class="nav"><a href="/main">🏠 Home</a><a href="/exam">✍️ CBT</a><a href="/lessons">🎓 Lessons</a><a href="/community">🌍 Community</a><a href="/chat">💬 Chat</a><a href="/groups">👥 Groups</a><a href="/me">👤 Me</a></div>""" if show_nav else ""
    return f"""<div class="header">{favicon_html}{exit_html}<h1>MOTIZ E-LEARNING {verified}</h1>{theme_html}</div>{nav_html}"""

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
                db.execute(sa.text("INSERT INTO users (nickname,name,password,class,dept,referred_by,last_login) VALUES (:u,:n,:p,:c,:d,:r,:t)"),{"u": nickname, "n": name, "p": request.form['password'], "c": request.form['class'], "d": request.form.get('dept',''), "r": ref, "t": datetime.now(NIGERIA_TZ).strftime("%Y-%m-%d %I:%M %p")})
                if ref: db.execute(sa.text("INSERT INTO referrals (referrer, referred) VALUES (:r, :ref)"), {"r": ref, "ref": nickname})
                db.commit(); session["nickname"] = nickname; return redirect("/main")
    js = """<script>function d(){let c=document.getElementById('class').value;let x=document.getElementById('dept');x.innerHTML='';if(['SS1','SS2','SS3'].includes(c)){x.innerHTML='<label>Department *</label><select name=dept id=dept required><option value="">Select Department</option><option>Science</option><option>Commercial</option><option>Art</option></select>'}else{x.innerHTML='<input type=hidden name=dept value=>';}}</script>"""
    ref_box = f"<div class=card><b>Referred by:</b> {ref}</div>" if ref else ""
    form = f"<div class='card'><h2>Register</h2>{ref_box}{error}<form method=POST><input name=nickname placeholder='Nickname' required><input name=surname placeholder='Surname' required><input name=other placeholder='Other Name' required><input type=password name=password placeholder='Password' required><select name=class id=class onchange=d() required><option value=''>Select Class</option>{''.join([f'<option>{c}</option>' for c in CLASSES])}</select><div id=dept></div><button class=btn>Register</button><p>Already have account? <a href=/login>Login</a></p></form></div>{js}"
    return render_template_string(BASE, title="Register", header="", content=Markup(form), timer_script="")
@app.route('/login', methods=["GET","POST"])
def login():
    if get_user()[1]: return redirect("/main")
    error = ""
    if request.method == "POST":
        nickname = request.form["nickname"].strip().lower(); pwd = request.form["password"]
        if nickname == ADMIN_NICKNAME: error = "<div class=error>Admin cannot login here. Use /admin panel</div>"
        else:
            with DBSession() as db:
                u = db.execute(sa.text("SELECT * FROM users WHERE nickname=:u"), {"u": nickname}).mappings().first()
                if u and u["password"] == pwd: session["nickname"] = nickname; update_last_login(nickname); return redirect("/main")
                else: error = "<div class=error>Invalid Nickname or Password</div>"
    return render_template_string(BASE, title="Login", header="", content=Markup(f"<div class='card'><h2>Login</h2>{error}<form method=POST><input name=nickname placeholder='Nickname' required><input type=password name=password placeholder=Password required><button class=btn>Login</button><a class=btn.blue href=/register>Register</a></form></div>"), timer_script="")

@app.route('/main')
@login_required
def main(nickname, user):
    global NOTICES
    notices_html = ""
    for n in NOTICES:
        media = embed_media(n.get('media_link'))
        pin = "<span style='color:gold'>📌</span>" if n.get('pinned') else ""
        notices_html += f"<div class=card><div class=notice-title>{pin}{n['title']}</div>{n['text']}{media}</div>"
    status = "Paid Member" if user.get('is_verified') else f"Free: {FREE_Q - user['free_questions_used']} left"
    ref_link = f"{BASE_URL}/register?ref={nickname}"
    content = f"<div class=card><h2>Welcome {user['name']}</h2><p>Status: {status}</p><p><b>Referral Link - Tap to copy:</b></p><div class=readonly-box onclick='navigator.clipboard.writeText(this.innerText)'>{ref_link}</div><a class='btn orange' href=/pay>💳 Pay for Lessons/Questions</a></div>{notices_html}"
    return render_template_string(BASE, title="Home", header=Markup(get_header(nickname,user)), content=Markup(content), timer_script="")

@app.route('/logout')
def logout(): session.clear(); return redirect("/login")

@app.route('/pay', methods=["GET","POST"])
@login_required
def pay(nickname, user):
    error = ""
    if request.method=="POST":
        p_type = request.form['type']
        with DBSession() as db:
            db.execute(sa.text("INSERT INTO payments (nickname,name,type,status,bank_used,account_name,date_paid,proof_link) VALUES (:u,:n,:t,'Pending',:b,:a,:d,:p)"),{"u":nickname,"n":user['name'],"t":p_type,"b":PALMPAY_BANK,"a":PALMPAY_NAME,"d":str(date.today()),"p":request.form['proof']})
            db.commit(); error = "<div class=success>Payment submitted. Wait for admin verification</div>"
    return render_template_string(BASE, title="Payment", header=Markup(get_header(nickname,user)), content=Markup(f"<div class=card><h2>Make Payment</h2><p><b>Account:</b> {PALMPAY_ACCOUNT}</p><p><b>Bank:</b> {PALMPAY_BANK}</p><p><b>Name:</b> {PALMPAY_NAME}</p><form method=POST><select name=type required><option value=''>Select</option><option value=lessons>Lessons - N{LESSON_PRICE}</option><option value=questions>Questions - N{QUESTION_PRICE}</option></select><input name=proof placeholder='Paste Imgur Proof Link' required><button class=btn>Submit Payment</button></form>{error}</div>"), timer_script="")

@app.route('/exam')
@login_required
def exam(nickname, user):
    total_limit = FREE_Q + PAID_Q if user.get('is_verified') else FREE_Q
    used = user['q_used'] if user.get('is_verified') else user['free_questions_used']
    if used >= total_limit: return render_template_string(BASE, title="CBT", header=Markup(get_header(nickname,user)), content=Markup(f"<div class=error>You have used all your questions. <a href=/pay>Pay N{QUESTION_PRICE} to continue</a></div>"), timer_script="")
    class_key = user['class'] if user['class'].startswith('JSS') else f"{user['class']}_{user['dept']}"
    subjects = SUBJECTS.get(class_key, [])
    sub_html = "".join([f"<a class=btn href=/start/{urllib.parse.quote(class_key)}/{urllib.parse.quote(s)}>{s}</a>" for s in subjects])
    return render_template_string(BASE, title="CBT", header=Markup(get_header(nickname,user)), content=Markup(f"<div class=card><h2>Select Subject</h2>{sub_html}</div>"), timer_script="")

@app.route('/start/<path:key>/<path:sub>', methods=["GET","POST"])
@login_required
def start(nickname, user, key, sub):
    key = urllib.parse.unquote(key); sub = urllib.parse.unquote(sub)
    total_limit = FREE_Q + PAID_Q if user.get('is_verified') else FREE_Q
    if not user.get('is_verified') and user['free_questions_used'] >= FREE_Q: return redirect("/exam")
    if user.get('is_verified') and user['q_used'] >= total_limit: return redirect("/exam")
    full_key = f"{key}_{sub}"

    with DBSession() as db:
        q_list = db.execute(sa.text("SELECT * FROM questions WHERE key=:k"), {"k": full_key}).mappings().all()

    if len(q_list) == 0:
        return render_template_string(BASE, title="No Questions", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=error>No questions found for <b>{sub}</b><br>Key searched: {full_key}</div>"), timer_script="")

    session_key = f"exam_{full_key}"; answers_key = f"answers_{full_key}"
    if request.method == "GET":
        questions = list(q_list); random.shuffle(questions)
        session[session_key] = questions[:total_limit]; session[answers_key] = {}; session['q_index'] = 0

    questions = session.get(session_key, []); answers = session.get(answers_key, {}); q_index = session.get('q_index', 0)
    if request.method == "POST":
        if "save_answer" in request.form and request.form.get("answer"): session[answers_key][str(q_index)] = request.form.get("answer"); session.modified = True
        if "next" in request.form:
            if str(q_index) not in answers: session[answers_key][str(q_index)] = "SKIPPED"
            session['q_index'] = q_index + 1
        if "prev" in request.form: session['q_index'] = q_index - 1
        if "submit_exam" in request.form: return redirect("/result")
        if "timeout" in request.form:
            if str(q_index) not in answers: session[answers_key][str(q_index)] = "TIMEOUT"
            session.modified = True; session['q_index'] = q_index + 1
        return redirect(f"/start/{urllib.parse.quote(key)}/{urllib.parse.quote(sub)}")

    if q_index >= len(questions): return redirect("/result")
    q = questions[q_index]; q['options'] = json.loads(q['options']); saved_ans = answers.get(str(q_index))
    timer_js = Markup(f"""let timeLeft = {TIMER_PER_QUESTION}; const qKey = '{full_key}_{q_index}'; const timerEl = document.createElement('div'); timerEl.style.cssText='position:fixed;top:60px;right:10px;background:#ff9800;color:white;padding:8px 12px;border-radius:8px;font-weight:bold;z-index:1001'; document.body.appendChild(timerEl); let submitted = false; let savedTime = localStorage.getItem(qKey); if(savedTime && parseInt(savedTime) > 0){{ timeLeft = parseInt(savedTime); }} function updateTimer(){{ if(timeLeft < 0) timeLeft = 0; localStorage.setItem(qKey, timeLeft); let m = Math.floor(timeLeft / 60); let s = timeLeft % 60; s = s < 10? '0' + s : s; timerEl.innerHTML = '⏰ ' + m + ':' + s; if(timeLeft <= 0 &&!submitted){{ submitted = true; localStorage.removeItem(qKey); let form = document.getElementById('exam_form'); let input = document.createElement('input'); input.type = 'hidden'; input.name = 'save_answer'; input.value = '1'; form.appendChild(input); form.submit(); setTimeout(()=>{{if(!submitted){{document.getElementById('timeout_form').submit();}}}}, 200); }} timeLeft--; }} updateTimer(); let timerInterval = setInterval(updateTimer, 1000); document.getElementById('exam_form').addEventListener('submit', ()=>{{localStorage.removeItem(qKey); clearInterval(timerInterval);}});""")
    options_html = "".join([f"<label style='display:block;padding:10px;margin:8px 0;background:var(--bg);border-radius:8px'><input type=radio name=answer value='{opt}' {'checked' if saved_ans==opt else ''}> {opt}</label>" for opt in q['options']])
    prev_btn = f"<button name=prev class='btn gray' {'disabled' if q_index==0 else ''}>⬅️ Prev</button>" if q_index > 0 else ""
    next_btn = f"<button name=next class='btn blue'>Next ➡️</button>" if q_index < len(questions)-1 else f"<button name=submit_exam class='btn orange'>Submit Exam</button>"
    content = f"<div class='card'><h2>{sub}</h2><h3>Question {q_index+1} of {len(questions)}</h3><p><b>{q['q']}</b></p><form method=POST id=exam_form>{options_html}<div style='display:flex;gap:10px'>{prev_btn}{next_btn}</div></form><form method=POST id=timeout_form style=display:none><input type=hidden name=timeout value=1></form></div>"
    return render_template_string(BASE, title=sub, header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script=timer_js)

@app.route('/result')
@login_required
def result(nickname, user):
    session_keys = [k for k in session.keys() if k.startswith('exam_')]
    if not session_keys: return redirect("/exam")
    full_key = session_keys[0].replace('exam_','')
    answers_key = f"answers_{full_key}"
    questions = session.get(session_keys[0], [])
    answers = session.get(answers_key, {})
    correct = 0; wrong = 0
    for i, q in enumerate(questions):
        user_ans = answers.get(str(i), "SKIPPED")
        if user_ans == q['ans']: correct += 1
        else: wrong += 1
    with DBSession() as db:
        if user.get('is_verified'):
            db.execute(sa.text("UPDATE users SET correct=correct+:c, wrong=wrong+:w, q_used=q_used+:t WHERE nickname=:u"), {"c": correct, "w": wrong, "t": len(questions), "u": nickname})
        else:
            db.execute(sa.text("UPDATE users SET correct=correct+:c, wrong=wrong+:w, free_questions_used=free_questions_used+:t WHERE nickname=:u"), {"c": correct, "w": wrong, "t": len(questions), "u": nickname})
        db.commit()
    session.pop(session_keys[0], None); session.pop(answers_key, None)
    return render_template_string(BASE, title="Result", header=Markup(get_header(nickname,user)), content=Markup(f"<div class=card><h2>Exam Submitted</h2><p>Correct: {correct}</p><p>Wrong: {wrong}</p><a class=btn href=/exam>Back to CBT</a></div>"), timer_script="")

@app.route('/lessons')
@login_required
def lessons(nickname, user):
    class_key = user['class'] if user['class'].startswith('JSS') else f"{user['class']}_{user['dept']}"
    with DBSession() as db:
        lessons = db.execute(sa.text("SELECT * FROM lessons WHERE class=:c AND (dept=:d OR dept='') ORDER BY id DESC"), {"c": user['class'], "d": user.get('dept','')}).mappings().all()
    lessons_html = "".join([f"<div class=card><h3>{l['subject']}: {l['title']}</h3>{l['notes']}{embed_media(l['media_link'])}<p style=font-size:0.8rem;color:gray>Date: {l['date']}</p></div>" for l in lessons])
    return render_template_string(BASE, title="Lessons", header=Markup(get_header(nickname,user)), content=Markup(f"<div class=card><h2>Lessons for {class_key}</h2></div>{lessons_html or '<div class=card>No lessons yet</div>'}"), timer_script="")
@app.route('/community', methods=["GET","POST"])
@login_required
def community(nickname, user):
    with DBSession() as db:
        if request.method=="POST":
            if "new_post" in request.form:
                post_text = request.form["post"][:1000]
                media_link = request.form.get("media_link","")
                name_display = user["name"] + (" <span class=admin-badge>ADMIN OFFICIAL ✔️</span>" if user.get('is_admin') else "")
                db.execute(sa.text("INSERT INTO posts (nickname, name, text, likes, comments) VALUES (:u, :n, :t, '[]', '[]')"),{"u": nickname, "n": name_display + f"<br>{embed_media(media_link)}", "t": post_text})
            if "like_post" in request.form:
                pid = request.form['like_post']
                post = db.execute(sa.text("SELECT likes FROM posts WHERE id=:id"), {"id": pid}).scalar()
                likes = json.loads(post)
                if nickname in likes: likes.remove(nickname)
                else: likes.append(nickname)
                db.execute(sa.text("UPDATE posts SET likes=:l WHERE id=:id"), {"l": json.dumps(likes), "id": pid})
            if "comment_post" in request.form:
                pid = request.form['comment_post']
                comment = request.form['comment_text'][:300]
                post = db.execute(sa.text("SELECT comments FROM posts WHERE id=:id"), {"id": pid}).mappings().first()
                comments = json.loads(post['comments'])
                comments.append({"user": nickname, "text": comment, "time": datetime.now(NIGERIA_TZ).strftime("%I:%M %p")})
                db.execute(sa.text("UPDATE posts SET comments=:c WHERE id=:id"), {"c": json.dumps(comments), "id": pid})
            db.commit(); return redirect("/community")
        posts = db.execute(sa.text("SELECT * FROM posts ORDER BY id DESC")).mappings().all()

    posts_html = ""
    for p in posts:
        likes = json.loads(p['likes']); comments = json.loads(p['comments'])
        like_btn = f"<form method=POST style=display:inline><button name=like_post value={p['id']} class=like-btn>{'❤️' if nickname in likes else '🤍'} {len(likes)}</button></form>"
        comments_html = "".join([f"<div class=comment><b>{c['user']}:</b> {c['text']} <span class=time>{c['time']}</span></div>" for c in comments])
        posts_html += f"<div class=card><b>{p['name']}</b>: {p['text']}<br>{like_btn}<div>{comments_html}</div><form method=POST><input name=comment_text placeholder='Write comment...' required><button name=comment_post value={p['id']} class='btn gray'>Comment</button></form></div>"

    image_input = "<input name=media_link placeholder='Paste Imgur Image Link Here for Post'>" if user.get('is_admin') else ""
    return render_template_string(BASE, title="Community", header=Markup(get_header(nickname,user)), content=Markup(f"<div class=card><h2>Community</h2><form method=POST><textarea name=post placeholder='Whats on your mind?' required maxlength=1000></textarea>{image_input}<button class='send-img-btn'><img src='{SEND_BTN_URL}'></button><input type=hidden name=new_post value=1></form></div>{posts_html}"), timer_script="")

@app.route('/chat', methods=["GET","POST"])
@login_required
def chat(nickname, user):
    with DBSession() as db:
        if request.method=="POST" and "add_friend" in request.form:
            to_user = request.form['add_friend'].strip().lower()
            exists = db.execute(sa.text("SELECT nickname FROM users WHERE nickname=:u"), {"u": to_user}).scalar()
            if exists and to_user!= nickname:
                db.execute(sa.text("INSERT INTO friend_requests (from_nickname, to_nickname) VALUES (:f, :t) ON CONFLICT DO NOTHING"), {"f": nickname, "t": to_user})
                db.commit()

        friends_html = ""
        for f in user['friends']:
            name = db.execute(sa.text("SELECT name FROM users WHERE nickname=:u"), {"u": f}).scalar(); initial = name[0].upper() if name else "?"
            friends_html += f"<a class=friend-card href=/dm/{f}><div class=friend-avatar>{initial}</div><div><b>{name}</b></div></a>"

        reqs = db.execute(sa.text("SELECT * FROM friend_requests WHERE to_nickname=:u AND status='Pending'"), {"u": nickname}).mappings().all()
        req_html = "".join([f"<div class=card>{r['from_nickname']} sent you a friend request <form method=POST><button name=accept_req value={r['id']} class='btn blue'>Accept</button></form></div>" for r in reqs])

        if request.method=="POST" and "accept_req" in request.form:
            rid = request.form['accept_req']
            req = db.execute(sa.text("SELECT * FROM friend_requests WHERE id=:id"), {"id": rid}).mappings().first()
            f1 = json.loads(db.execute(sa.text("SELECT friends FROM users WHERE nickname=:u"), {"u": req['from_nickname']}).scalar())
            f2 = json.loads(db.execute(sa.text("SELECT friends FROM users WHERE nickname=:u"), {"u": req['to_nickname']}).scalar())
            f1.append(req['to_nickname']); f2.append(req['from_nickname'])
            db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(f1), "u": req['from_nickname']})
            db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(f2), "u": req['to_nickname']})
            db.execute(sa.text("UPDATE friend_requests SET status='Accepted' WHERE id=:id"), {"id": rid}); db.commit(); return redirect("/chat")

    complaint_btn = f"<a class='btn orange' href=/dm/{ADMIN_NICKNAME}>🛡️ Lodge Complaint to Admin</a>"
    content = f"<div class=card><h2>DM</h2>{complaint_btn}</div><div class=card><h3>Add Friend</h3><form method=POST><input name=add_friend placeholder='Enter nickname'><button class=btn>Add Friend</button></form></div>{req_html}<div class=card><h3>Your Friends</h3>{friends_html or '<p>No friends</p>'}</div>"
    return render_template_string(BASE, title="Chat", header=Markup(get_header(nickname,user)), content=Markup(content), timer_script="")

@app.route('/dm/<to_nickname>', methods=["GET","POST"])
@login_required
def dm_chat(nickname, user, to_nickname):
    if to_nickname not in user['friends'] and to_nickname!= ADMIN_NICKNAME: return redirect("/chat")
    with DBSession() as db:
        if request.method=="POST":
            msg_text = request.form["msg"][:700]
            db.execute(sa.text("INSERT INTO dms (from_nickname, to_nickname, text, time, read_by) VALUES (:f, :t, :txt, :time, :r)"),{"f": nickname, "t": to_nickname, "txt": msg_text, "time": datetime.now(NIGERIA_TZ).strftime("%I:%M %p"), "r": json.dumps([nickname])})
            db.commit(); return redirect(f"/dm/{to_nickname}")
        chat = db.execute(sa.text("SELECT * FROM dms WHERE (from_nickname=:u AND to_nickname=:t) OR (from_nickname=:t AND to_nickname=:u) ORDER BY id"),{"u": nickname, "t": to_nickname}).mappings().all()
        to_name = db.execute(sa.text("SELECT name FROM users WHERE nickname=:u"), {"u": to_nickname}).scalar()
        if to_nickname == ADMIN_NICKNAME: to_name = "ADMIN OFFICIAL ✔️"
    msgs = "".join([f"<div class='chat-msg {'me' if m['from_nickname']==nickname else 'other'}'><div class='bubble {'me' if m['from_nickname']==nickname else 'other'}'><b>{m['from_nickname']}:</b> {m['text']} <span class=time>{m['time']}</span></div></div>" for m in chat])
    return render_template_string(BASE, title=f"Chat with {to_name}", header=Markup(get_header(nickname,user)), content=Markup(f"<div class=card><div class=chat-box>{msgs}</div></div><form method=POST class=chat-input-fixed><input name=msg placeholder='Type message...' required><button class='send-img-btn'><img src='{SEND_BTN_URL}'></button></form>"), timer_script="")

@app.route('/groups', methods=["GET","POST"])
@login_required
def groups(nickname, user):
    with DBSession() as db:
        if request.method=="POST" and "create_group" in request.form:
            db.execute(sa.text("INSERT INTO groups (name, creator, members) VALUES (:n, :c, :m)"), {"n": request.form['group_name'], "c": nickname, "m": json.dumps([nickname])})
            db.commit(); return redirect("/groups")
        my_groups = db.execute(sa.text("SELECT * FROM groups WHERE members LIKE :u"), {"u": f'%"{nickname}"%'}).mappings().all()
    group_html = "".join([f"<div class=card><h3>{g['name']}</h3><p>Creator: {g['creator']}</p><a class=btn.blue href=/group_chat/{g['id']}>Open Group</a></div>" for g in my_groups])
    return render_template_string(BASE, title="Groups", header=Markup(get_header(nickname,user)), content=Markup(f"<div class=card><h2>Groups</h2><form method=POST><input name=group_name placeholder='Group Name' required><button name=create_group class=btn>Create Group</button></form></div>{group_html or '<div class=card>No groups yet</div>'}"), timer_script="")

@app.route('/group_chat/<group_id>', methods=["GET","POST"])
@login_required
def group_chat(nickname, user, group_id):
    with DBSession() as db:
        group = db.execute(sa.text("SELECT * FROM groups WHERE id=:id"), {"id": group_id}).mappings().first()
        if nickname not in json.loads(group['members']): return redirect("/groups")
        if request.method=="POST":
            msgs = json.loads(group['messages'])
            msgs.append({"user": nickname, "text": request.form['msg'], "time": datetime.now(NIGERIA_TZ).strftime("%I:%M %p")})
            db.execute(sa.text("UPDATE groups SET messages=:m WHERE id=:id"), {"m": json.dumps(msgs), "id": group_id}); db.commit(); return redirect(f"/group_chat/{group_id}")
    msgs_html = "".join([f"<div class=card><b>{m['user']}</b>: {m['text']} <span class=time>{m['time']}</span></div>" for m in json.loads(group['messages'])])
    return render_template_string(BASE, title=group['name'], header=Markup(get_header(nickname,user)), content=Markup(f"<div class=card><h2>{group['name']}</h2>{msgs_html}</div><form method=POST class=chat-input-fixed><input name=msg placeholder='Type message...' required><button class='send-img-btn'><img src='{SEND_BTN_URL}'></button></form>"), timer_script="")

@app.route('/me')
@login_required
def me(nickname, user):
    ref_bonus = f"<p>Referrals: {user['referral_count']} | Free Days: {user['free_days']}</p>" if user['referral_count'] > 0 else ""
    return render_template_string(BASE, title="Me", header=Markup(get_header(nickname,user)), content=Markup(f"<div class=card><h2>{user['name']}</h2><p>Class: {user['class']} {user.get('dept','')}</p><p>Score: {user['correct']} Correct, {user['wrong']} Wrong</p>{ref_bonus}<a class='btn red' href=/logout>Logout</a></div>"), timer_script="")
@app.route('/admin_chat/<student_nickname>', methods=["GET","POST"])
@login_required
def admin_chat(nickname, user, student_nickname):
    if not session.get("admin_logged_in"): return redirect("/admin")
    with DBSession() as db:
        admin_exists = db.execute(sa.text("SELECT nickname FROM users WHERE nickname=:a"), {"a": ADMIN_NICKNAME}).scalar()
        if not admin_exists: db.execute(sa.text("INSERT INTO users (nickname,name,password,is_admin,is_verified) VALUES (:u,'ADMIN OFFICIAL',:p,TRUE,TRUE)"),{"u": ADMIN_NICKNAME, "p": ADMIN_PASS}); db.commit()
    if request.method=="POST":
        msg_text = request.form["msg"][:700]
        if request.form.get("media_link"): msg_text += f"<br>{embed_media(request.form.get('media_link'))}"
        with DBSession() as db:
            db.execute(sa.text("INSERT INTO dms (from_nickname, to_nickname, text, time, read_by) VALUES (:f, :t, :txt, :time, :r)"),{"f": ADMIN_NICKNAME, "t": student_nickname, "txt": msg_text, "time": datetime.now(NIGERIA_TZ).strftime("%I:%M %p"), "r": json.dumps([ADMIN_NICKNAME])})
            db.commit(); return redirect(f"/admin_chat/{student_nickname}")
    with DBSession() as db:
        chat = db.execute(sa.text("SELECT * FROM dms WHERE (from_nickname=:u AND to_nickname=:t) OR (from_nickname=:t AND to_nickname=:u) ORDER BY id"),{"u": ADMIN_NICKNAME, "t": student_nickname}).mappings().all()
        student_name = db.execute(sa.text("SELECT name FROM users WHERE nickname=:u"), {"u": student_nickname}).scalar()
    msgs = "".join([f"<div class='chat-msg {'me' if m['from_nickname']==ADMIN_NICKNAME else 'other'}'><div class='bubble {'me' if m['from_nickname']==ADMIN_NICKNAME else 'other'}'><b>{'ADMIN OFFICIAL ✔️' if m['from_nickname']==ADMIN_NICKNAME else m['from_nickname']}:</b> {m['text']} <span class=time>{m['time']}</span></div></div>" for m in chat])
    content = f"<div class=card><h2>Chat with {student_name}</h2><div class=chat-box>{msgs or '<p style=text-align:center;color:gray>No messages yet</p>'}</div></div><form method=POST class=chat-input-fixed><input name=msg placeholder='Type reply...' required maxlength=700 style='flex:1'><input name=media_link placeholder='Imgur Image Link'><button class='send-img-btn'><img src='{SEND_BTN_URL}'></button></form>"
    return render_template_string(BASE, title=f"Chat {student_name}", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")

@app.route('/admin_attendance')
@login_required
def admin_attendance(nickname, user):
    if not session.get("admin_logged_in"): return redirect("/admin")
    with DBSession() as db:
        students = db.execute(sa.text("SELECT * FROM users WHERE nickname!=:a ORDER BY last_login DESC NULLS LAST"), {"a": ADMIN_NICKNAME}).mappings().all()
    rows = ""
    for s in students:
        total = s['correct'] + s['wrong']
        score = f"{s['correct']}/{total}" if total > 0 else "0/0"
        last = s['last_login'] or "Never"
        rows += f"<tr><td>{s['name']}</td><td>{s['class']}</td><td>{score}</td><td>{last}</td></tr>"
    content = f"<div class=card><h2>Attendance - Last Login Time</h2><table style='width:100%'><tr><th>Name</th><th>Class</th><th>Score</th><th>Last Login</th></tr>{rows}</table></div>"
    return render_template_string(BASE, title="Attendance", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")

@app.route('/admin', methods=["GET","POST"])
@login_required
def admin(nickname, user):
    global ADMIN_PASS, NOTICES
    if not session.get("admin_logged_in"):
        error = ""
        if request.method=="POST" and "login_pass" in request.form:
            if request.form.get("login_pass")== ADMIN_PASS: session["admin_logged_in"] = True; return redirect("/admin")
            else: error = "<div class=error>Wrong Password</div>"
        return render_template_string(BASE, title="Admin", header="", content=Markup(f"<div class='card'><h2>🔒 Admin Login</h2>{error}<form method=POST><input type=password name=login_pass placeholder='Enter Admin Password' required><button class=btn>Login</button></form></div>"), timer_script="")

    error = ""; bulk_result = ""
    q_target = request.args.get('q_target'); l_target = request.args.get('l_target')

    if request.method=="POST":
        with DBSession() as db:
            if "create_admin" in request.form:
                db.execute(sa.text("DELETE FROM users WHERE nickname=:a"), {"a": ADMIN_NICKNAME})
                db.execute(sa.text("INSERT INTO users (nickname,name,password,is_admin,is_verified) VALUES (:u,'ADMIN OFFICIAL',:p,TRUE,TRUE)"),{"u": ADMIN_NICKNAME, "p": ADMIN_PASS}); db.commit()
                error = "<div class=success>✅ Admin Account Ready</div>"

            if "verify_id" in request.form:
                req = db.execute(sa.text("SELECT * FROM payments WHERE id=:id"), {"id": request.form["verify_id"]}).mappings().first()
                if req["type"] == "questions": db.execute(sa.text("UPDATE users SET q_cycle='paid' WHERE nickname=:u"), {"u": req["nickname"]})
                if req["type"] == "lessons": db.execute(sa.text("UPDATE users SET lesson_expiry=:d, is_verified=TRUE, payment_verified_date=:today WHERE nickname=:u"), {"d": str(date.today() + timedelta(days=15)), "today": str(date.today()), "u": req["nickname"]})
                ref = db.execute(sa.text("SELECT referred_by FROM users WHERE nickname=:u"), {"u": req["nickname"]}).scalar()
                if ref: db.execute(sa.text("UPDATE users SET free_days=free_days+5 WHERE nickname=:r"), {"r": ref}); db.execute(sa.text("UPDATE users SET referral_count=referral_count+1 WHERE nickname=:r"), {"r": ref})
                db.execute(sa.text("UPDATE payments SET status='Verified' WHERE id=:id"), {"id": request.form["verify_id"]}); db.commit(); error = "<div class=success>Payment Verified</div>"

            if "add_question" in request.form:
                options = json.dumps([request.form['opt_a'], request.form['opt_b'], request.form['opt_c'], request.form['opt_d']])
                db.execute(sa.text("INSERT INTO questions (key, q, options, ans) VALUES (:k, :q, :o, :a)"),{"k": request.form['q_key'], "q": request.form['question'], "o": options, "a": request.form['answer']}); db.commit(); error = "<div class=success>Question Added</div>"

            if "bulk_upload" in request.form:
                lines = request.form['bulk_text'].strip().split('\n'); count = 0
                for line in lines:
                    if '|' in line:
                        parts = line.split('|')
                        if len(parts) == 7:
                            options = json.dumps([parts[2], parts[3], parts[4], parts[5]])
                            db.execute(sa.text("INSERT INTO questions (key, q, options, ans) VALUES (:k, :q, :o, :a)"),{"k": request.form['bulk_key'], "q": parts[1], "o": options, "a": parts[6]}); count += 1
                db.commit(); bulk_result = f"<div class=success>{count} Questions Added</div>"

            if "add_lesson" in request.form:
                db.execute(sa.text("INSERT INTO lessons (class, dept, subject, title, notes, date, media_link) VALUES (:c, :d, :s, :t, :n, :dt, :m)"),{"c": request.form['l_class'], "d": request.form.get('l_dept',''), "s": request.form['l_subject'], "t": request.form['l_title'], "n": request.form['l_notes'], "dt": str(date.today()), "m": request.form.get('media_link','')}); db.commit(); error = "<div class=success>Lesson Added</div>"

            if "post_notice" in request.form:
                NOTICES.append({"title": request.form['notice_title'], "text": request.form['notice_text'], "created_at": str(datetime.now(NIGERIA_TZ)), "media_link": request.form.get('media_link',''), "pinned": False}); set_setting("notices", json.dumps(NOTICES)); error = "<div class=success>Notice Posted</div>"

            if "pin_notice" in request.form:
                idx = int(request.form['pin_notice']);
                for i in range(len(NOTICES)): NOTICES[i]['pinned'] = False
                NOTICES[idx]['pinned'] = True; set_setting("notices", json.dumps(NOTICES)); error = "<div class=success>Notice Pinned</div>"

            if "clear_all_data" in request.form:
                db.execute(sa.text("DELETE FROM questions")); db.execute(sa.text("DELETE FROM lessons")); db.execute(sa.text("DELETE FROM payments")); db.commit(); error = "<div class=success>All Data Cleared</div>"

    with DBSession() as db:
        pending_reqs = db.execute(sa.text("SELECT * FROM payments WHERE status='Pending'")).mappings().all()
        pending_complaints = db.execute(sa.text("SELECT DISTINCT from_nickname FROM dms WHERE to_nickname=:a ORDER BY id DESC"), {"a": ADMIN_NICKNAME}).mappings().all()

    pending_html = "".join([f"<div class='card'><b>{r['name']}</b> for {r['type']}<br><a href={r['proof_link']} target=_blank>View Proof</a><form method=POST><input type=hidden name=verify_id value={r['id']}><button class=btn>Verify</button></form></div>" for r in pending_reqs])
    complaints_html = "".join([f"<a href=/admin_chat/{c['from_nickname']} class=btn.blue>💬 Chat with {c['from_nickname']}</a>" for c in pending_complaints])
    notices_admin = "".join([f"<div class=card>{i+1}. {n['title']} <form method=POST style=display:inline><button name=pin_notice value={i} class='btn gray'>📌 Pin</button></form></div>" for i,n in enumerate(NOTICES)])

    keys = ["JSS1","JSS2","JSS3","SS1_Science","SS1_Commercial","SS1_Art","SS2_Science","SS2_Commercial","SS2_Art","SS3_Science","SS3_Commercial","SS3_Art"]
    labels = ["JSS1","JSS2","JSS3","SS1 Science","SS1 Commercial","SS1 Art","SS2 Science","SS2 Commercial","SS2 Art","SS3 Science","SS3 Commercial","SS3 Art"]
    group1 = "".join([f"<a href=/admin?q_target={k} class=btn.gray>➕ Add Q: {l}</a><a href=/admin?q_target={k}&bulk=1 class=btn.orange>📦 Bulk Q: {l}</a>" for k,l in zip(keys,labels)])
    group2 = "".join([f"<a href=/admin?l_target={k} class=btn.gray>➕ Add Lesson: {l}</a>" for k,l in zip(keys,labels)])

    add_q_form = f"<div class=card><h3>Add Question to {q_target}</h3><form method=POST><input type=hidden name=q_key value={q_target}><textarea name=question placeholder='Question' required></textarea><input name=opt_a placeholder='Option A'><input name=opt_b placeholder='Option B'><input name=opt_c placeholder='Option C'><input name=opt_d placeholder='Option D'><input name=answer placeholder='Correct Answer'><button name=add_question class=btn>Add</button></form></div>" if q_target and not request.args.get('bulk') else ""
    bulk_form = f"<div class=card><h3>Bulk Upload to {q_target}</h3><form method=POST><input type=hidden name=bulk_key value={q_target}><textarea name=bulk_text placeholder='Format: 1|Question|A|B|C|D|A' rows=10 required></textarea><button name=bulk_upload class=btn.orange>Upload</button></form>{bulk_result}</div>" if q_target and request.args.get('bulk') else ""
    add_l_form = f"<div class=card><h3>Add Lesson to {l_target}</h3><form method=POST><input type=hidden name=l_class value={l_target.split('_')[0]}><input type=hidden name=l_dept value={l_target.split('_')[1] if '_' in l_target else ''}><input name=l_subject placeholder='Subject' required><input name=l_title placeholder='Title' required><textarea name=l_notes placeholder='Notes' required></textarea><input name=media_link placeholder='Imgur Link'><button name=add_lesson class=btn>Add Lesson</button></form></div>" if l_target else ""

    form = f'\
<div class="card"><h2>Admin Panel</h2>{error}</div>\
<div class="card"><h2>👑 GROUP 0: COMPLAINTS</h2>{complaints_html or "<p>No complaints yet</p>"}<form method=POST><button name=create_admin class="btn orange">Create/Reset Admin Account</button></form></div>\
{add_q_form}{bulk_form}{add_l_form}\
<div class="card"><h2>📝 GROUP 1: CBT - ADD QUESTIONS</h2><div style="display:flex;flex-direction:column;gap:10px">{group1}</div></div>\
<div class="card"><h2>🎓 GROUP 2: LESSONS</h2><div style="display:flex;flex-direction:column;gap:10px">{group2}</div></div>\
<div class="card"><h2>👥 GROUP 3: STUDENT MANAGEMENT</h2><h3>Confirm Payment</h3>{pending_html or "<p>No pending payments</p>"}<a href=/admin_attendance class=btn.blue>View Attendance</a><h3>Manage Notices</h3>{notices_admin}<form method=POST><h3>Post New Notice</h3><input name=notice_title placeholder="Notice Title" required><textarea name=notice_text placeholder="Notice Message" required></textarea><input name=media_link placeholder="Image/Video Imgur Link optional"><button name=post_notice class="send-img-btn"><img src="{SEND_BTN_URL}"></button></form></div>\
<div class="card"><h2>🛑 DANGER ZONE</h2><form method=POST onsubmit="return confirm(\'Delete ALL?\')"><button name=clear_all_data class="btn red">Clear All Old Data</button></form></div>'
    return render_template_string(BASE, title="Admin", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(form), timer_script="")

if __name__ == '__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
