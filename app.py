from flask import Flask, render_template_string, request, redirect, session
from markupsafe import Markup
from datetime import date, datetime, timedelta
import random, json, os, urllib.parse
from functools import wraps
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import pytz # FOR NIGERIA TIME

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', "motiz_secret_key_2026_v9_6")

# ====== RENDER DATABASE CONNECTION - SECURE ======
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise Exception("DATABASE_URL environment variable is not set")

engine = sa.create_engine(DATABASE_URL)
DBSession = sessionmaker(bind=engine)

PALMPAY_ACCOUNT = "8908025244"
PALMPAY_NAME = "HAMZAT KOLADE AJIMOTI"
PALMPAY_BANK = "PALMPAY"
LESSON_PRICE = 1000
QUESTION_PRICE = 500
ADMIN_PASS = os.environ.get('ADMIN_PASS', "24434")
FREE_Q = 30
PAID_Q = 70
TIMER_PER_QUESTION = 120 # 2 MINUTES PER QUESTION

NIGERIA_TZ = pytz.timezone('Africa/Lagos')

# ====== EMOJI GROUPS ======
EMOJI_GROUPS = {
    "😀 Smile": "😀 😃 😄 😁 😆 😅 😂 🤣 😊 😇 🙂 🙃 😉 😌 😍 🥰 😘 😗 😙 😚",
    "😎 Cool": "😎 🤓 🧐 🤠 🤩 🥳 🤗 😏 😒 😑 😶‍🌫️ 😮‍💨 😵‍💫 😵 🤯 🤔 🤭 🤫 🤐",
    "😭 Sad": "😢 😭 😞 😔 😟 😕 🙁 ☹️ 😣 😖 😫 😩 😤 😡 🤬 😠 😈 👿 💀",
    "❤️ Love": "❤️ 🧡 💛 💚 💙 💜 🖤 🤍 🤎 💕 💖 💗 💘 💝 💞 💟 ❣️ 💌 💋",
    "🙌 Hands": "👋 🤚 🖐️ ✋ 🖖 👌 🤏 ✌️ 🤞 🤟 🤘 🤙 👈 👉 👆 🖕 👇 ☝️ 👏",
    "⚽ Sports": "⚽ 🏀 🏈 ⚾ 🥎 🎾 🏐 🏉 🥏 🎱 🪀 🏓 🏸 🏒 🏑 🥍 🏏 🥅 ⛳ 🥊",
    "🎓 School": "📚 📖 📝 ✏️ 📐 📏 📊 📈 📉 🧮 🔬 🔭 🧪 🧬 🦠 🩺 💊 💉 🌡️ 🧠",
    "🎉 Party": "🎉 🎊 🎈 🎁 🎀 🎗️ 🎟️ 🎫 🎖️ 🏆 🥇 🥈 🥉 ⚽ 🏅 🎯 🎪 🎨 🎭 🎤",
    "🍕 Food": "🍎 🍐 🍊 🍋 🍌 🍉 🍇 🍓 🍈 🍒 🍑 🥭 🍍 🥥 🥝 🍅 🍆 🥑 🥦 🥬",
    "🌍 Nature": "🌍 🌎 🌏 🌐 🌑 🌒 🌓 🌔 🌕 🌖 🌗 🌘 🌙 🌛 🌜 ⭐ 🌟 ⚡ 🔥 💧"
}

# ====== CREATE TABLES ======
def init_db():
    with engine.connect() as conn:
        conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            nickname TEXT UNIQUE,
            name TEXT,
            password TEXT,
            class TEXT,
            dept TEXT,
            q_cycle TEXT DEFAULT 'free',
            q_used INTEGER DEFAULT 0,
            lesson_expiry DATE,
            correct INTEGER DEFAULT 0,
            wrong INTEGER DEFAULT 0,
            friends TEXT DEFAULT '[]',
            referred_by TEXT DEFAULT NULL,
            referral_count INTEGER DEFAULT 0,
            free_days INTEGER DEFAULT 0,
            is_verified BOOLEAN DEFAULT FALSE
        );
        """))
        conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            nickname TEXT,
            name TEXT,
            type TEXT,
            status TEXT,
            bank_used TEXT,
            account_name TEXT,
            date_paid TEXT
        );
        """))
        conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS friend_requests (
            id SERIAL PRIMARY KEY,
            from_nickname TEXT,
            to_nickname TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """))
        conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS posts (
            id SERIAL PRIMARY KEY,
            nickname TEXT,
            name TEXT,
            text TEXT,
            emoji TEXT,
            likes TEXT DEFAULT '[]',
            dislikes TEXT DEFAULT '[]',
            comments TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            views TEXT DEFAULT '[]'
        );
        """))
        conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS dms (
            id SERIAL PRIMARY KEY,
            from_nickname TEXT,
            to_nickname TEXT,
            text TEXT,
            time TEXT
        );
        """))
        conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS groups (
            id SERIAL PRIMARY KEY,
            name TEXT,
            creator TEXT,
            members TEXT DEFAULT '[]',
            messages TEXT DEFAULT '[]'
        );
        """))
        conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS lessons (
            id SERIAL PRIMARY KEY,
            class TEXT,
            dept TEXT,
            subject TEXT,
            title TEXT,
            notes TEXT,
            date TEXT
        );
        """))
        conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS questions (
            id SERIAL PRIMARY KEY,
            key TEXT,
            q TEXT,
            options TEXT,
            ans TEXT,
            exp TEXT
        );
        """))
        conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """))
        conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS referrals (
            id SERIAL PRIMARY KEY,
            referrer TEXT,
            referred TEXT,
            paid BOOLEAN DEFAULT FALSE,
            bonus_given BOOLEAN DEFAULT FALSE
        );
        """))
        conn.commit()

init_db()
def get_setting(key, default):
    with DBSession() as db:
        res = db.execute(sa.text("SELECT value FROM settings WHERE key=:k"), {"k": key}).scalar()
        return res if res else default

def set_setting(key, value):
    with DBSession() as db:
        db.execute(sa.text("INSERT INTO settings (key, value) VALUES (:k, :v) ON CONFLICT (key) DO UPDATE SET value=:v"), {"k": key, "v": value})
        db.commit()

ADMIN_PASS = get_setting("admin_pass", ADMIN_PASS)
ADS = json.loads(get_setting("ads", json.dumps([])))
NOTICES = json.loads(get_setting("notices", json.dumps([{"title":"Welcome","text":"Welcome to MOTIZ E-LEARNING!","created_at": str(datetime.now(NIGERIA_TZ))}])))
PINNED_NOTICE = get_setting("pinned_notice", "")

JSS_SUBJECTS = ["Mathematics", "English", "Social Studies", "Agriculture Science", "Basic Technology", "Basic Science", "National Value", "Civic Education", "Language/Linguistics", "History", "Physical & Health Education", "Cultural & Creative Art", "Security Education", "Home Economics", "Computer Studies"]

CLASSES = ["JSS1", "JSS2", "JSS3", "SS1", "SS2", "SS3"]
SUBJECTS = {
    "JSS1": JSS_SUBJECTS, "JSS2": JSS_SUBJECTS, "JSS3": JSS_SUBJECTS,
    "SS1_Science": ["Mathematics", "English", "Physics", "Chemistry", "Biology", "Further Maths"],
    "SS1_Commercial": ["Mathematics", "English", "Economics", "Commerce", "Financial Accounting", "Marketing", "Livestock Farming", "Civic Education", "Business Studies"],
    "SS1_Art": ["Mathematics", "English", "Literature", "Government", "History", "Economics", "Civic Education", "Christian Religious Studies", "Livestock Farming"],
    "SS2_Science": ["Mathematics", "English", "Physics", "Chemistry", "Biology", "Further Maths"],
    "SS2_Commercial": ["Mathematics", "English", "Economics", "Commerce", "Financial Accounting", "Marketing", "Livestock Farming", "Civic Education", "Business Studies"],
    "SS2_Art": ["Mathematics", "English", "Literature", "Government", "History", "Economics", "Civic Education", "Christian Religious Studies", "Livestock Farming"],
    "SS3_Science": ["Mathematics", "English", "Physics", "Chemistry", "Biology", "Further Maths"],
    "SS3_Commercial": ["Mathematics", "English", "Economics", "Commerce", "Financial Accounting", "Marketing", "Livestock Farming", "Civic Education", "Business Studies"],
    "SS3_Art": ["Mathematics", "English", "Literature", "Government", "History", "Economics", "Civic Education", "Christian Religious Studies", "Livestock Farming"]
}

PRACTICE_MAP = {"JSS1": "JSS3", "JSS2": "JSS3", "JSS3": "JSS3_BECE", "SS1": "SS3", "SS2": "SS3", "SS3": "SS3_WAEC"}

# AUTO SEED SAMPLE QUESTIONS IF EMPTY
def seed_questions():
    with DBSession() as db:
        count = db.execute(sa.text("SELECT COUNT(*) FROM questions")).scalar()
        if count == 0:
            sample = [
                ("JSS3_BECE_Mathematics", "BECE: 10 + 5 =?", json.dumps(["15","16","14","17"]), "15", "Addition"),
                ("SS3_WAEC_Science_Mathematics", "WAEC: If x + 3 = 10, find x", json.dumps(["7","8","9","10"]), "7", "x = 10-3")
            ]
            for key,q,opt,ans,exp in sample:
                db.execute(sa.text("INSERT INTO questions (key,q,options,ans,exp) VALUES (:k,:q,:o,:a,:e)"),
                           {"k":key,"q":q,"o":opt,"a":ans,"e":exp})
            db.commit()

seed_questions()

def get_user():
    nickname = session.get("nickname")
    if not nickname: return None, None
    with DBSession() as db:
        user = db.execute(sa.text("SELECT * FROM users WHERE nickname=:u"), {"u": nickname}).mappings().first()
        if user:
            user = dict(user)
            user['friends'] = json.loads(user.get('friends', '[]'))
        return nickname, user

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        nickname, user = get_user()
        if not user: return redirect("/login")
        delete_old_posts()
        delete_old_notices()
        return f(nickname, user, *args, **kwargs)
    return wrapper

def delete_old_posts():
    with DBSession() as db:
        cutoff = datetime.now(NIGERIA_TZ) - timedelta(hours=24)
        db.execute(sa.text("DELETE FROM posts WHERE created_at < :c"), {"c": cutoff})
        db.commit()

def delete_old_notices():
    global NOTICES
    cutoff = datetime.now(NIGERIA_TZ) - timedelta(hours=24)
    new_notices = []
    for n in NOTICES:
        try:
            if datetime.fromisoformat(n.get('created_at')) > cutoff:
                new_notices.append(n)
        except: new_notices.append(n)
    if len(new_notices)!= len(NOTICES):
        NOTICES = new_notices
        set_setting("notices", json.dumps(NOTICES))

BASE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title><style>:root{--bg:#f0f2f5;--card:white;--text:#333} body.dark{--bg:#121212;--card:#1e1e1e;--text:#eee}
body{font-family:Segoe UI;background:var(--bg);color:var(--text);margin:0;padding:0;padding-bottom:80px}
.header{background:#0f3460;color:white;padding:10px;text-align:center;position:fixed;top:0;width:100%;z-index:1000;display:flex;justify-content:space-between;align-items:center}
.header h1{margin:0;font-size:0.85rem;flex:1;text-align:center;line-height:1.1;white-space:nowrap}
.theme-btn{border:none;background:transparent;color:white;font-size:1.3rem;cursor:pointer;margin-left:10px}
.exit-btn{background:#e94560;color:white;border:none;padding:5px 10px;border-radius:5px;text-decoration:none;font-size:0.8rem;margin-right:10px}
.nav{display:flex;gap:5px;background:#16213e;padding:5px;flex-wrap:wrap;position:fixed;top:50px;width:100%;overflow-x:auto;z-index:999}
.nav a{color:white;text-decoration:none;padding:5px 8px;border-radius:10px;border:1px solid #fff3;font-size:0.8rem}
.container{padding:10px;padding-top:105px}
.card{background:var(--card);padding:12px;margin:8px 0;border-radius:10px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}
.btn{background:#28a745;color:white;padding:12px 15px;text-decoration:none;border-radius:8px;display:block;margin:8px 0;text-align:center;font-weight:bold;border:none;width:100%;cursor:pointer}
.btn.red{background:#e94560}.btn.blue{background:#2196f3}.btn.orange{background:#ff9800}.btn.gray{background:#6c757d;font-size:0.9rem;padding:8px}
input,select,textarea{width:100%;padding:10px;margin:5px 0;border-radius:5px;border:1px solid #ccc;box-sizing:border-box;font-size:1rem;background:var(--card);color:var(--text)}
.correct{background:#d4edda;border-left:5px solid #28a745}.wrong{background:#f8d7da;border-left:5px solid #e94560}
.timer{background:#e94560;color:white;padding:12px;text-align:center;border-radius:8px;font-weight:bold;font-size:1.3rem;position:sticky;top:105px;z-index:999}
.copy-btn{background:#2196f3;color:white;border:none;padding:8px;border-radius:5px;cursor:pointer;margin-left:10px}
.comment-box{margin-top:10px;padding-top:10px;border-top:1px dashed #ccc}
.comment{font-size:0.9rem;background:#f0f2f5;padding:6px;border-radius:5px;margin:4px 0}
.like-btn{background:transparent;border:none;color:#e94560;cursor:pointer;font-weight:bold;margin-right:10px}
.success{color:green;background:#d4edda;padding:10px;border-radius:5px}.error{color:red;background:#f8d7da;padding:10px;border-radius:5px}
.emoji-box{display:none;margin:8px 0;padding:10px;background:var(--bg);border-radius:8px}
.emoji-tab{display:flex;gap:5px;overflow-x:auto;margin-bottom:8px}
.emoji-tab button{border:none;background:#ddd;padding:5px 8px;border-radius:15px;cursor:pointer}
.emoji-tab button.active{background:#2196f3;color:white}
.emoji-btn{font-size:1.5rem;border:none;background:transparent;cursor:pointer;margin:3px}
.chat-box{height:400px;overflow-y:auto;background:var(--bg);padding:10px;border-radius:8px;margin-bottom:10px}
.chat-msg{margin:5px 0;padding:8px;background:var(--card);border-radius:8px}
.badge{background:#28a745;color:white;padding:2px 6px;border-radius:10px;font-size:0.7rem;margin-left:5px}
.notice-title{font-size:1.1rem;font-weight:bold;color:#0f3460;margin-bottom:5px}
.collapsible{cursor:pointer}
.collapsed-content{display:none}
.book{position:absolute;font-size:2.5rem;animation:bounce 2s infinite ease-in-out}
@keyframes bounce{0%,100%{transform:translateY(0)}50%{transform:translateY(-30px)}}
@keyframes glow{from{text-shadow:0 0 10px #fff}to{text-shadow:0 0 30px #2196f3}}
</style></head><body>{{header}}<div class="container">{{content}}</div><script>{{timer_script}}</script></body></html>"""

def get_header(nickname,user, show_exit=True):
    if not user: return ""
    exit_html = '<a href="/main" class="exit-btn">Exit</a>' if show_exit else ""
    verified = '<span class=badge>✓ Verified</span>' if user.get('is_verified') else ""
    return f"""<div class="header"><button class="theme-btn" onclick="document.body.classList.toggle('dark')">🌙</button><h1>MOTIZ E-LEARNING INSTITUTION {verified}</h1>{exit_html}</div><div class="nav"><a href="/main">🏠 Home</a><a href="/exam">✍️ CBT</a><a href="/lessons">🎓 Lessons</a><a href="/community">🌍 Community</a><a href="/groups">👥 Groups</a><a href="/dm">💬 DM</a><a href="/friends">👤 Friends</a><a href="/profile">📊 Profile</a><a href="/admin">🔒 Admin</a><a href="/logout">🚪 Logout</a></div>"""

@app.route('/')
def splash():
    return render_template_string("""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Welcome</title><meta http-equiv="refresh" content="10;url=/login">
<style>body{margin:0;background:linear-gradient(135deg,#0f3460,#16213e);color:white;font-family:Segoe UI;display:flex;justify-content:center;align-items:center;height:100vh;flex-direction:column;text-align:center;overflow:hidden}
.logo{font-size:2.8rem;font-weight:bold;animation:glow 2s ease-in-out infinite alternate;line-height:1.2;z-index:10}
.subtext{font-size:1.1rem;margin-top:10px;opacity:0.9;z-index:10}
.loader{border:4px solid #fff3;border-top:4px solid white;border-radius:50%;width:40px;height:40px;animation:spin 1s linear infinite;margin-top:20px;z-index:10}
@keyframes spin{0%{transform:rotate(0)}100%{transform:rotate(360deg)}}
@keyframes glow{from{text-shadow:0 0 10px #fff}to{text-shadow:0 0 30px #2196f3}}
.book{position:absolute;font-size:2.5rem;animation:bounce 2s infinite ease-in-out;z-index:1}
@keyframes bounce{0%,100%{transform:translateY(0)}50%{transform:translateY(-30px)}}
.b1{top:10%;left:15%;animation-delay:0s}.b2{top:20%;right:20%;animation-delay:0.5s}.b3{bottom:25%;left:10%;animation-delay:1s}
</style></head><body>
<div class="book b1">📖</div><div class="book b2">📓</div><div class="book b3">📒</div>
<div class="logo">MOTIZ E-LEARNING INSTITUTION</div><div class="subtext">Learn. Practice. Excel.</div><div class="loader"></div></body></html>""")

@app.route('/main')
@login_required
def main(nickname, user):
    pinned_html = ""
    if PINNED_NOTICE:
        try:
            pin = json.loads(PINNED_NOTICE)
            if isinstance(pin, dict):
                pinned_html = f"<div class='card' style='border:2px solid gold'><div class=notice-title>📌 {pin['title']}</div>{pin['text']}</div>"
        except: pinned_html = f"<div class='card' style='border:2px solid gold'><b>📌 PINNED:</b> {PINNED_NOTICE}</div>"
    notices_html = ""
    for n in NOTICES:
        try: notices_html += f"<div class='card'><div class=notice-title>📢 {n['title']}</div>{n['text']}</div>"
        except: notices_html += f"<div class='card'><b>📢 ADMIN:</b> {n}</div>"
    return render_template_string(BASE, title="Home", header=Markup(get_header(nickname,user, show_exit=False)), content=Markup(f"<div class='card'><h2>Welcome {user['name']}</h2><p><b>Class:</b> {user['class']} {user.get('dept','')}</p></div>{pinned_html}<h3>General Notice</h3>{notices_html}<a class=btn href=/exam>Start CBT Exam</a>"), timer_script="")

@app.route('/register', methods=["GET","POST"])
def register():
    if get_user()[1]: return redirect("/main")
    error = ""; success = ""
    ref = request.args.get('ref')
    if request.method == "POST":
        nickname = request.form.get("nickname","").strip().lower()
        with DBSession() as db:
            exists = db.execute(sa.text("SELECT nickname FROM users WHERE nickname=:u"), {"u": nickname}).scalar()
            if exists: error = "<div class=error>Nickname taken</div>"
            else:
                name = f"{request.form['surname']} {request.form['other']}"
                db.execute(sa.text("INSERT INTO users (nickname,name,password,class,dept,referred_by) VALUES (:u,:n,:p,:c,:d,:r)"),
                           {"u": nickname, "n": name, "p": request.form['password'], "c": request.form['class'], "d": request.form.get('dept',''), "r": ref})
                if ref: db.execute(sa.text("INSERT INTO referrals (referrer, referred) VALUES (:r, :ref)"), {"r": ref, "ref": nickname})
                db.commit()
                success = f"<div class=success>Registration Successful!<br>You can now login</div>"
                session["nickname"] = nickname; return redirect("/main")
    js = """<script>function d(){let c=document.getElementById('class').value;let x=document.getElementById('dept');x.innerHTML='';if(['SS1','SS2','SS3'].includes(c)){x.innerHTML='<label>Department *</label><select name=dept required><option value="">Select</option><option>Science</option><option>Commercial</option><option>Art</option></select>'}}</script>"""
    form = f"<div class='card'><h2>Register</h2>{error}{success}<form method=POST><input name=nickname placeholder='Nickname' required><input name=surname placeholder='Surname' required><input name=other placeholder='Other Name' required><input type=password name=password placeholder='Password' required><select name=class id=class onchange=d() required><option value=''>Select Class</option>{''.join([f'<option>{c}</option>' for c in CLASSES])}</select><div id=dept></div><button class=btn>Register</button><p>Already have account? <a href=/login>Login</a></p></form></div>{js}"
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
@app.route('/exam')
@login_required
def exam(nickname, user):
    key = f"{user['class']}_{user['dept']}" if user['dept'] else user['class']
    subs = SUBJECTS.get(key, [])
    if not subs: return render_template_string(BASE, title="Error", header=Markup(get_header(nickname,user)), content=Markup("<div class=error>No subjects for your class yet</div>"), timer_script="")
    sub_btns = "".join([f"<a class='btn blue' href=/start/{urllib.parse.quote(key)}/{urllib.parse.quote(s)}>📚 {s}</a>" for s in subs])
    return render_template_string(BASE, title="CBT", header=Markup(get_header(nickname,user)), content=Markup(f"<div class='card'><h2>Select Subject - {user['class']}</h2>{sub_btns}</div>"), timer_script="")

@app.route('/start/<path:key>/<path:sub>', methods=["GET","POST"])
@login_required
def start(nickname, user, key, sub):
    key = urllib.parse.unquote(key); sub = urllib.parse.unquote(sub)
    limit = FREE_Q if user['q_cycle']=="free" else PAID_Q
    if user['q_used'] >= limit and user['q_cycle']=="free": return redirect("/request-payment/questions")
    with DBSession() as db: q_list = db.execute(sa.text("SELECT * FROM questions WHERE key=:k"), {"k": f"{key}_{sub}"}).mappings().all()

    if len(q_list) == 0:
        return render_template_string(BASE, title="Error", header=Markup(get_header(nickname,user)), content=Markup(f"<div class=error>No questions for {sub} yet. Contact Admin</div>"), timer_script="")

    session_key = f"exam_{key}_{sub}"
    answers_key = f"answers_{key}_{sub}"
    if request.method == "GET":
        questions = list(q_list); random.shuffle(questions)
        session[session_key] = questions[:limit]
        session[answers_key] = {}
        session['q_index'] = 0

    questions = session.get(session_key, [])
    answers = session.get(answers_key, {})
    q_index = session.get('q_index', 0)

    if request.method == "POST":
        if "save_answer" in request.form:
            session[answers_key][str(q_index)] = request.form.get("answer")
            session.modified = True
        if "next" in request.form: session['q_index'] = q_index + 1
        if "prev" in request.form: session['q_index'] = q_index - 1
        if "submit_exam" in request.form: return redirect("/result")
        return redirect(f"/start/{urllib.parse.quote(key)}/{urllib.parse.quote(sub)}")

    if q_index >= len(questions): return redirect("/result")
    q = questions[q_index]; q['options'] = json.loads(q['options'])
    saved_ans = answers.get(str(q_index))

    timer_js = f"""let timeLeft = {TIMER_PER_QUESTION}; const timerEl = document.createElement('div'); timerEl.className = 'timer'; document.querySelector('.container').prepend(timerEl); function updateTimer(){{let m = Math.floor(timeLeft / 60); let s = timeLeft % 60; s = s < 10? '0' + s : s; timerEl.innerHTML = `⏰ TIME LEFT: ${{m}}:${{s}}`; if(timeLeft <= 30){{timerEl.style.background = '#ffc107';timerEl.style.color = 'black';}} if(timeLeft <= 0){{document.getElementById('exam_form').submit();}} timeLeft--;}} updateTimer(); setInterval(updateTimer, 1000);"""

    options_html = "".join([f"<label style='display:block;padding:10px;margin:8px 0;background:var(--bg);border-radius:8px'><input type=radio name=answer value='{opt}' {'checked' if saved_ans==opt else ''} required> {opt}</label>" for opt in q['options']])
    prev_btn = f"<button name=prev class='btn gray' {'disabled' if q_index==0 else ''}>⬅️ Prev</button>" if q_index > 0 else ""
    next_btn = f"<button name=next class='btn blue'>Next ➡️</button>" if q_index < len(questions)-1 else f"<button name=submit_exam class='btn orange'>Submit Exam</button>"

    content = f"<div class='card'><h2>{sub}</h2><h3>Question {q_index+1} of {len(questions)}</h3><p><b>{q['q']}</b></p><form method=POST id=exam_form>{options_html}<input type=hidden name=save_answer value=1><div style='display:flex;gap:10px'>{prev_btn}{next_btn}</div></form></div>"
    return render_template_string(BASE, title=sub, header=Markup(get_header(nickname,user)), content=Markup(content), timer_script=Markup(timer_js))

@app.route('/result')
@login_required
def result(nickname, user):
    session_key = [k for k in session.keys() if k.startswith('exam_')][0]
    answers_key = [k for k in session.keys() if k.startswith('answers_')][0]
    questions = session.get(session_key, [])
    answers = session.get(answers_key, {})

    correct = 0
    result_html = ""
    for i, q in enumerate(questions):
        q['options'] = json.loads(q['options'])
        user_ans = answers.get(str(i))
        if user_ans == q['ans']: correct += 1
        status = "correct" if user_ans == q['ans'] else "wrong"
        result_html += f"<div class='card {status}'><h4>Q{i+1}: {q['q']}</h4><p><b>Your Answer:</b> {user_ans or 'Not Answered'}</p><p><b>Correct Answer:</b> {q['ans']}</p><p><b>Explanation:</b> {q['exp']}</p></div>"

    total = len(questions)
    wrong = total - correct # FIXED: NOW COUNTING WRONG
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET q_used=q_used+:t, correct=correct+:c, wrong=wrong+:w WHERE nickname=:u"), {"t": total, "c": correct, "w": wrong, "u": nickname})
        db.commit()

    percent = round((correct/total)*100, 1) if total>0 else 0
    grade = "A" if percent>=70 else "B" if percent>=60 else "C" if percent>=50 else "F"
    session.pop(session_key, None); session.pop(answers_key, None)

    return render_template_string(BASE, title="Result", header=Markup(get_header(nickname,user)), content=Markup(f"<div class='card'><h2>🎉 Your Result</h2><p><b>Score:</b> {correct}/{total}</p><p><b>Percentage:</b> {percent}%</p><p><b>Grade:</b> {grade}</p></div>{result_html}<a class=btn href=/exam>Start New Exam</a>"), timer_script="")

@app.route('/community', methods=["GET","POST"])
@login_required
def community(nickname, user):
    is_admin = session.get("admin_logged_in");
    with DBSession() as db:
        if request.method=="POST":
            if "new_post" in request.form:
                db.execute(sa.text("INSERT INTO posts (nickname, name, text, emoji, likes, comments) VALUES (:u, :n, :t, :e, '[]', '[]')"),
                           {"u": nickname, "n": user["name"], "t": request.form["post"], "e": request.form.get("emoji","")})
            elif "comment_post_id" in request.form:
                p = db.execute(sa.text("SELECT comments FROM posts WHERE id=:id"), {"id": request.form["comment_post_id"]}).scalar()
                comments = json.loads(p); comments.append({"user": user["name"], "text": request.form["comment_text"]})
                db.execute(sa.text("UPDATE posts SET comments=:c WHERE id=:id"), {"c": json.dumps(comments), "id": request.form["comment_post_id"]})
            elif "like_post_id" in request.form:
                p = db.execute(sa.text("SELECT likes FROM posts WHERE id=:id"), {"id": request.form["like_post_id"]}).scalar()
                likes = json.loads(p); likes.remove(nickname) if nickname in likes else likes.append(nickname)
                db.execute(sa.text("UPDATE posts SET likes=:l WHERE id=:id"), {"l": json.dumps(likes), "id": request.form["like_post_id"]})
            elif "delete_post_id" in request.form and is_admin:
                db.execute(sa.text("DELETE FROM posts WHERE id=:id"), {"id": request.form["delete_post_id"]})
            db.commit(); return redirect("/community")
        posts = db.execute(sa.text("SELECT * FROM posts ORDER BY id DESC")).mappings().all()

    # BUILD EMOJI - FIXED SPACE BUG
    tabs_html, boxes_html = "", ""
    first = True
    for name, emojis in EMOJI_GROUPS.items():
        active = "active" if first else ""
        display = "block" if first else "none"
        tabs_html += f'<button type="button" id="ctab_{name}" class="{active}" onclick="showEmojiGroupC(\'{name}\')">{name}</button>'
        emoji_spans = "".join([f'<span onclick="addEmojiC(\'{e}\')" class="emoji-btn">{e}</span>' for e in emojis.split()])
        boxes_html += f'<div id="cgroup_{name}" class="emoji-box" style="display:{display}">{emoji_spans}</div>'
        first = False

    emoji_html = f"""<div class="emoji-wrap"><button type="button" class="btn gray" onclick="toggleEmojiC()">😀 Add Emoji</button><div id="emoji_wrap_c" class="emoji-box-wrap" style="display:none"><div id="emoji_tab_c" class="emoji-tab">{tabs_html}</div>{boxes_html}</div></div>"""
    emoji_js = Markup("""<script>function toggleEmojiC(){let x=document.getElementById('emoji_wrap_c');x.style.display=x.style.display=='block'?'none':'block';}function showEmojiGroupC(id){document.querySelectorAll('#emoji_wrap_c.emoji-box').forEach(x=>x.style.display='none');document.querySelectorAll('#emoji_tab_c button').forEach(x=>x.classList.remove('active'));document.getElementById('cgroup_'+id).style.display='block';document.getElementById('ctab_'+id).classList.add('active');}function addEmojiC(e){let t=document.getElementById('post');t.value+=e;t.focus();}</script>""")

    posts_html = ""
    for p in posts:
        likes_count = len(json.loads(p['likes'])); comments_data = json.loads(p['comments'])
        comments_html = "".join([f'<div class=comment><b>{c["user"]}:</b> {c["text"]}</div>' for c in comments_data]) or '<p style=font-size:0.8rem>No comments</p>'
        delete_btn = f'<form method=POST style=display:inline><input type=hidden name=delete_post_id value={p["id"]}><button class=btn.red style=padding:5px;font-size:0.8rem;margin-left:10px>Delete</button></form>' if is_admin else ''
        posts_html += f"<div class=card><b>{p['name']}</b>: {p['text']} {p['emoji']}<div style=margin-top:8px><form method=POST style='display:inline'><input type=hidden name=like_post_id value={p['id']}><button class=like-btn>🩷 {likes_count}</button></form>{delete_btn}</div><div class=comment-box><b>Comments:</b>{comments_html}<form method=POST><input type=hidden name=comment_post_id value={p['id']}><input name=comment_text placeholder='Write comment...' required style=width:75%;display:inline-block><button class='btn gray' style=width:23%;display:inline-block>Send</button></form></div></div>"
    return render_template_string(BASE, title="Community", header=Markup(get_header(nickname,user)), content=Markup(f"<div class=card><h2>Community</h2><form method=POST><textarea name=post id=post placeholder='Whats on your mind?' required></textarea>{emoji_html}<button class=btn>Post</button><input type=hidden name=new_post value=1></form></div>{posts_html}"), timer_script=emoji_js)

@app.route('/request-payment/<t>')
@login_required
def req_pay(nickname, user, t):
    price = QUESTION_PRICE if t=="questions" else LESSON_PRICE
    with DBSession() as db: pending = db.execute(sa.text("SELECT * FROM payments WHERE nickname=:u AND type=:t AND status='Pending'"), {"u": nickname, "t": t}).scalar()
    if pending: return render_template_string(BASE, title="Payment", header=Markup(get_header(nickname,user)), content=Markup("<div class=card><h2>⏳ Request Pending</h2><p>Wait for admin to verify</p></div>"), timer_script="")

    copy_js = Markup(f"""<script>
    function copyAcc(){{
        let acc = '{PALMPAY_ACCOUNT}';
        navigator.clipboard.writeText(acc).then(()=>{{alert('Account number copied!')}}).catch(()=>{{
            let el = document.createElement('textarea');
            el.value = acc;
            document.body.appendChild(el);
            el.select();
            document.execCommand('copy');
            document.body.removeChild(el);
            alert('Account number copied!');
        }});
    }}
    </script>""")

    form = f'<div class=card><h2>Pay &#8358;{price} to unlock</h2><p><b>Bank:</b> {PALMPAY_BANK}<br><b>Account:</b> {PALMPAY_ACCOUNT} <button type=button class=copy-btn onclick=copyAcc()>Copy</button><br><b>Name:</b> {PALMPAY_NAME}</p><p style=color:orange;font-weight:bold>ADMIN WILL VERIFY WITHIN 24HRS</p><form method=POST action=/confirm/{t}><input name=bank_used placeholder="Bank you used to transfer e.g GTBank" required><input name=account_name placeholder="Account Name you used" required><button class=btn>I Have Paid</button></form></div>'
    return render_template_string(BASE, title="Payment", header=Markup(get_header(nickname,user)), content=Markup(form), timer_script=copy_js)

@app.route('/confirm/<t>', methods=["POST"])
@login_required
def confirm(nickname, user, t):
    with DBSession() as db:
        db.execute(sa.text("INSERT INTO payments (nickname, name, type, status, bank_used, account_name) VALUES (:u, :n, :t, 'Pending', :b, :a)"),
                   {"u": nickname, "n": user["name"], "t": t, "b": request.form["bank_used"], "a": request.form["account_name"]})
        db.commit()
    return render_template_string(BASE, title="Sent", header=Markup(get_header(nickname,user)), content=Markup("<div class='card'><h2>✅ Request Sent</h2><p>Admin will verify with your bank details</p><a class=btn href=/main>Home</a></div>"), timer_script="")

@app.route('/friends', methods=["GET","POST"])
@login_required
def friends(nickname, user):
    with DBSession() as db:
        if request.method=="POST":
            if "send_request" in request.form:
                f = request.form["send_request"]
                db.execute(sa.text("INSERT INTO friend_requests (from_nickname, to_nickname) VALUES (:f, :t)"), {"f": nickname, "t": f})
                db.commit()
            elif "accept_user" in request.form:
                from_user = request.form["accept_user"]
                user['friends'].append(from_user)
                db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(user['friends']), "u": nickname})
                from_friends = json.loads(db.execute(sa.text("SELECT friends FROM users WHERE nickname=:u"), {"u": from_user}).scalar() or '[]')
                from_friends.append(nickname)
                db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(from_friends), "u": from_user})
                db.execute(sa.text("DELETE FROM friend_requests WHERE from_nickname=:f AND to_nickname=:t"), {"f": from_user, "t": nickname})
                db.commit()
            elif "decline_user" in request.form:
                from_user = request.form["decline_user"]
                db.execute(sa.text("DELETE FROM friend_requests WHERE from_nickname=:f AND to_nickname=:t"), {"f": from_user, "t": nickname})
                db.commit()
        incoming = db.execute(sa.text("SELECT * FROM friend_requests WHERE to_nickname=:u AND status='Pending'"), {"u": nickname}).mappings().all()
        all_users = db.execute(sa.text("SELECT * FROM users WHERE nickname!=:u"), {"u": nickname}).mappings().all()
    incoming_html = "".join([f"<div class=card><b>{db.execute(sa.text('SELECT name FROM users WHERE nickname=:u'), {'u': r['from_nickname']}).scalar()}</b><div style='display:flex;gap:5px'><form method=POST><input type=hidden name=accept_user value={r['from_nickname']}><button class=btn>Accept</button></form><form method=POST><input type=hidden name=decline_user value={r['from_nickname']}><button class='btn red'>Decline</button></form></div></div>" for r in incoming])
    all_users_html = "".join([f"<div class=card><b>{u['name']}</b> @{u['nickname']}<form method=POST><input type=hidden name=send_request value={u['nickname']}><button class=btn.blue>Add Friend</button></form></div>" for u in all_users if u['nickname'] not in user['friends']])
    friends_html = "".join([f"<div class=card>👤 {db.execute(sa.text('SELECT name FROM users WHERE nickname=:u'), {'u': f}).scalar()}</div>" for f in user['friends']]) or "<p>No friends yet</p>"
    return render_template_string(BASE, title="Friends", header=Markup(get_header(nickname,user)), content=Markup(f"<div class=card><h2>Friend Requests</h2>{incoming_html or '<p>No requests</p>'}</div><div class=card><h2>My Friends</h2>{friends_html}</div><div class=card><h2>All Users</h2>{all_users_html}</div>"), timer_script="")

@app.route('/dm')
@login_required
def dm_list(nickname, user):
    with DBSession() as db:
        friends_html = "".join([f"<a class=btn.blue href=/dm/{f}>💬 Chat with {db.execute(sa.text('SELECT name FROM users WHERE nickname=:u'), {'u': f}).scalar()}</a>" for f in user['friends']])
    return render_template_string(BASE, title="Messages", header=Markup(get_header(nickname,user)), content=Markup(f"<div class=card><h2>My Friends</h2>{friends_html or '<p>Add friends to start chat</p>'}</div>"), timer_script="")

@app.route('/dm/<to_nickname>', methods=["GET","POST"])
@login_required
def dm_chat(nickname, user, to_nickname):
    if to_nickname not in user['friends']: return redirect("/dm")
    with DBSession() as db:
        if request.method=="POST":
            db.execute(sa.text("INSERT INTO dms (from_nickname, to_nickname, text, time) VALUES (:f, :t, :txt, :time)"),
                       {"f": nickname, "t": to_nickname, "txt": request.form["msg"], "time": datetime.now(NIGERIA_TZ).strftime("%H:%M")})
            db.commit(); return redirect(f"/dm/{to_nickname}")
        chat = db.execute(sa.text("SELECT * FROM dms WHERE (from_nickname=:u AND to_nickname=:t) OR (from_nickname=:t AND to_nickname=:u) ORDER BY id"),
                          {"u": nickname, "t": to_nickname}).mappings().all()
        to_name = db.execute(sa.text("SELECT name FROM users WHERE nickname=:u"), {"u": to_nickname}).scalar()

    # BUILD EMOJI - FIXED SPACE BUG
    tabs_html, boxes_html = "", ""
    first = True
    for name, emojis in EMOJI_GROUPS.items():
        active = "active" if first else ""
        display = "block" if first else "none"
        tabs_html += f'<button type="button" id="dtab_{name}" class="{active}" onclick="showEmojiDM(\'{name}\')">{name}</button>'
        emoji_spans = "".join([f'<span onclick="addEmojiD(\'{e}\')" class="emoji-btn">{e}</span>' for e in emojis.split()])
        boxes_html += f'<div id="dgroup_{name}" class="emoji-box" style="display:{display}">{emoji_spans}</div>'
        first = False
    emoji_html = f"""<button type=button class='btn gray' onclick=toggleEmojiD()>😀</button><div id=dm_emoji_wrap style=display:none><div id=dm_emoji_tab class=emoji-tab>{tabs_html}</div>{boxes_html}</div>"""
    emoji_js = Markup("""<script>function toggleEmojiD(){let x=document.getElementById('dm_emoji_wrap');x.style.display=x.style.display=='block'?'none':'block';}function showEmojiDM(id){document.querySelectorAll('#dm_emoji_wrap.emoji-box').forEach(x=>x.style.display='none');document.querySelectorAll('#dm_emoji_tab button').forEach(x=>x.classList.remove('active'));document.getElementById('dgroup_'+id).style.display='block';document.getElementById('dtab_'+id).classList.add('active');}function addEmojiD(e){let t=document.getElementById('msg');t.value+=e;t.focus();}</script>""")

    msgs = "".join([f"<div class=chat-msg><b>{db.execute(sa.text('SELECT name FROM users WHERE nickname=:u'), {'u': m['from_nickname']}).scalar()}:</b> {m['text']} <small>{m['time']}</small></div>" for m in chat])
    content = f"<div class=card><div class=chat-box>{msgs}</div><form method=POST><input id=msg name=msg placeholder='Type message...' required style=width:70%;display:inline-block><button class=btn.gray style=width:28%;display:inline-block>Send</button>{emoji_html}</form></div>"
    return render_template_string(BASE, title=f"Chat with {to_name}", header=Markup(get_header(nickname,user)), content=Markup(content), timer_script=emoji_js)
@app.route('/lessons')
@login_required
def lessons(nickname, user):
    try:
        expired = not user.get('lesson_expiry') or date.today() > datetime.strptime(user['lesson_expiry'], "%Y-%m-%d").date()
        if user.get('free_days', 0) > 0: expired = False
    except: expired = True
    if expired: return redirect("/request-payment/lessons")

    access_banner = f"<div class=success>✅ Access Active till {user['lesson_expiry']}</div>"

    with DBSession() as db:
        lessons = db.execute(sa.text("SELECT * FROM lessons WHERE class=:c AND dept=:d"), {"c": user['class'], "d": user.get('dept','')}).mappings().all()
    lessons_html = "".join([f"<div class=card><h3>📖 {l['subject']} - {l['title']}</h3><p>{l['notes']}</p><small>Posted: {l['date']}</small></div>" for l in lessons])
    if not lessons_html: lessons_html = "<p>No lessons for your class yet</p>"
    return render_template_string(BASE, title="Lessons", header=Markup(get_header(nickname,user)), content=Markup(f"<div class=card><h2>My Lessons</h2>{access_banner}<p>Free Days Left: {user.get('free_days', 0)}</p></div>{lessons_html}"), timer_script="")

@app.route('/groups', methods=["GET","POST"])
@login_required
def groups(nickname, user):
    with DBSession() as db:
        if request.method=="POST":
            if "create_group" in request.form:
                db.execute(sa.text("INSERT INTO groups (name, creator, members, messages) VALUES (:n, :c, :m, :msg)"),
                           {"n": request.form["group_name"], "c": nickname, "m": json.dumps([nickname]), "msg": json.dumps([])})
                db.commit()
            return redirect("/groups")
        my_groups = db.execute(sa.text("SELECT * FROM groups")).mappings().all()
    my_groups_html = "".join([f"<a class=btn.blue href=/group/{g['id']}>👥 {g['name']} ({len(json.loads(g['members']))} members)</a>" for g in my_groups if nickname in json.loads(g['members'])])
    create_form = f"<div class=card><h3>Create Group</h3><form method=POST><input name=group_name placeholder='Group Name' required><button name=create_group class=btn>Create</button></form></div>"
    content = f"{create_form}<div class=card><h3>My Groups</h3>{my_groups_html or '<p>No groups yet</p>'}</div>"
    return render_template_string(BASE, title="Groups", header=Markup(get_header(nickname,user)), content=Markup(content), timer_script="")

@app.route('/group/<int:gid>', methods=["GET","POST"])
@login_required
def group_chat(nickname, user, gid):
    with DBSession() as db:
        group = db.execute(sa.text("SELECT * FROM groups WHERE id=:id"), {"id": gid}).mappings().first()
        if not group or nickname not in json.loads(group['members']): return redirect("/groups")
        members = json.loads(group['members']); messages = json.loads(group['messages']); is_creator = group['creator']==nickname

        # BUILD EMOJI - FIXED SPACE BUG
        tabs_html, boxes_html = "", ""
        first = True
        for name, emojis in EMOJI_GROUPS.items():
            active = "active" if first else ""
            display = "block" if first else "none"
            tabs_html += f'<button type="button" id="gtab_{name}" class="{active}" onclick="showEmojiGroupG(\'{name}\')">{name}</button>'
            emoji_spans = "".join([f'<span onclick="addEmojiG(\'{e}\')" class="emoji-btn">{e}</span>' for e in emojis.split()])
            boxes_html += f'<div id="ggroup_{name}" class="emoji-box" style="display:{display}">{emoji_spans}</div>'
            first = False
        emoji_html = f"""<button type=button class='btn gray' onclick=toggleEmojiG()>😀</button><div id=emoji_wrap_g style=display:none><div id=emoji_tab_g class=emoji-tab>{tabs_html}</div>{boxes_html}</div>"""
        emoji_js = Markup("""<script>function toggleEmojiG(){let x=document.getElementById('emoji_wrap_g');x.style.display=x.style.display=='block'?'none':'block';}function showEmojiGroupG(id){document.querySelectorAll('#emoji_wrap_g.emoji-box').forEach(x=>x.style.display='none');document.querySelectorAll('#emoji_tab_g button').forEach(x=>x.classList.remove('active'));document.getElementById('ggroup_'+id).style.display='block';document.getElementById('gtab_'+id).classList.add('active');}function addEmojiG(e){let t=document.getElementById('msg');t.value+=e;t.focus();}</script>""")

        if request.method=="POST":
            if "send_msg" in request.form:
                messages.append({"user": user["name"], "text": request.form["msg"], "time": datetime.now(NIGERIA_TZ).strftime("%H:%M")})
                db.execute(sa.text("UPDATE groups SET messages=:m WHERE id=:id"), {"m": json.dumps(messages), "id": gid})
            elif "new_name" in request.form and is_creator:
                db.execute(sa.text("UPDATE groups SET name=:n WHERE id=:id"), {"n": request.form["new_name"], "id": gid})
            elif "remove_member" in request.form and is_creator:
                member = request.form["remove_member"]
                if member in members and member!= nickname: members.remove(member)
                db.execute(sa.text("UPDATE groups SET members=:m WHERE id=:id"), {"m": json.dumps(members), "id": gid})
            elif "add_member" in request.form and is_creator:
                member = request.form["add_member"]
                user_exists = db.execute(sa.text("SELECT nickname FROM users WHERE nickname=:u"), {"u": member}).scalar()
                if user_exists and member not in members: members.append(member)
                db.execute(sa.text("UPDATE groups SET members=:m WHERE id=:id"), {"m": json.dumps(members), "id": gid})
            db.commit(); return redirect(f"/group/{gid}")

    msgs = "".join([f"<div class=chat-msg><b>{m['user']}:</b> {m['text']} <small>{m['time']}</small></div>" for m in messages])
    with DBSession() as db:
        all_users = db.execute(sa.text("SELECT nickname,name FROM users WHERE nickname!=:u"), {"u": nickname}).mappings().all()
        friends_options = "".join([f"<option value={u['nickname']}>{u['name']}</option>" for u in all_users if u['nickname'] not in members])
        members_html = "".join([f"<li>{db.execute(sa.text('SELECT name FROM users WHERE nickname=:u'), {'u': m}).scalar()} {f'<form method=POST style=display:inline><input type=hidden name=remove_member value={m}><button class=btn.red style=padding:2px 5px;font-size:0.7rem>Remove</button></form>' if is_creator and m!=nickname else ''}</li>" for m in members])
    add_member_form = f"<form method=POST><select name=add_member required><option value=''>Add Member</option>{friends_options}</select><button class=btn.gray>Add</button></form>" if is_creator else "<p><i>Only group creator can add/remove members</i></p>"
    rename_form = f"<form method=POST><input name=new_name placeholder=New Group Name required><button name=rename class=btn.orange>Rename</button></form>" if is_creator else ""
    content = f"<div class=card><h2>{group['name']}</h2>{rename_form}{add_member_form}<h4>Members:</h4><ul>{members_html}</ul></div>"
    content += f"<div class=card><div class=chat-box>{msgs or '<p>No messages yet</p>'}</div><form method=POST><input id=msg name=msg placeholder='Type message...' required style=width:70%;display:inline-block><button name=send_msg class=btn.gray style=width:28%;display:inline-block>Send</button>{emoji_html}</form></div>"
    return render_template_string(BASE, title=group['name'], header=Markup(get_header(nickname,user)), content=Markup(content), timer_script=emoji_js)

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

    error = ""
    if request.method=="POST":
        with DBSession() as db:
            if "verify_id" in request.form:
                req = db.execute(sa.text("SELECT * FROM payments WHERE id=:id"), {"id": request.form["verify_id"]}).mappings().first()
                if req["type"] == "questions": db.execute(sa.text("UPDATE users SET q_cycle='paid' WHERE nickname=:u"), {"u": req["nickname"]})
                if req["type"] == "lessons": db.execute(sa.text("UPDATE users SET lesson_expiry=:d WHERE nickname=:u"), {"d": str(date.today() + timedelta(days=30)), "u": req["nickname"]})
                db.execute(sa.text("UPDATE payments SET status='Verified' WHERE id=:id"), {"id": request.form["verify_id"]})
                db.commit(); error = "<div class=success>Payment Verified & Saved</div>"
            if "deny_id" in request.form: db.execute(sa.text("UPDATE payments SET status='Denied' WHERE id=:id"), {"id": request.form["deny_id"]}); db.commit(); error = "<div class=error>Payment Denied</div>"
            if "change_pass" in request.form:
                if request.form["old_pass"]!= ADMIN_PASS: error = "<div class=error>Old password is wrong</div>"
                else: ADMIN_PASS = request.form["new_pass"]; set_setting("admin_pass", ADMIN_PASS); error = "<div class=success>Admin Password Changed & Saved</div>"
            if "add_lesson" in request.form: db.execute(sa.text("INSERT INTO lessons (class, dept, subject, title, notes, date) VALUES (:c, :d, :s, :t, :n, :date)"),{"c": request.form['lesson_class'], "d": request.form.get('lesson_dept',''), "s": request.form['lesson_subject'], "t": request.form['lesson_title'], "n": request.form['lesson_notes'], "date": str(date.today())}); db.commit(); error = "<div class=success>Lesson Note Posted & Saved</div>"
            if "add_question" in request.form:
                cls = request.form['admin_class']; dept = request.form.get('admin_dept',''); sub = request.form['admin_subject']; key = f"{cls}_{dept}_{sub}" if dept else f"{cls}_{sub}"
                db.execute(sa.text("INSERT INTO questions (key, q, options, ans, exp) VALUES (:k, :q, :o, :a, :e)"),{"k": key, "q": request.form["q"], "o": json.dumps([request.form["a"],request.form["b"],request.form["c"],request.form["d"]]), "a": request.form["ans"], "e": request.form["exp"]}); db.commit(); error = "<div class=success>Single Question Added & Saved</div>"
            if "bulk_upload" in request.form:
                cls = request.form['bulk_class']; dept = request.form.get('bulk_dept',''); sub = request.form['bulk_subject']; key = f"{cls}_{dept}_{sub}" if dept else f"{cls}_{sub}"; lines = request.form["bulk_text"].strip().split('\n'); count = 0
                for line in lines:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 7: db.execute(sa.text("INSERT INTO questions (key, q, options, ans, exp) VALUES (:k, :q, :o, :a, :e)"),{"k": key, "q": parts[0], "o": json.dumps([parts[1],parts[2],parts[3],parts[4]]), "a": parts[5], "e": parts[6]}); count += 1
                db.commit(); error = f"<div class=success>{count} Questions Added & Saved</div>"
            if "new_notice" in request.form:
                notice = {"title": request.form["notice_title"], "text": request.form["new_notice"], "created_at": str(datetime.now(NIGERIA_TZ))}
                notices = NOTICES + [notice]
                NOTICES = notices; set_setting("notices", json.dumps(notices)); set_setting("ads", json.dumps(notices)); error = "<div class=success>Notice/Ad Posted to Home</div>"
            if "delete_notice_id" in request.form:
                del_id = int(request.form["delete_notice_id"])
                NOTICES.pop(del_id)
                set_setting("notices", json.dumps(NOTICES)); set_setting("ads", json.dumps(NOTICES)); error = "<div class=success>Notice Deleted</div>"
            if "edit_notice_id" in request.form:
                edit_id = int(request.form["edit_notice_id"])
                NOTICES[edit_id] = {"title": request.form["edit_title"], "text": request.form["edit_text"], "created_at": NOTICES[edit_id]['created_at']}
                set_setting("notices", json.dumps(NOTICES)); set_setting("ads", json.dumps(NOTICES)); error = "<div class=success>Notice Updated</div>"

    js = Markup(f"""<script>
const subjects = {json.dumps(SUBJECTS)};
function updateDept(id){{
    let c = document.getElementById(id+'_class').value;
    let dDiv = document.getElementById(id+'_dept_div');
    dDiv.innerHTML = '';
    if(['SS1','SS2','SS3'].includes(c)){{
        dDiv.innerHTML = '<label>Department</label><select name='+id+'_dept id='+id+'_dept onchange=updateSub("'+id+'") required><option value="">Select Dept</option><option>Science</option><option>Commercial</option><option>Art</option></select>';
    }} else {{
        updateSub(id);
    }}
}}
function updateSub(id){{
    let c = document.getElementById(id+'_class').value;
    let dEl = document.getElementById(id+'_dept');
    let d = dEl? dEl.value : '';
    let key = d? c+'_'+d : c;
    let s = document.getElementById(id+'_subject');
    s.innerHTML = '<option value="">Select Subject</option>';
    (subjects[key] || []).forEach(sub => s.innerHTML += '<option>'+sub+'</option>');
}}
function toggleHistory(){{let x=document.getElementById('history_box');x.style.display=x.style.display=='block'?'none':'block'}}
window.onload=function(){{updateSub('lesson');updateSub('admin');updateSub('bulk');}}
</script>""")

    with DBSession() as db:
        pending_reqs = db.execute(sa.text("SELECT * FROM payments WHERE status='Pending'")).mappings().all()
        history_reqs = db.execute(sa.text("SELECT * FROM payments WHERE status!='Pending' ORDER BY id DESC LIMIT 50")).mappings().all()

    pending_html = "".join([f"<div class='card'><b>{r['name']}</b> for {r['type']}<br><small>Bank: {r.get('bank_used','N/A')} | Acc Name: {r.get('account_name','N/A')}</small><div style='display:flex;gap:5px'><form method=POST style='flex:1'><input type=hidden name=verify_id value={r['id']}><button class=btn>Verify</button></form><form method=POST style='flex:1'><input type=hidden name=deny_id value={r['id']}><button class='btn red'>Deny</button></form></div></div>" for r in pending_reqs])
    history_html = "".join([f"<div class='card' style='opacity:0.7'><b>{r['name']}</b> - {r['status']} for {r['type']}</div>" for r in history_reqs])

    notices_admin_html = ""
    for i,n in enumerate(NOTICES):
        notices_admin_html += f"<div class='card'><form method=POST><input name=edit_title value='{n['title']}' required><textarea name=edit_text required>{n['text']}</textarea><input type=hidden name=edit_notice_id value={i}><button class='btn blue' style=width:48%;display:inline-block>Update</button></form><form method=POST style='display:inline'><input type=hidden name=delete_notice_id value={i}><button class='btn red' style=width:48%;display:inline-block>Delete</button></form></div>"

    form = f'\
<div class="card"><h2>Admin Panel</h2>{error}</div>\
<div class="card"><h2>Pending Payments</h2>{pending_html or "<p>No pending payments</p>"}</div>\
<button type="button" class="btn gray collapsible" onclick="toggleHistory()"> View Verified/Denied History</button>\
<div id="history_box" class="collapsed-content"><div class="card"><h3>Payment History</h3>{history_html or "<p>No history</p>"}</div></div>\
<div class="card"><h2>Manage Notices - Auto delete after 24hrs</h2>{notices_admin_html or "<p>No notices</p>"}</div>\
<div class="card"><h2>Change Admin Password</h2><form method="POST"><input type="password" name="old_pass" placeholder="Current Password" required><input type="password" name="new_pass" placeholder="New Password" required><button name="change_pass" class="btn orange">Change Password</button></form></div>\
<div class="card"><h2> Upload Lesson Note</h2><form method="POST">\
<label>Select Class</label><select name="lesson_class" id="lesson_class" onchange="updateDept(\'lesson\')" required><option value="">Select Class</option>{"".join([f"<option>{c}</option>" for c in CLASSES])}</select>\
<div id="lesson_dept_div"></div>\
<label>Select Subject</label><select name="lesson_subject" id="lesson_subject" required><option value="">Select Subject</option></select>\
<input name="lesson_title" placeholder="Lesson Title e.g Algebra Basics" required>\
<textarea name="lesson_notes" rows="8" placeholder="Paste lesson notes here..." required></textarea>\
<button name="add_lesson" class="btn blue">Post Lesson</button></form></div>\
<div class="card"><h2>Post General Notice / Ad</h2><form method="POST">\
<input name="notice_title" placeholder="Notice Heading - Big Title" required>\
<textarea name="new_notice" placeholder="Notice details / subheading" required></textarea>\
<button class="btn orange">Post Notice</button></form></div>\
<div class="card"><h2>Add Single Question</h2><form method="POST">\
<label>Select Class</label><select name="admin_class" id="admin_class" onchange="updateDept(\'admin\')" required><option value="">Select Class</option>{"".join([f"<option>{c}</option>" for c in CLASSES])}</select>\
<div id="admin_dept_div"></div>\
<label>Select Subject</label><select name="admin_subject" id="admin_subject" required><option value="">Select Subject</option></select>\
<textarea name="q" placeholder="Question" required></textarea>\
<input name="a" placeholder="Option A" required><input name="b" placeholder="Option B" required><input name="c" placeholder="Option C" required><input name="d" placeholder="Option D" required>\
<input name="ans" placeholder="Correct Answer" required><input name="exp" placeholder="Explanation" required>\
<button name="add_question" class="btn">Post Question</button></form></div>\
<div class="card"><h2>Bulk Upload Questions</h2><p><b>Format per line:</b> Question|A|B|C|D|CorrectAnswer|Explanation</p><form method="POST">\
<label>Select Class</label><select name="bulk_class" id="bulk_class" onchange="updateDept(\'bulk\')" required><option value="">Select Class</option>{"".join([f"<option>{c}</option>" for c in CLASSES])}</select>\
<div id="bulk_dept_div"></div>\
<label>Select Subject</label><select name="bulk_subject" id="bulk_subject" required><option value="">Select Subject</option></select>\
<textarea name="bulk_text" rows="10" placeholder="What is 2+2?|3|4|5|6|4|Simple addition\nCapital of Nigeria?|Lagos|Abuja|Kano|PH|Abuja|FCT" required></textarea>\
<button name="bulk_upload" class="btn blue">Upload Bulk Questions</button></form></div>'
    return render_template_string(BASE, title="Admin", header=Markup(get_header(nickname,user, show_exit=True)), content=Markup(form), timer_script=js)

@app.route('/profile')
@login_required
def profile(nickname, user):
    content = f"<div class=card><h2>My Profile</h2><p><b>Name:</b> {user['name']}</p><p><b>Nickname:</b> @{user['nickname']}</p><p><b>Class:</b> {user['class']} {user.get('dept','')}</p><p><b>Correct:</b> {user['correct']}</p><p><b>Wrong:</b> {user['wrong']}</p><p><b>Q Used:</b> {user['q_used']}</p><p><b>Lesson Expiry:</b> {user['lesson_expiry']}</p></div>"
    return render_template_string(BASE, title="Profile", header=Markup(get_header(nickname,user)), content=Markup(content), timer_script="")

@app.route('/logout')
def logout():
    session.clear()
    return redirect("/login")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
