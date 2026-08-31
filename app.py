from flask import Flask, render_template_string, request, redirect, session
from markupsafe import Markup
from datetime import date, datetime, timedelta
import random, json, os, urllib.parse
from functools import wraps
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import pytz # FOR NIGERIA TIME

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', "motiz_secret_key_2026_v9_2")

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
ADMIN_PASS = os.environ.get('ADMIN_PASS', "24434") # NOW SECURE
FREE_Q = 30
PAID_Q = 70

NIGERIA_TZ = pytz.timezone('Africa/Lagos')

def generate_admission_no():
    return str(random.randint(1000, 9999))

# ====== CREATE TABLES ======
def init_db():
    with engine.connect() as conn:
        conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            nickname TEXT UNIQUE,
            admission_no TEXT UNIQUE,
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
            date_paid TEXT,
            amount_paid TEXT
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
NOTICES = json.loads(get_setting("notices", json.dumps(["Welcome to MOTIZ E-LEARNING!"])))
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
        return f(nickname, user, *args, **kwargs)
    return wrapper

def delete_old_posts():
    with DBSession() as db:
        cutoff = datetime.now(NIGERIA_TZ) - timedelta(hours=24)
        db.execute(sa.text("DELETE FROM posts WHERE created_at < :c"), {"c": cutoff})
        db.commit()

BASE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title><style>:root{--bg:#f0f2f5;--card:white;--text:#333} body.dark{--bg:#121212;--card:#1e1e1e;--text:#eee}
body{font-family:Segoe UI;background:var(--bg);color:var(--text);margin:0;padding:0;padding-bottom:80px}
.header{background:#0f3460;color:white;padding:10px;text-align:center;position:fixed;top:0;width:100%;z-index:1000;display:flex;justify-content:space-between;align-items:center}
.header h1{margin:0;font-size:0.9rem;flex:1;text-align:center;white-space:nowrap}
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
.like-btn{background:transparent;border:none;color:#2196f3;cursor:pointer;font-weight:bold;margin-right:10px}
.success{color:green;background:#d4edda;padding:10px;border-radius:5px}.error{color:red;background:#f8d7da;padding:10px;border-radius:5px}
.emoji-box{display:none;margin:8px 0;padding:10px;background:var(--bg);border-radius:8px}
.emoji-btn{font-size:1.5rem;border:none;background:transparent;cursor:pointer;margin:3px}
.chat-box{height:400px;overflow-y:auto;background:var(--bg);padding:10px;border-radius:8px;margin-bottom:10px}
.chat-msg{margin:5px 0;padding:8px;background:var(--card);border-radius:8px}
.badge{background:#28a745;color:white;padding:2px 6px;border-radius:10px;font-size:0.7rem;margin-left:5px}
</style></head><body>{{header}}<div class="container">{{content}}</div><script>{{timer_script}}</script></body></html>"""

def get_header(nickname,user, show_exit=True):
    if not user: return ""
    exit_html = '<a href="/main" class="exit-btn">Exit</a>' if show_exit else ""
    verified = '<span class=badge>✓ Verified</span>' if user.get('is_verified') else ""
    return f"""<div class="header"><button class="theme-btn" onclick="document.body.classList.toggle('dark')">🌙</button><h1>MOTIZ E-LEARNING INSTITUTION {verified}</h1>{exit_html}</div><div class="nav"><a href="/main">🏠 Home</a><a href="/exam">✍️ CBT</a><a href="/lessons">🎓 Lessons</a><a href="/community">🌍 Community</a><a href="/groups">👥 Groups</a><a href="/dm">💬 DM</a><a href="/friends">👤 Friends</a><a href="/profile">📊 Profile</a><a href="/admin">🔒 Admin</a><a href="/logout">🚪 Logout</a></div>"""

@app.route('/')
def splash():
    return render_template_string("""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Welcome</title><meta http-equiv="refresh" content="3;url=/login"><style>body{margin:0;background:linear-gradient(135deg,#0f3460,#16213e);color:white;font-family:Segoe UI;display:flex;justify-content:center;align-items:center;height:100vh;flex-direction:column;text-align:center}.logo{font-size:2.8rem;font-weight:bold;animation:glow 2s ease-in-out infinite alternate;white-space:nowrap}@keyframes glow{from{text-shadow:0 0 10px #fff}to{text-shadow:0 0 30px #2196f3}}.loader{border:4px solid #fff3;border-top:4px solid white;border-radius:50%;width:40px;height:40px;animation:spin 1s linear infinite;margin-top:20px}@keyframes spin{0%{transform:rotate(0)}100%{transform:rotate(360deg)}}</style></head><body><div class="logo">MOTIZ E-LEARNING INSTITUTION</div><div>Learn. Practice. Excel.</div><div class="loader"></div></body></html>""")

@app.route('/main')
@login_required
def main(nickname, user):
    pinned_html = f"<div class='card' style='border:2px solid gold'><b>📌 PINNED:</b> {PINNED_NOTICE}</div>" if PINNED_NOTICE else ""
    notices_html = "".join([f"<div class='card'><b>📢 ADMIN:</b> {n}</div>" for n in NOTICES])
    return render_template_string(BASE, title="Home", header=Markup(get_header(nickname,user, show_exit=False)), content=Markup(f"<div class='card'><h2>Welcome {user['name']}</h2><p><b>Class:</b> {user['class']} {user.get('dept','')}</p><p><b>Admission No:</b> {user['admission_no']}</p></div>{pinned_html}<h3>General Notice</h3>{notices_html}<a class=btn href=/exam>Start CBT Exam</a>"), timer_script="")
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
                # Generate unique 4 digit admission number
                admission_no = generate_admission_no()
                while db.execute(sa.text("SELECT admission_no FROM users WHERE admission_no=:a"), {"a": admission_no}).scalar():
                    admission_no = generate_admission_no()

                name = f"{request.form['surname']} {request.form['other']}"
                db.execute(sa.text("INSERT INTO users (nickname,admission_no,name,password,class,dept,referred_by) VALUES (:u,:a,:n,:p,:c,:d,:r)"),
                           {"u": nickname, "a": admission_no, "n": name, "p": request.form['password'], "c": request.form['class'], "d": request.form.get('dept',''), "r": ref})
                if ref: db.execute(sa.text("INSERT INTO referrals (referrer, referred) VALUES (:r, :ref)"), {"r": ref, "ref": nickname})
                db.commit()
                success = f"<div class=success>Registration Successful!<br><b>Your Admission No: {admission_no}</b><br>Save it! You need it to login.</div>"
                session["nickname"] = nickname;
                return redirect("/main")
    js = """<script>function d(){let c=document.getElementById('class').value;let x=document.getElementById('dept');x.innerHTML='';if(['SS1','SS2','SS3'].includes(c)){x.innerHTML='<label>Department *</label><select name=dept required><option value="">Select</option><option>Science</option><option>Commercial</option><option>Art</option></select>'}}</script>"""
    form = f"<div class='card'><h2>Register</h2>{error}{success}<form method=POST><input name=nickname placeholder='Nickname' required><input name=surname placeholder='Surname' required><input name=other placeholder='Other Name' required><input type=password name=password placeholder='Password' required><select name=class id=class onchange=d() required><option value=''>Select Class</option>{''.join([f'<option>{c}</option>' for c in CLASSES])}</select><div id=dept></div><button class=btn>Register</button><p>Already have account? <a href=/login>Login</a></p></form></div>{js}"
    return render_template_string(BASE, title="Register", header="", content=Markup(form), timer_script="")

@app.route('/login', methods=["GET","POST"])
def login():
    if get_user()[1]: return redirect("/main")
    error = ""
    if request.method == "POST":
        nickname = request.form["nickname"].strip().lower()
        admission_no = request.form["admission_no"].strip()
        pwd = request.form["password"]
        with DBSession() as db:
            u = db.execute(sa.text("SELECT * FROM users WHERE nickname=:u AND admission_no=:a"), {"u": nickname, "a": admission_no}).mappings().first()
            if u and u["password"] == pwd: session["nickname"] = nickname; return redirect("/main")
            else: error = "<div class=error>Invalid Nickname, Admission No or Password</div>"
    return render_template_string(BASE, title="Login", header="", content=Markup(f"<div class='card'><h2>Login</h2>{error}<form method=POST><input name=nickname placeholder='Nickname' required><input name=admission_no placeholder='Admission Number e.g 1234' required><input type=password name=password placeholder=Password required><button class=btn>Login</button><a class=btn.blue href=/register>Register</a></form></div>"), timer_script="")

@app.route('/lessons')
@login_required
def lessons(nickname, user):
    try:
        expired = not user.get('lesson_expiry') or date.today() > datetime.strptime(user['lesson_expiry'], "%Y-%m-%d").date()
        if user.get('free_days', 0) > 0: expired = False
    except:
        expired = True
    if expired:
        return redirect("/request-payment/lessons")

    with DBSession() as db:
        lessons = db.execute(sa.text("SELECT * FROM lessons WHERE class=:c AND dept=:d"), {"c": user['class'], "d": user.get('dept','')}).mappings().all()
    lessons_html = "".join([f"<div class=card><h3>📖 {l['subject']} - {l['title']}</h3><p>{l['notes']}</p><small>Posted: {l['date']}</small></div>" for l in lessons])
    if not lessons_html: lessons_html = "<p>No lessons for your class yet</p>"
    return render_template_string(BASE, title="Lessons", header=Markup(get_header(nickname,user)), content=Markup(f"<div class=card><h2>My Lessons</h2><p>Access expires: {user['lesson_expiry']}</p><p>Free Days Left: {user.get('free_days', 0)}</p></div>{lessons_html}"), timer_script="")

# ===== GROUP CHAT =====
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

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS dms (
            id SERIAL PRIMARY KEY,
            from_user TEXT,
            to_user TEXT,
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
ADS = json.loads(get_setting("ads", json.dumps(["Ad: Join MOTIZ WhatsApp Group!"])))
NOTICES = json.loads(get_setting("notices", json.dumps(["Welcome to MOTIZ E-LEARNING!"])))

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
    username = session.get("username")
    if not username: return None, None
    with DBSession() as db:
        user = db.execute(sa.text("SELECT * FROM users WHERE username=:u"), {"u": username}).mappings().first()
        if user:
            user = dict(user)
            user['friends'] = json.loads(user.get('friends', '[]'))
        return username, user

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        username, user = get_user()
        if not user: return redirect("/login")
        return f(username, user, *args, **kwargs)
    return wrapper

BASE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title><style>:root{--bg:#f0f2f5;--card:white;--text:#333} body.dark{--bg:#121212;--card:#1e1e1e;--text:#eee}
body{font-family:Segoe UI;background:var(--bg);color:var(--text);margin:0;padding:0;padding-bottom:80px}
.header{background:#0f3460;color:white;padding:10px;text-align:center;position:fixed;top:0;width:100%;z-index:1000;display:flex;justify-content:space-between;align-items:center}
.header h1{margin:0;font-size:0.9rem;flex:1;text-align:center}
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
.like-btn{background:transparent;border:none;color:#2196f3;cursor:pointer;font-weight:bold}
.success{color:green;background:#d4edda;padding:10px;border-radius:5px}.error{color:red;background:#f8d7da;padding:10px;border-radius:5px}
.emoji-box{display:none;margin:8px 0;padding:10px;background:var(--bg);border-radius:8px}
.emoji-btn{font-size:1.5rem;border:none;background:transparent;cursor:pointer;margin:3px}
.chat-box{height:400px;overflow-y:auto;background:var(--bg);padding:10px;border-radius:8px;margin-bottom:10px}
.chat-msg{margin:5px 0;padding:8px;background:var(--card);border-radius:8px}
</style></head><body>{{header}}<div class="container">{{content}}</div><script>{{timer_script}}</script></body></html>"""

def get_header(username,user):
    if not user: return ""
    return f"""<div class="header"><button class="theme-btn" onclick="document.body.classList.toggle('dark')">🌙</button><h1>MOTIZ E-LEARNING INSTITUTION</h1><a href="/main" class="exit-btn">Exit</a></div><div class="nav"><a href="/main">🏠 Home</a><a href="/exam">✍️ CBT</a><a href="/lessons">🎓 Lessons</a><a href="/community">🌍 Community</a><a href="/groups">👥 Groups</a><a href="/dm">💬 DM</a><a href="/friends">👤 Friends</a><a href="/profile">📊 Profile</a><a href="/admin">🔒 Admin</a><a href="/logout">🚪 Logout</a></div>"""

@app.route('/')
def splash():
    return render_template_string("""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Welcome</title><meta http-equiv="refresh" content="3;url=/login"><style>body{margin:0;background:linear-gradient(135deg,#0f3460,#16213e);color:white;font-family:Segoe UI;display:flex;justify-content:center;align-items:center;height:100vh;flex-direction:column;text-align:center}.logo{font-size:2.8rem;font-weight:bold;animation:glow 2s ease-in-out infinite alternate}@keyframes glow{from{text-shadow:0 0 10px #fff}to{text-shadow:0 0 30px #2196f3}}.loader{border:4px solid #fff3;border-top:4px solid white;border-radius:50%;width:40px;height:40px;animation:spin 1s linear infinite;margin-top:20px}@keyframes spin{0%{transform:rotate(0)}100%{transform:rotate(360deg)}}</style></head><body><div class="logo">MOTIZ E-LEARNING INSTITUTION</div><div>Learn. Practice. Excel.</div><div class="loader"></div></body></html>""")

@app.route('/main')
@login_required
def main(username, user):
    notices_html = "".join([f"<div class='card'><b>📢 ADMIN:</b> {n}</div>" for n in NOTICES])
    ads_html = "".join([f"<div style='background:#fff3cd;padding:10px;margin:8px 0;border-radius:8px'><b>📢 AD:</b> {a}</div>" for a in ADS])
    return render_template_string(BASE, title="Home", header=Markup(get_header(username,user)), content=Markup(f"<div class='card'><h2>Welcome {user['name']}</h2><p><b>Class:</b> {user['class']} {user.get('dept','')}</p></div>{ads_html}<h3>General Notice</h3>{notices_html}<a class=btn href=/exam>Start CBT Exam</a>"), timer_script="")

@app.route('/register', methods=["GET","POST"])
def register():
    if get_user()[1]: return redirect("/main")
    error = ""
    if request.method == "POST":
        username = request.form.get("username","").strip().lower()
        with DBSession() as db:
            exists = db.execute(sa.text("SELECT username FROM users WHERE username=:u"), {"u": username}).scalar()
            if exists: error = "<div class=error>Username taken</div>"
            else:
                name = f"{request.form['surname']} {request.form['other']}"
                db.execute(sa.text("INSERT INTO users (username,name,password,class,dept) VALUES (:u,:n,:p,:c,:d)"),
                           {"u": username, "n": name, "p": request.form['password'], "c": request.form['class'], "d": request.form.get('dept','')})
                db.commit()
                session["username"] = username; return redirect("/main")
    js = """<script>function d(){let c=document.getElementById('class').value;let x=document.getElementById('dept');x.innerHTML='';if(['SS1','SS2','SS3'].includes(c)){x.innerHTML='<label>Department *</label><select name=dept required><option value="">Select</option><option>Science</option><option>Commercial</option><option>Art</option></select>'}}</script>"""
    form = f"<div class='card'><h2>Register</h2>{error}<form method=POST><input name=username placeholder='Username' required><input name=surname placeholder='Surname' required><input name=other placeholder='Other Name' required><input type=password name=password placeholder='Password' required><select name=class id=class onchange=d() required><option value=''>Select Class</option>{''.join([f'<option>{c}</option>' for c in CLASSES])}</select><div id=dept></div><button class=btn>Register</button></form></div>{js}"
    return render_template_string(BASE, title="Register", header="", content=Markup(form), timer_script="")

@app.route('/login', methods=["GET","POST"])
def login():
    if get_user()[1]: return redirect("/main")
    error = ""
    if request.method == "POST":
        username, pwd = request.form["username"].strip().lower(), request.form["password"]
        with DBSession() as db:
            u = db.execute(sa.text("SELECT * FROM users WHERE username=:u"), {"u": username}).mappings().first()
            if u and u["password"] == pwd: session["username"] = username; return redirect("/main")
            else: error = "<div class=error>Invalid Login</div>"
    return render_template_string(BASE, title="Login", header="", content=Markup(f"<div class='card'><h2>Login</h2>{error}<form method=POST><input name=username placeholder='Username' required><input type=password name=password placeholder=Password required><button class=btn>Login</button><a class=btn.blue href=/register>Register</a></form></div>"), timer_script="")

@app.route('/lessons')
@login_required
def lessons(username, user):
    try:
        expired = not user.get('lesson_expiry') or date.today() > datetime.strptime(user['lesson_expiry'], "%Y-%m-%d").date()
    except:
        expired = True
    if expired:
        return redirect("/request-payment/lessons")

    with DBSession() as db:
        lessons = db.execute(sa.text("SELECT * FROM lessons WHERE class=:c AND dept=:d"), {"c": user['class'], "d": user.get('dept','')}).mappings().all()
    lessons_html = "".join([f"<div class=card><h3>📖 {l['subject']} - {l['title']}</h3><p>{l['notes']}</p><small>Posted: {l['date']}</small></div>" for l in lessons])
    if not lessons_html: lessons_html = "<p>No lessons for your class yet</p>"
    return render_template_string(BASE, title="Lessons", header=Markup(get_header(username,user)), content=Markup(f"<div class=card><h2>My Lessons</h2><p>Access expires: {user['lesson_expiry']}</p></div>{lessons_html}"), timer_script="")
# ===== GROUP CHAT =====
@app.route('/groups', methods=["GET","POST"])
@login_required
def groups(username, user):
    with DBSession() as db:
        if request.method=="POST":
            if "create_group" in request.form:
                db.execute(sa.text("INSERT INTO groups (name, creator, members, messages) VALUES (:n, :c, :m, :msg)"),
                           {"n": request.form["group_name"], "c": username, "m": json.dumps([username]), "msg": json.dumps([])})
                db.commit()
            return redirect("/groups")

        my_groups = db.execute(sa.text("SELECT * FROM groups")).mappings().all()

    my_groups_html = [f"<a class=btn.blue href=/group/{g['id']}>👥 {g['name']} ({len(json.loads(g['members']))} members)</a>"
                      for g in my_groups if username in json.loads(g['members'])]
    create_form = f"<div class=card><h3>Create Group</h3><form method=POST><input name=group_name placeholder='Group Name' required><button name=create_group class=btn>Create</button></form></div>"
    return render_template_string(BASE, title="Groups", header=Markup(get_header(username,user)), content=Markup(f"{create_form}<div class=card><h3>My Groups</h3>{''.join(my_groups_html) or '<p>No groups yet</p>'}</div>"), timer_script="")

@app.route('/group/<int:gid>', methods=["GET","POST"])
@login_required
def group_chat(username, user, gid):
    with DBSession() as db:
        group = db.execute(sa.text("SELECT * FROM groups WHERE id=:id"), {"id": gid}).mappings().first()
        if not group or username not in json.loads(group['members']): return redirect("/groups")

        members = json.loads(group['members'])
        messages = json.loads(group['messages'])
        is_creator = group['creator']==username
        emojis = "😀😃😄😁😆😅😂🤣"
        emoji_btns = "".join([f"<button type=button class=emoji-btn onclick=\"document.getElementById('msg').value+='{e}'\">{e}</button>" for e in emojis])

        if request.method=="POST":
            if "send_msg" in request.form:
                messages.append({"user": user["name"], "text": request.form["msg"], "time": datetime.now().strftime("%H:%M")})
                db.execute(sa.text("UPDATE groups SET messages=:m WHERE id=:id"), {"m": json.dumps(messages), "id": gid})
            elif "new_name" in request.form and is_creator:
                db.execute(sa.text("UPDATE groups SET name=:n WHERE id=:id"), {"n": request.form["new_name"], "id": gid})
            elif "remove_member" in request.form and is_creator:
                member = request.form["remove_member"]
                if member in members and member!= username: members.remove(member)
                db.execute(sa.text("UPDATE groups SET members=:m WHERE id=:id"), {"m": json.dumps(members), "id": gid})
            elif "add_member" in request.form and is_creator:
                member = request.form["add_member"]
                user_exists = db.execute(sa.text("SELECT username FROM users WHERE username=:u"), {"u": member}).scalar()
                if user_exists and member not in members: members.append(member)
                db.execute(sa.text("UPDATE groups SET members=:m WHERE id=:id"), {"m": json.dumps(members), "id": gid})
            db.commit(); return redirect(f"/group/{gid}")

    msgs = "".join([f"<div class=chat-msg><b>{m['user']}:</b> {m['text']} <small>{m['time']}</small></div>" for m in messages])
    with DBSession() as db:
        friends_options = "".join([f"<option value={f}>{db.execute(sa.text('SELECT name FROM users WHERE username=:u'), {'u': f}).scalar()}</option>" for f in user['friends'] if f not in members])
        members_html = "".join([f"<li>{db.execute(sa.text('SELECT name FROM users WHERE username=:u'), {'u': m}).scalar()} {f'<form method=POST style=display:inline><input type=hidden name=remove_member value={m}><button class=btn.red style=padding:2px 5px;font-size:0.7rem>Remove</button></form>' if is_creator and m!=username else ''}</li>" for m in members])

    add_member_form = f"<form method=POST><select name=add_member required><option value=''>Add Member</option>{friends_options}</select><button class=btn.gray>Add</button></form>" if is_creator else ""
    content = f"<div class=card><h2>{group['name']}</h2>{f'<form method=POST><input name=new_name placeholder=New Group Name required><button name=rename class=btn.orange>Rename</button></form>' if is_creator else ''}{add_member_form}<h4>Members:</h4><ul>{members_html}</ul></div>"
    content += f"<div class=card><div class=chat-box>{msgs or '<p>No messages yet</p>'}</div><form method=POST><input id=msg name=msg placeholder='Type message...' required style=width:70%;display:inline-block><button name=send_msg class=btn.gray style=width:28%;display:inline-block>Send</button><button type=button class='btn gray' onclick=document.getElementById('emoji_box').style.display='block'>😀</button><div id=emoji_box class=emoji-box>{emoji_btns}</div></form></div>"
    return render_template_string(BASE, title=group['name'], header=Markup(get_header(username,user)), content=Markup(content), timer_script="")

# ===== DIRECT MESSAGE =====
@app.route('/dm')
@login_required
def dm_list(username, user):
    with DBSession() as db:
        friends_html = "".join([f"<a class=btn.blue href=/dm/{f}>💬 Chat with {db.execute(sa.text('SELECT name FROM users WHERE username=:u'), {'u': f}).scalar()}</a>" for f in user['friends']])
    return render_template_string(BASE, title="Messages", header=Markup(get_header(username,user)), content=Markup(f"<div class=card><h2>My Friends</h2>{friends_html or '<p>Add friends to start chat</p>'}</div>"), timer_script="")

@app.route('/dm/<to_user>', methods=["GET","POST"])
@login_required
def dm_chat(username, user, to_user):
    if to_user not in user['friends']: return redirect("/dm")
    with DBSession() as db:
        if request.method=="POST":
            db.execute(sa.text("INSERT INTO dms (from_user, to_user, text, time) VALUES (:f, :t, :txt, :time)"),
                       {"f": username, "t": to_user, "txt": request.form["msg"], "time": datetime.now().strftime("%H:%M")})
            db.commit(); return redirect(f"/dm/{to_user}")

        chat = db.execute(sa.text("SELECT * FROM dms WHERE (from_user=:u AND to_user=:t) OR (from_user=:t AND to_user=:u) ORDER BY id"),
                          {"u": username, "t": to_user}).mappings().all()
        to_name = db.execute(sa.text("SELECT name FROM users WHERE username=:u"), {"u": to_user}).scalar()

    msgs = "".join([f"<div class=chat-msg><b>{db.execute(sa.text('SELECT name FROM users WHERE username=:u'), {'u': m['from_user']}).scalar()}:</b> {m['text']} <small>{m['time']}</small></div>" for m in chat])
    return render_template_string(BASE, title=f"Chat with {to_name}", header=Markup(get_header(username,user)), content=Markup(f"<div class=card><div class=chat-box>{msgs}</div><form method=POST><input name=msg placeholder='Type message...' required><button class=btn>Send</button></form></div>"), timer_script="")

# ===== FRIEND REQUEST SYSTEM =====
@app.route('/friends', methods=["GET","POST"])
@login_required
def friends(username, user):
    with DBSession() as db:
        if request.method=="POST":
            if "send_request" in request.form:
                f = request.form["send_request"]
                db.execute(sa.text("INSERT INTO payments (username, name, type, status) VALUES (:u, :n, 'friend_req', 'Pending')"), {"u": f, "n": username})
                db.commit()
            elif "accept_user" in request.form:
                from_user = request.form["accept_user"]
                user['friends'].append(from_user)
                db.execute(sa.text("UPDATE users SET friends=:f WHERE username=:u"), {"f": json.dumps(user['friends']), "u": username})
                from_friends = json.loads(db.execute(sa.text("SELECT friends FROM users WHERE username=:u"), {"u": from_user}).scalar() or '[]')
                from_friends.append(username)
                db.execute(sa.text("UPDATE users SET friends=:f WHERE username=:u"), {"f": json.dumps(from_friends), "u": from_user})
                db.execute(sa.text("DELETE FROM payments WHERE username=:u AND name=:n AND type='friend_req'"), {"u": username, "n": from_user})
                db.commit()
            elif "decline_user" in request.form:
                from_user = request.form["decline_user"]
                db.execute(sa.text("DELETE FROM payments WHERE username=:u AND name=:n AND type='friend_req'"), {"u": username, "n": from_user})
                db.commit()

        incoming = db.execute(sa.text("SELECT * FROM payments WHERE username=:u AND type='friend_req' AND status='Pending'"), {"u": username}).mappings().all()
        all_users = db.execute(sa.text("SELECT * FROM users WHERE username!=:u"), {"u": username}).mappings().all()

    incoming_html = "".join([f"<div class=card><b>{db.execute(sa.text('SELECT name FROM users WHERE username=:u'), {'u': r['name']}).scalar()}</b><div style='display:flex;gap:5px'><form method=POST><input type=hidden name=accept_user value={r['name']}><button class=btn>Accept</button></form><form method=POST><input type=hidden name=decline_user value={r['name']}><button class='btn red'>Decline</button></form></div></div>" for r in incoming])
    all_users_html = "".join([f"<div class=card><b>{u['name']}</b> @{u['username']}<form method=POST><input type=hidden name=send_request value={u['username']}><button class=btn.blue>Add Friend</button></form></div>" for u in all_users if u['username'] not in user['friends']])
    friends_html = "".join([f"<div class=card>👤 {db.execute(sa.text('SELECT name FROM users WHERE username=:u'), {'u': f}).scalar()}</div>" for f in user['friends']]) or "<p>No friends yet</p>"
    return render_template_string(BASE, title="Friends", header=Markup(get_header(username,user)), content=Markup(f"<div class=card><h2>Friend Requests</h2>{incoming_html or '<p>No requests</p>'}</div><div class=card><h2>My Friends</h2>{friends_html}</div><div class=card><h2>All Users</h2>{all_users_html}</div>"), timer_script="")

# ===== EXAM / CBT =====
@app.route('/exam')
@login_required
def exam(username, user):
    key = f"{user['class']}_{user['dept']}" if user['dept'] else user['class']
    subs = SUBJECTS.get(key, [])
    if not subs: return render_template_string(BASE, title="Error", header=Markup(get_header(username,user)), content=Markup("<div class=error>No subjects for your class yet</div>"), timer_script="")
    sub_btns = "".join([f"<a class='btn blue' href=/start/{urllib.parse.quote(key)}/{urllib.parse.quote(s)}>📚 {s}</a>" for s in subs])
    return render_template_string(BASE, title="CBT", header=Markup(get_header(username,user)), content=Markup(f"<div class='card'><h2>Select Subject - {user['class']}</h2>{sub_btns}</div>"), timer_script="")

@app.route('/start/<path:key>/<path:sub>', methods=["GET","POST"])
@login_required
def start(username, user, key, sub):
    key = urllib.parse.unquote(key)
    sub = urllib.parse.unquote(sub)
    limit = FREE_Q if user['q_cycle']=="free" else PAID_Q
    if user['q_used'] >= limit and user['q_cycle']=="free": return redirect("/request-payment/questions")

    with DBSession() as db:
        q_list = db.execute(sa.text("SELECT * FROM questions WHERE key=:k"), {"k": f"{key}_{sub}"}).mappings().all()

    session_key = f"exam_{key}_{sub}"
    if request.method == "GET": questions = list(q_list); random.shuffle(questions); session[session_key] = questions; session['q_index'] = 0

    questions = session.get(session_key, q_list); q_index = session.get('q_index', 0)
    if q_index >= limit or q_index >= len(questions): session.pop(session_key, None); session.pop('q_index', None); return redirect("/result")
    q = questions[q_index]
    q['options'] = json.loads(q['options'])

    timer_js = """let timeLeft = 600; const timerEl = document.createElement('div'); timerEl.className = 'timer'; document.querySelector('.container').prepend(timerEl); function updateTimer(){let m = Math.floor(timeLeft / 60); let s = timeLeft % 60; s = s < 10? '0' + s : s; timerEl.innerHTML = `⏰ TIME LEFT: ${m}:${s}`; if(timeLeft <= 60){timerEl.style.background = '#ffc107';timerEl.style.color = 'black';} if(timeLeft <= 0){document.querySelector('form').submit();} timeLeft--;} updateTimer(); setInterval(updateTimer, 1000);"""

    if request.method == "POST":
        ans = request.form.get("answer")
        with DBSession() as db:
            if ans == q['ans']: db.execute(sa.text("UPDATE users SET correct=correct+1 WHERE username=:u"), {"u": username})
            else: db.execute(sa.text("UPDATE users SET wrong=wrong+1 WHERE username=:u"), {"u": username})
            db.execute(sa.text("UPDATE users SET q_used=q_used+1 WHERE username=:u"), {"u": username})
            db.commit()
        session['q_index'] = q_index + 1
        result_html = f"<div class='card correct'><h3>✅ Correct!</h3><p>{q['exp']}</p></div>" if ans == q['ans'] else f"<div class='card wrong'><h3>❌ Wrong!</h3><p><b>Answer:</b> {q['ans']}</p><p>{q['exp']}</p></div>"
        return render_template_string(BASE, title="Result", header=Markup(get_header(username,user)), content=Markup(f"{result_html}<a class=btn href=/start/{urllib.parse.quote(key)}/{urllib.parse.quote(sub)}>Next Question</a>"), timer_script="")

    options_html = "".join([f"<label style='display:block;padding:10px;margin:8px 0;background:var(--bg);border-radius:8px'><input type=radio name=answer value='{opt}' required> {opt}</label>" for opt in q['options']])
    content = f"<div class='card'><h2>{sub}</h2><h3>Question {q_index+1} of {limit}</h3><p><b>{q['q']}</b></p><form method=POST>{options_html}<button class=btn>Submit</button></form></div>"
    return render_template_string(BASE, title=sub, header=Markup(get_header(username,user)), content=Markup(content), timer_script=Markup(timer_js))

@app.route('/result')
@login_required
def result(username, user):
    with DBSession() as db:
        u = db.execute(sa.text("SELECT * FROM users WHERE username=:u"), {"u": username}).mappings().first()
        total, correct = u['q_used'], u['correct']
        percent = round((correct/total)*100, 1) if total>0 else 0
        grade = "A" if percent>=70 else "B" if percent>=60 else "C" if percent>=50 else "F"
        db.execute(sa.text("UPDATE users SET q_used=0, correct=0, wrong=0 WHERE username=:u"), {"u": username})
        db.commit()
    return render_template_string(BASE, title="Result", header=Markup(get_header(username,user)), content=Markup(f"<div class='card'><h2>🎉 Your Result</h2><p><b>Score:</b> {correct}/{total}</p><p><b>Percentage:</b> {percent}%</p><p><b>Grade:</b> {grade}</p><a class=btn href=/exam>Start New Exam</a></div>"), timer_script="")

# ===== COMMUNITY =====
@app.route('/community', methods=["GET","POST"])
@login_required
def community(username, user):
    is_admin = session.get("admin_logged_in")
    emojis = "😀😃😄😁😆😅😂🤣😊😇🙂🙃😉😌😍🥰😘😗😙😚😋😛😝😜🤪🤨🧐🤓😎🤩🥳"
    with DBSession() as db:
        if request.method=="POST":
            if "new_post" in request.form:
                db.execute(sa.text("INSERT INTO posts (username, name, text, emoji, likes, comments) VALUES (:u, :n, :t, :e, '[]', '[]')"),
                           {"u": username, "n": user["name"], "t": request.form["post"], "e": request.form.get("emoji","")})
            elif "comment_post_id" in request.form:
                p = db.execute(sa.text("SELECT comments FROM posts WHERE id=:id"), {"id": request.form["comment_post_id"]}).scalar()
                comments = json.loads(p); comments.append({"user": user["name"], "text": request.form["comment_text"]})
                db.execute(sa.text("UPDATE posts SET comments=:c WHERE id=:id"), {"c": json.dumps(comments), "id": request.form["comment_post_id"]})
            elif "like_post_id" in request.form:
                p = db.execute(sa.text("SELECT likes FROM posts WHERE id=:id"), {"id": request.form["like_post_id"]}).scalar()
                likes = json.loads(p)
                if username in likes: likes.remove(username)
                else: likes.append(username)
                db.execute(sa.text("UPDATE posts SET likes=:l WHERE id=:id"), {"l": json.dumps(likes), "id": request.form["like_post_id"]})
            elif "delete_post_id" in request.form and is_admin:
                db.execute(sa.text("DELETE FROM posts WHERE id=:id"), {"id": request.form["delete_post_id"]})
            db.commit(); return redirect("/community")
        posts = db.execute(sa.text("SELECT * FROM posts ORDER BY id DESC")).mappings().all()

    emoji_btns = "".join([f"<button type=button class=emoji-btn onclick=\"document.getElementById('post').value+='{e}';document.getElementById('emoji_box').style.display='none'\">{e}</button>" for e in emojis])
    
    posts_html = ""
    for p in posts:
        likes_count = len(json.loads(p['likes']))
        comments_data = json.loads(p['comments'])
        comments_html = "".join([f'<div class=comment><b>{c["user"]}:</b> {c["text"]}</div>' for c in comments_data]) or '<p style=font-size:0.8rem>No comments</p>'
        delete_btn = f'<form method=POST style=display:inline><input type=hidden name=delete_post_id value={p["id"]}><button class=btn.red style=padding:5px;font-size:0.8rem;margin-left:10px>Delete</button></form>' if is_admin else ''
        posts_html += f"<div class=card><b>{p['name']}</b>: {p['text']} {p['emoji']}<div style=margin-top:8px><form method=POST style='display:inline'><input type=hidden name=like_post_id value={p['id']}><button class=like-btn>🤍 Like ({likes_count})</button></form>{delete_btn}</div><div class=comment-box><b>Comments:</b>{comments_html}<form method=POST><input type=hidden name=comment_post_id value={p['id']}><input name=comment_text placeholder='Write comment...' required style=width:75%;display:inline-block><button class='btn gray' style=width:23%;display:inline-block>Send</button></form></div></div>"
    
    emoji_js = """<script>function toggleEmoji(){let x=document.getElementById('emoji_box');x.style.display=x.style.display=='block'?'none':'block'}</script>"""
    return render_template_string(BASE, title="Community", header=Markup(get_header(username,user)), content=Markup(f"<div class=card><h2>Community</h2><form method=POST><textarea name=post id=post placeholder='Whats on your mind?' required></textarea><button type=button class='btn gray' onclick=toggleEmoji()>😀 Add Emoji</button><div id=emoji_box class=emoji-box>{emoji_btns}</div><button class=btn>Post</button><input type=hidden name=new_post value=1></form></div>{posts_html}"), timer_script=Markup(emoji_js))
# ===== PAYMENT =====
@app.route('/request-payment/<t>')
@login_required
def req_pay(username, user, t):
    price = QUESTION_PRICE if t=="questions" else LESSON_PRICE
    with DBSession() as db:
        pending = db.execute(sa.text("SELECT * FROM payments WHERE username=:u AND type=:t AND status='Pending'"), {"u": username, "t": t}).scalar()
    if pending: return render_template_string(BASE, title="Payment", header=Markup(get_header(username,user)), content=Markup("<div class=card><h2>⏳ Request Pending</h2><p>Wait for admin to verify</p></div>"), timer_script="")
    copy_js = f"""<script>function copyAcc(){{navigator.clipboard.writeText('{PALMPAY_ACCOUNT}');alert('Account number copied!')}}</script>"""
    form = f"""<div class=card><h2>Pay ₦{price} to unlock</h2>
    <p><b>Bank:</b> {PALMPAY_BANK}<br><b>Account:</b> {PALMPAY_ACCOUNT} <button class=copy-btn onclick=copyAcc()>Copy</button><br><b>Name:</b> {PALMPAY_NAME}</p>
    <form method=POST action=/confirm/{t}>
    <input name=bank_used placeholder="Bank you used to transfer e.g GTBank" required>
    <input name=account_name placeholder="Account Name you used" required>
    <input name=teller_id placeholder="Transaction ID / Teller ID" required>
    <button class=btn>I Have Paid</button></form></div>"""
    return render_template_string(BASE, title="Payment", header=Markup(get_header(username,user)), content=Markup(form), timer_script=Markup(copy_js))

@app.route('/confirm/<t>', methods=["POST"])
@login_required
def confirm(username, user, t):
    with DBSession() as db:
        db.execute(sa.text("INSERT INTO payments (username, name, type, status, bank_used, account_name, teller_id) VALUES (:u, :n, :t, 'Pending', :b, :a, :tid)"),
                   {"u": username, "n": user["name"], "t": t, "b": request.form["bank_used"], "a": request.form["account_name"], "tid": request.form["teller_id"]})
        db.commit()
    return render_template_string(BASE, title="Sent", header=Markup(get_header(username,user)), content=Markup("<div class='card'><h2>✅ Request Sent</h2><p>Admin will verify with your bank details</p><a class=btn href=/main>Home</a></div>"), timer_script="")

# ===== ADMIN PANEL =====
@app.route('/admin', methods=["GET","POST"])
def admin():
    global ADMIN_PASS
    logged_in = session.get("admin_logged_in")
    error = ""
    if request.method=="POST":
        if "login_pass" in request.form:
            if request.form.get("login_pass")== ADMIN_PASS: session["admin_logged_in"] = True; return redirect("/admin")
            else: error = "<div class=error>Wrong Password</div>"
        elif logged_in:
            with DBSession() as db:
                if "verify_id" in request.form:
                    req = db.execute(sa.text("SELECT * FROM payments WHERE id=:id"), {"id": request.form["verify_id"]}).mappings().first()
                    if req["type"] == "questions": db.execute(sa.text("UPDATE users SET q_cycle='paid' WHERE username=:u"), {"u": req["username"]})
                    if req["type"] == "lessons": db.execute(sa.text("UPDATE users SET lesson_expiry=:d WHERE username=:u"), {"d": str(date.today() + timedelta(days=30)), "u": req["username"]})
                    db.execute(sa.text("UPDATE payments SET status='Verified' WHERE id=:id"), {"id": request.form["verify_id"]})
                    db.commit(); error = "<div class=success>Payment Verified & Saved</div>"

                if "deny_id" in request.form:
                    db.execute(sa.text("UPDATE payments SET status='Denied' WHERE id=:id"), {"id": request.form["deny_id"]})
                    db.commit(); error = "<div class=error>Payment Denied</div>"

                if "change_pass" in request.form:
                    if request.form["old_pass"]!= ADMIN_PASS: error = "<div class=error>Old password is wrong</div>"
                    else: ADMIN_PASS = request.form["new_pass"]; set_setting("admin_pass", ADMIN_PASS); error = "<div class=success>Admin Password Changed & Saved</div>"

                if "add_lesson" in request.form:
                    db.execute(sa.text("INSERT INTO lessons (class, dept, subject, title, notes, date) VALUES (:c, :d, :s, :t, :n, :date)"),
                               {"c": request.form['lesson_class'], "d": request.form.get('lesson_dept',''), "s": request.form['lesson_subject'], "t": request.form['lesson_title'], "n": request.form['lesson_notes'], "date": str(date.today())})
                    db.commit(); error = "<div class=success>Lesson Note Posted & Saved</div>"

                if "add_question" in request.form:
                    cls = request.form['admin_class']
                    dept = request.form.get('admin_dept','')
                    sub = request.form['admin_subject']
                    key = f"{cls}_{dept}_{sub}" if dept else f"{cls}_{sub}"
                    db.execute(sa.text("INSERT INTO questions (key, q, options, ans, exp) VALUES (:k, :q, :o, :a, :e)"),
                               {"k": key, "q": request.form["q"], "o": json.dumps([request.form["a"],request.form["b"],request.form["c"],request.form["d"]]), "a": request.form["ans"], "e": request.form["exp"]})
                    db.commit(); error = "<div class=success>Single Question Added & Saved</div>"

                if "bulk_upload" in request.form:
                    cls = request.form['bulk_class']
                    dept = request.form.get('bulk_dept','')
                    sub = request.form['bulk_subject']
                    key = f"{cls}_{dept}_{sub}" if dept else f"{cls}_{sub}"
                    lines = request.form["bulk_text"].strip().split('\n')
                    count = 0
                    for line in lines:
                        parts = [p.strip() for p in line.split('|')]
                        if len(parts) >= 7:
                            db.execute(sa.text("INSERT INTO questions (key, q, options, ans, exp) VALUES (:k, :q, :o, :a, :e)"),
                                       {"k": key, "q": parts[0], "o": json.dumps([parts[1],parts[2],parts[3],parts[4]]), "a": parts[5], "e": parts[6]})
                            count += 1
                    db.commit(); error = f"<div class=success>{count} Questions Added & Saved</div>"

                if "new_notice" in request.form:
                    notices = NOTICES + [request.form["new_notice"]]
                    ads = ADS + [request.form["new_notice"]]
                    set_setting("notices", json.dumps(notices))
                    set_setting("ads", json.dumps(ads))
                    error = "<div class=success>Notice/Ad Posted to Home</div>"

    if not logged_in:
        return render_template_string(BASE, title="Admin", header="", content=Markup(f"<div class='card'><h2>🔒 Admin Login</h2>{error}<form method=POST><input type=password name=login_pass placeholder='Enter Admin Password' required><button class=btn>Login</button></form></div>"), timer_script="")

js = """<script>
    const subjects = %s;
    function updateDept(id){
        let c = document.getElementById(id+'_class').value;
        let d = document.getElementById(id+'_dept_div');
        d.innerHTML = '';
        if(['SS1','SS2','SS3'].includes(c)){
            d.innerHTML = '<label>Department</label><select name='+id+'_dept id='+id+'_dept onchange=updateSub("'+id+'") required><option value="">Select Dept</option><option>Science</option><option>Commercial</option><option>Art</option></select>';
        } else { updateSub(id); }
    }
    function updateSub(id){
        let c = document.getElementById(id+'_class').value;
        let d = document.getElementById(id+'_dept')? document.getElementById(id+'_dept').value : '';
        let key = d? c+'_'+d : c;
        let s = document.getElementById(id+'_subject');
        s.innerHTML = '<option value="">Select Subject</option>';
        (subjects[key] || []).forEach(sub => s.innerHTML += '<option>' + sub + '</option>');
    }
    </script>""" % json.dumps(SUBJECTS)

    with DBSession() as db:
        reqs = db.execute(sa.text("SELECT * FROM payments WHERE status='Pending'")).mappings().all()
    reqs_html = "".join([f"<div class='card'><b>{r['name']}</b> for {r['type']}<br><small>Bank: {r.get('bank_used','N/A')} | Acc Name: {r.get('account_name','N/A')} | Teller: {r.get('teller_id','N/A')}</small><div style='display:flex;gap:5px'><form method=POST style='flex:1'><input type=hidden name=verify_id value={r['id']}><button class=btn>Verify</button></form><form method=POST style='flex:1'><input type=hidden name=deny_id value={r['id']}><button class='btn red'>Deny</button></form></div></div>" for r in reqs])

    form = f"""<div class='card'><h2>Admin Panel</h2>{error}</div>
    <div class='card'><h2>Pending Payments</h2>{reqs_html or '<p>No pending payments</p>'}</div>
    <div class='card'><h2>Change Admin Password</h2><form method=POST><input type=password name=old_pass placeholder="Current Password" required><input type=password name=new_pass placeholder="New Password" required><button name=change_pass class=btn.orange>Change Password</button></form></div>
    <div class='card'><h2>📖 Upload Lesson Note</h2><form method=POST>
    <label>Select Class</label><select name=lesson_class id=lesson_class onchange=updateDept("lesson") required><option value="">Select Class</option>{''.join([f'<option>{c}</option>' for c in CLASSES])}</select>
    <div id=lesson_dept_div></div>
    <label>Select Subject</label><select name=lesson_subject id=lesson_subject required><option value="">Select Subject</option></select>
    <input name=lesson_title placeholder="Lesson Title e.g Algebra Basics" required>
    <textarea name=lesson_notes rows=8 placeholder="Paste lesson notes here..." required></textarea>
    <button name=add_lesson class=btn.blue>Post Lesson</button></form></div>
    <div class='card'><h2>Post General Notice / Ad</h2><form method=POST><textarea name=new_notice placeholder="This will show on Home page for all users" required></textarea><button class=btn.orange>Post Notice</button></form></div>
    <div class='card'><h2>Add Single Question</h2><form method=POST>
    <label>Select Class</label><select name=admin_class id=admin_class onchange=updateDept("admin") required><option value="">Select Class</option>{''.join([f'<option>{c}</option>' for c in CLASSES])}</select>
    <div id=admin_dept_div></div>
    <label>Select Subject</label><select name=admin_subject id=admin_subject required><option value="">Select Subject</option></select>
    <textarea name=q placeholder=Question required></textarea>
    <input name=a placeholder="Option A" required><input name=b placeholder="Option B" required><input name=c placeholder="Option C" required><input name=d placeholder="Option D" required>
    <input name=ans placeholder="Correct Answer" required><input name=exp placeholder="Explanation" required>
    <button name=add_question class=btn>Post Question</button></form></div>
    <div class='card'><h2>Bulk Upload Questions</h2><p><b>Format per line:</b> Question|A|B|C|D|CorrectAnswer|Explanation</p><form method=POST>
    <label>Select Class</label><select name=bulk_class id=bulk_class onchange=updateDept("bulk") required><option value="">Select Class</option>{''.join([f'<option>{c}</option>' for c in CLASSES])}</select>
    <div id=bulk_dept_div></div>
    <label>Select Subject</label><select name=bulk_subject id=bulk_subject required><option value="">Select Subject</option></select>
    <textarea name=bulk_text rows=10 placeholder="What is 2+2?|3|4|5|6|4|Simple addition\nCapital of Nigeria?|Lagos|Abuja|Kano|PH|Abuja|FCT" required></textarea>
    <button name=bulk_upload class=btn.blue>Upload Bulk Questions</button></form></div>"""
    return render_template_string(BASE, title="Admin", header="", content=Markup(form), timer_script=Markup(js))

@app.route('/profile')
@login_required
def profile(username, user):
    status = "PAID ✅" if user['q_cycle']=="paid" else "FREE"
    lesson = user['lesson_expiry'] if user['lesson_expiry'] else "No Access"
    return render_template_string(BASE, title="Profile", header=Markup(get_header(username,user)), content=Markup(f"<div class=card><h2>{user['name']}</h2><p><b>Username:</b> {username}</p><p><b>Class:</b> {user['class']} {user.get('dept','')}</p><p><b>CBT Status:</b> {status}</p><p><b>Lessons:</b> {lesson}</p></div>"), timer_script="")

@app.route('/logout')
def logout(): session.clear(); return redirect("/login")

if __name__ == '__main__':
    print("===================================")
    print("MOTIZ E-LEARNING INSTITUTION v9.1")
    print("ALL FEATURES ACTIVE + RENDER DB")
    print("Admin Password:", ADMIN_PASS)
    print("===================================")
    app.run(host='0.0.0.0', port=5000, debug=False)
