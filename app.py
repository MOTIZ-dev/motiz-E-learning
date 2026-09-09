from flask import Flask, render_template_string, request, redirect, session
from markupsafe import Markup
from datetime import date, datetime, timedelta
import random, json, os, urllib.parse
from functools import wraps
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import pytz

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', "motiz_secret_key_2026_v10_final")

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise Exception("DATABASE_URL environment variable is not set")

engine = sa.create_engine(DATABASE_URL)
DBSession = sessionmaker(bind=engine)

CLOUD_NAME = os.environ.get('CLOUD_NAME', '')
CLOUD_API_KEY = os.environ.get('CLOUD_API_KEY', '')
CLOUD_API_SECRET = os.environ.get('CLOUD_API_SECRET', '')

PALMPAY_ACCOUNT = "8908025244"
PALMPAY_NAME = "HAMZAT KOLADE AJIMOTI"
PALMPAY_BANK = "PALMPAY"
LESSON_PRICE = 1000
QUESTION_PRICE = 500
ADMIN_PASS = os.environ.get('ADMIN_PASS', "24434")
FREE_Q = 30
PAID_Q = 70
TIMER_PER_QUESTION = 120

NIGERIA_TZ = pytz.timezone('Africa/Lagos')

def init_db():
    with engine.connect() as conn:
        # FIX: lesson_expiry can be NULL
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, nickname TEXT UNIQUE, name TEXT, password TEXT, class TEXT, dept TEXT, q_cycle TEXT DEFAULT 'free', q_used INTEGER DEFAULT 0, lesson_expiry DATE DEFAULT NULL, correct INTEGER DEFAULT 0, wrong INTEGER DEFAULT 0, friends TEXT DEFAULT '[]', referred_by TEXT DEFAULT NULL, referral_count INTEGER DEFAULT 0, free_days INTEGER DEFAULT 0, is_verified BOOLEAN DEFAULT FALSE, last_seen TEXT DEFAULT '{}');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS payments (id SERIAL PRIMARY KEY, nickname TEXT, name TEXT, type TEXT, status TEXT, bank_used TEXT, account_name TEXT, date_paid TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS friend_requests (id SERIAL PRIMARY KEY, from_nickname TEXT, to_nickname TEXT, status TEXT DEFAULT 'Pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, nickname TEXT, name TEXT, text TEXT, image_url TEXT, likes TEXT DEFAULT '[]', comments TEXT DEFAULT '[]', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS dms (id SERIAL PRIMARY KEY, from_nickname TEXT, to_nickname TEXT, text TEXT, image_url TEXT, time TEXT, read BOOLEAN DEFAULT FALSE);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS groups (id SERIAL PRIMARY KEY, name TEXT, creator TEXT, members TEXT DEFAULT '[]', messages TEXT DEFAULT '[]');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS lessons (id SERIAL PRIMARY KEY, class TEXT, dept TEXT, subject TEXT, title TEXT, notes TEXT, audio_url TEXT, date TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS questions (id SERIAL PRIMARY KEY, key TEXT, q TEXT, options TEXT, ans TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS referrals (id SERIAL PRIMARY KEY, referrer TEXT, referred TEXT, paid BOOLEAN DEFAULT FALSE, bonus_given BOOLEAN DEFAULT FALSE);"))
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
NOTICES = json.loads(get_setting("notices", json.dumps([{"title":"Welcome","text":"Welcome to MOTIZ E-LEARNING!","created_at": str(datetime.now(NIGERIA_TZ))}])))
PINNED_NOTICE = get_setting("pinned_notice", "")

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

def get_user():
    nickname = session.get("nickname")
    if not nickname: return None, None
    with DBSession() as db:
        user = db.execute(sa.text("SELECT * FROM users WHERE nickname=:u"), {"u": nickname}).mappings().first()
        if user:
            user = dict(user)
            user['friends'] = json.loads(user.get('friends', '[]'))
            user['last_seen'] = json.loads(user.get('last_seen', '{}'))
        return nickname, user

def get_unread_counts(nickname, user):
    if not user: return {"dm": 0, "comm": 0}
    with DBSession() as db:
        dm_unread = db.execute(sa.text("SELECT COUNT(*) FROM dms WHERE to_nickname=:u AND read=FALSE"), {"u": nickname}).scalar()
        # FIX: Use last_seen instead of 1 day
        last_seen_comm = user['last_seen'].get('community', '2000-01-01 00:00:00')
        comm_unread = db.execute(sa.text("SELECT COUNT(*) FROM posts WHERE created_at > :t"), {"t": last_seen_comm}).scalar()
    return {"dm": dm_unread, "comm": comm_unread}

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        nickname, user = get_user()
        if not user: return redirect("/login")
        return f(nickname, user, *args, **kwargs)
    return wrapper

BASE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title><style>:root{--bg:#f0f2f5;--card:white;--text:#333} body.dark{--bg:#121212;--card:#1e1e1e;--text:#eee}
body{font-family:Segoe UI;background:var(--bg);color:var(--text);margin:0;padding:0;padding-bottom:80px}
.header{background:#0f3460;color:white;padding:10px;text-align:center;position:fixed;top:0;width:100%;z-index:1000;display:flex;justify-content:space-between;align-items:center}
.header h1{margin:0;font-size:0.85rem;flex:1;text-align:center;line-height:1.1;white-space:nowrap}
.theme-btn{border:none;background:transparent;color:white;font-size:1.3rem;cursor:pointer;margin-right:10px}
.exit-btn{background:transparent;color:white;border:none;font-size:1.5rem;text-decoration:none;margin-left:10px}
.nav{display:flex;gap:5px;background:#16213e;padding:5px;flex-wrap:wrap;position:fixed;top:50px;width:100%;overflow-x:auto;z-index:999}
.nav a{color:white;text-decoration:none;padding:5px 8px;border-radius:10px;border:1px solid #fff3;font-size:0.8rem;position:relative}
.bell{position:absolute;top:-5px;right:-5px;background:red;color:white;border-radius:50%;font-size:0.6rem;padding:2px 5px}
.container{padding:10px;padding-top:60px}
.card{background:var(--card);padding:12px;margin:8px 0;border-radius:10px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}
.btn{background:#28a745;color:white;padding:12px 15px;text-decoration:none;border-radius:8px;display:block;margin:8px 0;text-align:center;font-weight:bold;border:none;width:100%;cursor:pointer}
.btn.red{background:#e94560}.btn.blue{background:#2196f3}.btn.orange{background:#ff9800}.btn.gray{background:#6c757d;font-size:0.9rem;padding:8px}
input,select,textarea{width:100%;padding:10px;margin:5px 0;border-radius:5px;border:1px solid #ccc;box-sizing:border-box;font-size:1rem;background:var(--card);color:var(--text)}
.success{color:green;background:#d4edda;padding:10px;border-radius:5px}.error{color:red;background:#f8d7da;padding:10px;border-radius:5px}
.badge{background:#28a745;color:white;padding:2px 6px;border-radius:10px;font-size:0.7rem;margin-left:5px}
.notice-title{font-size:1.1rem;font-weight:bold;color:#0f3460;margin-bottom:5px}
@keyframes glow{from{text-shadow:0 0 10px #fff}to{text-shadow:0 0 30px #2196f3}}
.timer{background:#e94560;color:white;padding:12px;text-align:center;border-radius:8px;font-weight:bold;font-size:1.3rem;position:sticky;top:60px;z-index:999}
.friend-card{display:flex;align-items:center;gap:12px;padding:12px;background:var(--bg);border-radius:10px;margin:8px 0;text-decoration:none;color:var(--text)}
.friend-avatar{width:50px;height:50px;border-radius:50%;background:#2196f3;color:white;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:1.3rem}
.subject-btn{display:inline-block;background:#2196f3;color:white;padding:10px 15px;margin:5px;border-radius:8px;cursor:pointer;border:none;font-weight:bold}
.subject-btn.active{background:#28a745}
.dept-btn{display:block;width:100%;background:#ff9800;color:white;padding:12px;margin:5px 0;border-radius:8px;cursor:pointer;border:none;font-weight:bold;font-size:1rem}
.subject-grid{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.comment-box{margin-top:10px;padding-top:10px;border-top:1px dashed #ccc}
.comment{font-size:0.9rem;background:#f0f2f5;padding:6px;border-radius:5px;margin:4px 0}
.like-btn{background:transparent;border:none;color:#e94560;cursor:pointer;font-weight:bold;margin-right:10px}
.chat-box{height:400px;overflow-y:auto;background:var(--bg);padding:10px;border-radius:8px;margin-bottom:10px}
.chat-msg{margin:5px 0;padding:8px;background:var(--card);border-radius:8px;max-width:75%;clear:both}
.chat-me{background:#dcf8c6;margin-left:auto;text-align:right}
.chat-other{background:var(--card);margin-right:auto;text-align:left}
.correct{border-left:5px solid #28a745}
.wrong{border-left:5px solid #e94560}
</style></head><body>{{header}}<div class="container">{{content}}</div><script>{{timer_script}}</script></body></html>"""

def get_header(nickname,user, show_nav=False):
    if not user: return ""
    unread = get_unread_counts(nickname, user)
    nav_html = ""
    if show_nav:
        nav_html = f"""<div class="nav">
        <a href="/main">🏠 Home</a>
        <a href="/exam">✍️ CBT</a>
        <a href="/lessons">🎓 Lessons</a>
        <a href="/community">🌍 Community {f'<span class=bell>{unread["comm"]}</span>' if unread['comm']>0 else ''}</a>
        <a href="/groups">👥 Groups</a>
        <a href="/dm">💬 DM {f'<span class=bell>{unread["dm"]}</span>' if unread['dm']>0 else ''}</a>
        <a href="/friends">👤 Friends</a>
        <a href="/profile">📊 Profile</a>
        <a href="/admin">🔒 Admin</a>
        <a href="/logout">🚪 Logout</a>
        </div>"""
    verified = '<span class=badge>✓ Verified</span>' if user.get('is_verified') else ""
    return f"""<div class="header"><a href="/main" class="exit-btn">⬅️</a><h1>MOTIZ E-LEARNING INSTITUTION {verified}</h1><button class="theme-btn" onclick="document.body.classList.toggle('dark')">🌙</button></div>{nav_html}"""

@app.route('/')
def splash():
    return render_template_string("""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Welcome</title><meta http-equiv="refresh" content="4;url=/login">
<style>body{margin:0;background:linear-gradient(135deg,#0f3460,#16213e);color:white;font-family:Segoe UI;display:flex;justify-content:center;align-items:center;height:100vh;flex-direction:column;text-align:center}
.logo{font-size:2.8rem;font-weight:bold;animation:glow 2s ease-in-out infinite alternate;line-height:1.2;margin-bottom:20px}
.subtext{font-size:1.4rem;margin-top:15px;opacity:0.9;font-weight:bold}
@keyframes glow{from{text-shadow:0 0 10px #fff}to{text-shadow:0 0 30px #2196f3}}</style></head><body>
<div class="logo">MOTIZ E-LEARNING INSTITUTION</div>
<div class="subtext">Learn 📚</div>
<div class="subtext">Practice 📙</div>
<div class="subtext">Excel 📖</div>
</body></html>""")

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
                session["nickname"] = nickname; return redirect("/main")
    js = """<script>function d(){let c=document.getElementById('class').value;let x=document.getElementById('dept');x.innerHTML='';if(['SS1','SS2','SS3'].includes(c)){x.innerHTML='<label>Department *</label><select name=dept id=dept required><option value="">Select Department</option><option>Science</option><option>Commercial</option><option>Art</option></select>'}else{x.innerHTML='<input type=hidden name=dept value=>';}}</script>"""
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
    return render_template_string(BASE, title="Home", header=Markup(get_header(nickname,user, show_nav=True)), content=Markup(f"<div class='card'><h2>Welcome {user['name']}</h2><p><b>Class:</b> {user['class']} {user.get('dept','')}</p></div>{pinned_html}<h3>General Notice</h3>{notices_html}<a class=btn href=/exam>Start CBT Exam</a>"), timer_script="")

@app.route('/exam')
@login_required
def exam(nickname, user):
    key = f"{user['class']}_{user['dept']}" if user['dept'] else user['class']
    subs = SUBJECTS.get(key, [])
    if not subs: return render_template_string(BASE, title="Error", header=Markup(get_header(nickname,user)), content=Markup("<div class=error>No subjects for your class yet</div>"), timer_script="")
    sub_btns = "".join([f"<a class='btn blue' href=/start/{urllib.parse.quote(key)}/{urllib.parse.quote(s)}>📚 {s}</a>" for s in subs])

    if user['q_cycle']=='free':
        q_left = FREE_Q - user['q_used']
        q_info = f"<p><b>Free Questions Left:</b> {q_left}</p>" if q_left > 0 else "<p style=color:red><b>You used all 30 free questions. Pay to continue</b></p>"
    else:
        q_info = "<p style=color:green><b>Status:</b> Paid - Unlimited Access</p>"

    return render_template_string(BASE, title="CBT", header=Markup(get_header(nickname,user)), content=Markup(f"<div class='card'><h2>Select Subject - {user['class']}</h2>{q_info}{sub_btns}</div>"), timer_script="")

@app.route('/start/<path:key>/<path:sub>', methods=["GET","POST"])
@login_required
def start(nickname, user, key, sub):
    key = urllib.parse.unquote(key); sub = urllib.parse.unquote(sub)
    limit = FREE_Q if user['q_cycle']=="free" else PAID_Q

    if user['q_cycle']=="free" and user['q_used'] >= FREE_Q:
        return redirect("/request-payment/questions")

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

    timer_js = Markup(f"""let timeLeft = {TIMER_PER_QUESTION}; const timerEl = document.createElement('div'); timerEl.className = 'timer'; document.querySelector('.container').prepend(timerEl); function updateTimer(){{let m = Math.floor(timeLeft / 60); let s = timeLeft % 60; s = s < 10? '0' + s : s; timerEl.innerHTML = '⏰ TIME LEFT: ' + m + ':' + s; if(timeLeft <= 30){{timerEl.style.background = '#ffc107';timerEl.style.color = 'black';}} if(timeLeft <= 0){{document.getElementById('exam_form').submit();}} timeLeft--;}} updateTimer(); setInterval(updateTimer, 1000);""")

    options_html = "".join([f"<label style='display:block;padding:10px;margin:8px 0;background:var(--bg);border-radius:8px'><input type=radio name=answer value='{opt}' {'checked' if saved_ans==opt else ''} required> {opt}</label>" for opt in q['options']])
    prev_btn = f"<button name=prev class='btn gray' {'disabled' if q_index==0 else ''}>⬅️ Prev</button>" if q_index > 0 else ""
    next_btn = f"<button name=next class='btn blue'>Next ➡️</button>" if q_index < len(questions)-1 else f"<button name=submit_exam class='btn orange'>Submit Exam</button>"

    content = f"<div class='card'><h2>{sub}</h2><h3>Question {q_index+1} of {len(questions)}</h3><p><b>{q['q']}</b></p><form method=POST id=exam_form>{options_html}<input type=hidden name=save_answer value=1><div style='display:flex;gap:10px'>{prev_btn}{next_btn}</div></form></div>"
    return render_template_string(BASE, title=sub, header=Markup(get_header(nickname,user)), content=Markup(content), timer_script=timer_js)

@app.route('/result')
@login_required
def result(nickname, user):
    # FIX: Handle refresh crash
    session_key = None
    answers_key = None
    for k in session.keys():
        if k.startswith('exam_'): session_key = k
        if k.startswith('answers_'): answers_key = k
    
    if not session_key or not answers_key:
        return redirect("/exam")

    questions = session.get(session_key, [])
    answers = session.get(answers_key, {})

    if not questions: return redirect("/exam") # FIX: Empty session

    correct = 0
    result_html = ""
    for i, q in enumerate(questions):
        q['options'] = json.loads(q['options'])
        user_ans = answers.get(str(i))
        if user_ans == q['ans']: correct += 1
        status = "correct" if user_ans == q['ans'] else "wrong"
        result_html += f"<div class='card {status}'><h4>Q{i+1}: {q['q']}</h4><p><b>Your Answer:</b> {user_ans or 'Not Answered'}</p><p><b>Correct Answer:</b> {q['ans']}</p></div>"

    total = len(questions)
    wrong = total - correct
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET q_used=q_used+:t, correct=correct+:c, wrong=wrong+:w WHERE nickname=:u"), {"t": total, "c": correct, "w": wrong, "u": nickname})
        db.commit()

    percent = round((correct/total)*100, 1) if total>0 else 0
    grade = "A" if percent>=70 else "B" if percent>=60 else "C" if percent>=50 else "F"
    session.pop(session_key, None); session.pop(answers_key, None)

    return render_template_string(BASE, title="Result", header=Markup(get_header(nickname,user)), content=Markup(f"<div class='card'><h2>🎉 Your Result</h2><p><b>Score:</b> {correct}/{total}</p><p><b>Percentage:</b> {percent}%</p><p><b>Grade:</b> {grade}</p></div>{result_html}<a class=btn href=/exam>Start New Exam</a>"), timer_script="")

@app.route('/request-payment/<t>')
@login_required
def req_pay(nickname, user, t):
    price = QUESTION_PRICE if t=="questions" else LESSON_PRICE
    with DBSession() as db: pending = db.execute(sa.text("SELECT * FROM payments WHERE nickname=:u AND type=:t AND status='Pending'"), {"u": nickname, "t": t}).scalar()
    if pending: return render_template_string(BASE, title="Payment", header=Markup(get_header(nickname,user)), content=Markup("<div class=card><h2>⏳ Request Pending</h2><p>Wait for admin to verify</p></div>"), timer_script="")

    copy_js = Markup(f"""<script>function copyAcc(){{let acc = '{PALMPAY_ACCOUNT}';navigator.clipboard.writeText(acc).then(()=>{{alert('Account number copied!')}})}}</script>""")

    form = f'<div class=card><h2>Pay &#8358;{price} to unlock</h2><p><b>Bank:</b> {PALMPAY_BANK}<br><b>Account:</b> {PALMPAY_ACCOUNT} <button type=button class=btn.gray onclick=copyAcc()>Copy</button><br><b>Name:</b> {PALMPAY_NAME}</p><p style=color:orange;font-weight:bold>ADMIN WILL VERIFY WITHIN 24HRS</p><form method=POST action=/confirm/{t}><input name=bank_used placeholder="Bank you used to transfer e.g GTBank" required><input name=account_name placeholder="Account Name you used" required><button class=btn>I Have Paid</button></form></div>'
    return render_template_string(BASE, title="Payment", header=Markup(get_header(nickname,user)), content=Markup(form), timer_script=copy_js)

@app.route('/confirm/<t>', methods=["POST"])
@login_required
def confirm(nickname, user, t):
    with DBSession() as db:
        db.execute(sa.text("INSERT INTO payments (nickname, name, type, status, bank_used, account_name) VALUES (:u, :n, :t, 'Pending', :b, :a)"),
                   {"u": nickname, "n": user["name"], "t": t, "b": request.form["bank_used"], "a": request.form["account_name"]})
        db.commit()
    return render_template_string(BASE, title="Sent", header=Markup(get_header(nickname,user)), content=Markup("<div class='card'><h2>✅ Request Sent</h2><p>Admin will verify with your bank details</p><a class=btn href=/main>Home</a></div>"), timer_script="")
@app.route('/community', methods=["GET","POST"])
@login_required
def community(nickname, user):
    is_admin = session.get("admin_logged_in")
    with DBSession() as db:
        # Mark community as seen
        last_seen = user['last_seen']
        last_seen['community'] = str(datetime.now(NIGERIA_TZ))
        db.execute(sa.text("UPDATE users SET last_seen=:l WHERE nickname=:u"), {"l": json.dumps(last_seen), "u": nickname})

        if request.method=="POST":
            if "new_post" in request.form:
                image_url = ""
                if 'post_image' in request.files and request.files['post_image'].filename!= '':
                    # CLOUDINARY UPLOAD - UNCOMMENT AFTER SETUP
                    # import cloudinary.uploader
                    # res = cloudinary.uploader.upload(request.files['post_image'])
                    # image_url = res['secure_url']
                    pass

                db.execute(sa.text("INSERT INTO posts (nickname, name, text, image_url, likes, comments) VALUES (:u, :n, :t, :img, '[]', '[]')"),
                           {"u": nickname, "n": user["name"], "t": request.form["post"], "img": image_url})
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

    posts_html = ""
    for p in posts:
        likes_count = len(json.loads(p['likes'])); comments_data = json.loads(p['comments'])
        img_html = f"<img src={p['image_url']} style='width:100%;border-radius:8px;margin-top:8px'>" if p['image_url'] else ""
        comments_html = "".join([f'<div class=comment><b>{c["user"]}:</b> {c["text"]}</div>' for c in comments_data]) or '<p style=font-size:0.8rem>No comments</p>'
        delete_btn = f'<form method=POST style=display:inline><input type=hidden name=delete_post_id value={p["id"]}><button class=btn.red style=padding:5px;font-size:0.8rem;margin-left:10px>Delete</button></form>' if is_admin else ''
        posts_html += f"<div class=card><b>{p['name']}</b>: {p['text']}{img_html}<div style=margin-top:8px><form method=POST style='display:inline'><input type=hidden name=like_post_id value={p['id']}><button class=like-btn>🩷 {likes_count}</button></form>{delete_btn}</div><div class=comment-box><b>Comments:</b>{comments_html}<form method=POST enctype=multipart/form-data><input type=hidden name=comment_post_id value={p['id']}><input name=comment_text placeholder='Write comment...' required style=width:75%;display:inline-block><button class='btn gray' style=width:23%;display:inline-block>Send</button></form></div></div>"
    return render_template_string(BASE, title="Community", header=Markup(get_header(nickname,user)), content=Markup(f"<div class=card><h2>Community</h2><form method=POST enctype=multipart/form-data><textarea name=post id=post placeholder='Whats on your mind?' required></textarea><input type=file name=post_image accept=image/*><button class=btn>Post</button><input type=hidden name=new_post value=1></form></div>{posts_html}"), timer_script="")

@app.route('/friends', methods=["GET","POST"])
@login_required
def friends(nickname, user):
    with DBSession() as db:
        if request.method=="POST":
            if "send_request" in request.form:
                f = request.form["send_request"]
                # Prevent duplicate request
                exists = db.execute(sa.text("SELECT id FROM friend_requests WHERE from_nickname=:f AND to_nickname=:t"), {"f": nickname, "t": f}).scalar()
                if not exists:
                    db.execute(sa.text("INSERT INTO friend_requests (from_nickname, to_nickname) VALUES (:f, :t)"), {"f": nickname, "t": f})
                db.commit()
            elif "accept_user" in request.form:
                from_user = request.form["accept_user"]
                if from_user not in user['friends']: user['friends'].append(from_user)
                db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(user['friends']), "u": nickname})
                from_friends = json.loads(db.execute(sa.text("SELECT friends FROM users WHERE nickname=:u"), {"u": from_user}).scalar() or '[]')
                if nickname not in from_friends: from_friends.append(nickname)
                db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(from_friends), "u": from_user})
                db.execute(sa.text("DELETE FROM friend_requests WHERE from_nickname=:f AND to_nickname=:t"), {"f": from_user, "t": nickname})
                db.commit()
            elif "decline_user" in request.form:
                from_user = request.form["decline_user"]
                db.execute(sa.text("DELETE FROM friend_requests WHERE from_nickname=:f AND to_nickname=:t"), {"f": from_user, "t": nickname})
                db.commit()

        incoming = db.execute(sa.text("SELECT * FROM friend_requests WHERE to_nickname=:u AND status='Pending'"), {"u": nickname}).mappings().all()
        all_users = db.execute(sa.text("SELECT * FROM users WHERE nickname!=:u"), {"u": nickname}).mappings().all()

        incoming_list = []
        for r in incoming:
            name = db.execute(sa.text('SELECT name FROM users WHERE nickname=:u'), {'u': r['from_nickname']}).scalar()
            incoming_list.append({"id": r['from_nickname'], "name": name})

        friends_names = []
        for f in user['friends']:
            name = db.execute(sa.text('SELECT name FROM users WHERE nickname=:u'), {'u': f}).scalar()
            friends_names.append({"nickname": f, "name": name})

    incoming_html = "".join([f"<div class=card><b>{r['name']}</b><div style='display:flex;gap:5px'><form method=POST><input type=hidden name=accept_user value={r['id']}><button class=btn>Accept</button></form><form method=POST><input type=hidden name=decline_user value={r['id']}><button class='btn red'>Decline</button></form></div></div>" for r in incoming_list])
    all_users_html = "".join([f"<div class=card><b>{u['name']}</b><form method=POST><input type=hidden name=send_request value={u['nickname']}><button class=btn.blue>Add Friend</button></form></div>" for u in all_users if u['nickname'] not in user['friends']])
    friends_html = "".join([f"<a class=friend-card href=/dm/{f['nickname']}><div class=friend-avatar>{f['name'][0].upper()}</div><div style='flex:1'><b>{f['name']}</b></div><button class='btn blue' style='width:auto;padding:8px 15px'>Message</button></a>" for f in friends_names]) or "<p>No friends yet</p>"
    return render_template_string(BASE, title="Friends", header=Markup(get_header(nickname,user)), content=Markup(f"<div class=card><h2>Friend Requests</h2>{incoming_html or '<p>No requests</p>'}</div><div class=card><h2>My Friends</h2>{friends_html}</div><div class=card><h2>All Users</h2>{all_users_html}</div>"), timer_script="")

@app.route('/dm')
@login_required
def dm_list(nickname, user):
    with DBSession() as db:
        db.execute(sa.text("UPDATE dms SET read=TRUE WHERE to_nickname=:u"), {"u": nickname})
        db.commit()
        friends_html = ""
        for f in user['friends']:
            name = db.execute(sa.text("SELECT name FROM users WHERE nickname=:u"), {"u": f}).scalar()
            initial = name[0].upper() if name else "?"
            friends_html += f"<a class=friend-card href=/dm/{f}><div class=friend-avatar>{initial}</div><div style='flex:1'><b>{name}</b></div><button class='btn blue' style='width:auto;padding:8px 15px'>Message</button></a>"
    return render_template_string(BASE, title="Messages", header=Markup(get_header(nickname,user)), content=Markup(f"<div class=card><h2>My Friends</h2>{friends_html or '<p>Add friends to start chat</p>'}</div>"), timer_script="")

@app.route('/dm/<to_nickname>', methods=["GET","POST"])
@login_required
def dm_chat(nickname, user, to_nickname):
    if to_nickname not in user['friends']: return redirect("/dm")
    with DBSession() as db:
        if request.method=="POST":
            image_url = ""
            if 'msg_image' in request.files and request.files['msg_image'].filename!= '':
                # import cloudinary.uploader
                # res = cloudinary.uploader.upload(request.files['msg_image'])
                # image_url = res['secure_url']
                pass

            db.execute(sa.text("INSERT INTO dms (from_nickname, to_nickname, text, image_url, time, read) VALUES (:f, :t, :txt, :img, :time, FALSE)"),
                       {"f": nickname, "t": to_nickname, "txt": request.form["msg"], "img": image_url, "time": datetime.now(NIGERIA_TZ).strftime("%H:%M")})
            db.commit(); return redirect(f"/dm/{to_nickname}")

        db.execute(sa.text("UPDATE dms SET read=TRUE WHERE from_nickname=:t AND to_nickname=:u"), {"t": to_nickname, "u": nickname})

        chat = db.execute(sa.text("SELECT * FROM dms WHERE (from_nickname=:u AND to_nickname=:t) OR (from_nickname=:t AND to_nickname=:u) ORDER BY id"),
                          {"u": nickname, "t": to_nickname}).mappings().all()
        to_name = db.execute(sa.text("SELECT name FROM users WHERE nickname=:u"), {"u": to_nickname}).scalar()

        msgs = ""
        for m in chat:
            align_class = "chat-me" if m['from_nickname'] == nickname else "chat-other"
            img_html = f"<br><img src={m['image_url']} style='max-width:200px;border-radius:8px'>" if m['image_url'] else ""
            msgs += f"<div class='chat-msg {align_class}'><b>{m['text']}</b>{img_html} <small>{m['time']}</small></div>"

    content = f"<div class=card><div class=chat-box>{msgs or '<p style=text-align:center;color:gray>No messages yet. Start chatting!</p>'}</div><form method=POST enctype=multipart/form-data><input id=msg name=msg placeholder='Type message...' required style=width:100%;display:block><input type=file name=msg_image accept=image/*><button class=btn.gray style=margin-top:8px>Send</button></form></div>"
    return render_template_string(BASE, title=f"Chat with {to_name}", header=Markup(get_header(nickname,user)), content=Markup(content), timer_script="")

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
    my_groups_html = "".join([f"<a class=friend-card href=/group/{g['id']}><div class=friend-avatar>👥</div><div style='flex:1'><b>{g['name']}</b><br><small>{len(json.loads(g['members']))} members</small></div><button class='btn blue' style='width:auto;padding:8px 15px'>Open</button></a>" for g in my_groups if nickname in json.loads(g['members'])])
    create_form = f"<div class=card><h3>Create Group</h3><form method=POST><input name=group_name placeholder='Group Name' required><button name=create_group class=btn>Create</button></form></div>"
    content = f"{create_form}<div class=card><h3>My Groups</h3>{my_groups_html or '<p>No groups yet</p>'}</div>"
    return render_template_string(BASE, title="Groups", header=Markup(get_header(nickname,user)), content=Markup(content), timer_script="")
# ADD THIS TO PART 1: UPDATE get_unread_counts to include groups
def get_unread_counts(nickname, user):
    if not user: return {"dm": 0, "comm": 0, "groups": 0}
    with DBSession() as db:
        dm_unread = db.execute(sa.text("SELECT COUNT(*) FROM dms WHERE to_nickname=:u AND read=FALSE"), {"u": nickname}).scalar()
        last_seen_comm = user['last_seen'].get('community', '2000-01-01 00:00:00')
        comm_unread = db.execute(sa.text("SELECT COUNT(*) FROM posts WHERE created_at > :t"), {"t": last_seen_comm}).scalar()

        # NEW: Group unread
        group_unread = 0
        my_groups = db.execute(sa.text("SELECT id, messages FROM groups")).mappings().all()
        for g in my_groups:
            if nickname in json.loads(g['members']):
                last_seen_g = user['last_seen'].get(f'group_{g["id"]}', '2000-01-01 00:00:00')
                messages = json.loads(g['messages'])
                # Count messages after last_seen
                group_unread += len([m for m in messages if m.get('time', '00:00') > last_seen_g[-5:]])
    return {"dm": dm_unread, "comm": comm_unread, "groups": group_unread}

# UPDATE get_header to show group bell
def get_header(nickname,user, show_nav=False):
    if not user: return ""
    unread = get_unread_counts(nickname, user)
    nav_html = ""
    if show_nav:
        nav_html = f"""<div class="nav">
        <a href="/main">🏠 Home</a>
        <a href="/exam">✍️ CBT</a>
        <a href="/lessons">🎓 Lessons</a>
        <a href="/community">🌍 Community {f'<span class=bell>{unread["comm"]}</span>' if unread['comm']>0 else ''}</a>
        <a href="/groups">👥 Groups {f'<span class=bell>{unread["groups"]}</span>' if unread['groups']>0 else ''}</a>
        <a href="/dm">💬 DM {f'<span class=bell>{unread["dm"]}</span>' if unread['dm']>0 else ''}</a>
        <a href="/friends">👤 Friends</a>
        <a href="/profile">📊 Profile</a>
        <a href="/admin">🔒 Admin</a>
        <a href="/logout">🚪 Logout</a>
        </div>"""
    verified = '<span class=badge>✓ Verified</span>' if user.get('is_verified') else ""
    return f"""<div class="header"><a href="/main" class="exit-btn">⬅️</a><h1>MOTIZ E-LEARNING INSTITUTION {verified}</h1><button class="theme-btn" onclick="document.body.classList.toggle('dark')">🌙</button></div>{nav_html}"""

@app.route('/group/<int:gid>', methods=["GET","POST"])
@login_required
def group_chat(nickname, user, gid):
    with DBSession() as db:
        group = db.execute(sa.text("SELECT * FROM groups WHERE id=:id"), {"id": gid}).mappings().first()
        if not group or nickname not in json.loads(group['members']): return redirect("/groups")
        members = json.loads(group['members']); messages = json.loads(group['messages']); is_creator = group['creator']==nickname

        # Mark group as seen
        last_seen = user['last_seen']
        last_seen[f'group_{gid}'] = str(datetime.now(NIGERIA_TZ))
        db.execute(sa.text("UPDATE users SET last_seen=:l WHERE nickname=:u"), {"l": json.dumps(last_seen), "u": nickname})

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

        msgs = ""
        for m in messages:
            align_class = "chat-me" if m['user'] == user["name"] else "chat-other"
            msgs += f"<div class='chat-msg {align_class}'><b>{m['user']}:</b> {m['text']} <small>{m['time']}</small></div>"

        all_users = db.execute(sa.text("SELECT nickname,name FROM users WHERE nickname!=:u"), {"u": nickname}).mappings().all()
        friends_options = "".join([f"<option value={u['nickname']}>{u['name']}</option>" for u in all_users if u['nickname'] not in members])

        members_html = ""
        for m in members:
            name = db.execute(sa.text('SELECT name FROM users WHERE nickname=:u'), {'u': m}).scalar()
            remove_btn = f'<form method=POST style=display:inline><input type=hidden name=remove_member value={m}><button class=btn.red style=padding:2px 5px;font-size:0.7rem>Remove</button></form>' if is_creator and m!=nickname else ''
            members_html += f"<li>{name} {remove_btn}</li>"

    add_member_form = f"<form method=POST><select name=add_member required><option value=''>Add Member</option>{friends_options}</select><button class=btn.gray>Add</button></form>" if is_creator else "<p><i>Only group creator can add/remove members</i></p>"
    rename_form = f"<form method=POST><input name=new_name placeholder=New Group Name required><button name=rename class=btn.orange>Rename</button></form>" if is_creator else ""
    content = f"<div class=card><h2>{group['name']}</h2>{rename_form}{add_member_form}<h4>Members:</h4><ul>{members_html}</ul></div>"
    content += f"<div class=card><div class=chat-box>{msgs or '<p>No messages yet</p>'}</div><form method=POST><input id=msg name=msg placeholder='Type message...' required style=width:70%;display:inline-block><button name=send_msg class=btn.gray style=width:28%;display:inline-block>Send</button></form></div>"
    return render_template_string(BASE, title=group['name'], header=Markup(get_header(nickname,user)), content=Markup(content), timer_script="")

@app.route('/lessons')
@login_required
def lessons(nickname, user):
    try:
        if not user.get('lesson_expiry'):
            expired = True
        else:
            expired = date.today() > datetime.strptime(user['lesson_expiry'], "%Y-%m-%d").date()
        if user.get('free_days', 0) > 0: expired = False
    except: expired = True

    if expired: return redirect("/request-payment/lessons")

    access_banner = f"<div class=success>✅ Access Active till {user['lesson_expiry']}</div>"

    with DBSession() as db:
        lessons = db.execute(sa.text("SELECT * FROM lessons WHERE class=:c AND dept=:d"), {"c": user['class'], "d": user.get('dept','')}).mappings().all()
    lessons_html = ""
    for l in lessons:
        audio_html = f"<audio controls style='width:100%;margin-top:8px'><source src={l['audio_url']}></audio>" if l['audio_url'] else ""
        lessons_html += f"<div class=card><h3>📖 {l['subject']} - {l['title']}</h3><p>{l['notes']}</p>{audio_html}<small>Posted: {l['date']}</small></div>"
    if not lessons_html: lessons_html = "<p>No lessons for your class yet</p>"
    return render_template_string(BASE, title="Lessons", header=Markup(get_header(nickname,user)), content=Markup(f"<div class=card><h2>My Lessons</h2>{access_banner}<p>Free Days Left: {user.get('free_days', 0)}</p></div>{lessons_html}"), timer_script="")

@app.route('/admin', methods=["GET","POST"])
@login_required
def admin(nickname, user):
    global ADMIN_PASS
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
                if req["type"] == "questions":
                    db.execute(sa.text("UPDATE users SET q_cycle='paid' WHERE nickname=:u"), {"u": req["nickname"]})
                if req["type"] == "lessons":
                    expiry = str(date.today() + timedelta(days=30))
                    db.execute(sa.text("UPDATE users SET lesson_expiry=:d WHERE nickname=:u"), {"d": expiry, "u": req["nickname"]})
                db.execute(sa.text("UPDATE payments SET status='Verified' WHERE id=:id"), {"id": request.form["verify_id"]})
                db.commit(); error = "<div class=success>Payment Verified & Saved for 30 Days</div>"
            if "deny_id" in request.form: db.execute(sa.text("UPDATE payments SET status='Denied' WHERE id=:id"), {"id": request.form["deny_id"]}); db.commit(); error = "<div class=error>Payment Denied</div>"
            if "change_pass" in request.form:
                if request.form["old_pass"]!= ADMIN_PASS: error = "<div class=error>Old password is wrong</div>"
                else: ADMIN_PASS = request.form["new_pass"]; set_setting("admin_pass", ADMIN_PASS); error = "<div class=success>Admin Password Changed & Saved</div>"

            if "add_lesson" in request.form:
                audio_url = ""
                if 'lesson_audio' in request.files and request.files['lesson_audio'].filename!= '':
                    # import cloudinary.uploader
                    # res = cloudinary.uploader.upload(request.files['lesson_audio'], resource_type="video")
                    # audio_url = res['secure_url']
                    pass
                db.execute(sa.text("INSERT INTO lessons (class, dept, subject, title, notes, audio_url, date) VALUES (:c, :d, :s, :t, :n, :a, :date)"),{"c": request.form['lesson_class'], "d": request.form.get('lesson_dept',''), "s": request.form['lesson_subject'], "t": request.form['lesson_title'], "n": request.form['lesson_notes'], "a": audio_url, "date": str(date.today())}); db.commit(); error = "<div class=success>Lesson Note Posted & Saved</div>"

            if "add_question" in request.form:
                cls = request.form['admin_class']; dept = request.form.get('admin_dept_hidden',''); sub = request.form['admin_subject']; key = f"{cls}_{dept}_{sub}" if dept else f"{cls}_{sub}"
                db.execute(sa.text("INSERT INTO questions (key, q, options, ans) VALUES (:k, :q, :o, :a)"),{"k": key, "q": request.form["q"], "o": json.dumps([request.form["a"],request.form["b"],request.form["c"],request.form["d"]]), "a": request.form["ans"]}); db.commit(); error = f"<div class=success>Question Added for {sub}</div>"

            if "new_notice" in request.form:
                notice = {"title": request.form["notice_title"], "text": request.form["new_notice"], "created_at": str(datetime.now(NIGERIA_TZ))}
                NOTICES.append(notice); set_setting("notices", json.dumps(NOTICES)); error = "<div class=success>Notice Posted</div>"
            if "delete_notice_id" in request.form:
                del_id = int(request.form["delete_notice_id"])
                NOTICES.pop(del_id); set_setting("notices", json.dumps(NOTICES)); error = "<div class=success>Notice Deleted</div>"

    js = Markup(f"""<script>
const subjects = {json.dumps(SUBJECTS)};
function updateDept(){{
    let c = document.getElementById('admin_class').value;
    let dDiv = document.getElementById('admin_dept_div');
    dDiv.innerHTML = '';
    if(['SS1','SS2','SS3'].includes(c)){{
        dDiv.innerHTML = '<button type=button class=dept-btn onclick="loadSubjectsForDept(\''+c+'\',\'Science\')">🔬 Science</button><button type=button class=dept-btn onclick="loadSubjectsForDept(\''+c+'\',\'Commercial\')">💼 Commercial</button><button type=button class=dept-btn onclick="loadSubjectsForDept(\''+c+'\',\'Art\')">🎨 Art</button>';
    }} else {{
        loadSubjectsForDept(c, '');
    }}
}}
function loadSubjectsForDept(c, d){{
    let key = d? c+'_'+d : c;
    let grid = document.getElementById('subject_grid');
    grid.innerHTML = '';
    document.getElementById('admin_dept_hidden').value = d;
    (subjects[key] || []).forEach(sub => {{
        grid.innerHTML += `<button type=button class="subject-btn" onclick="selectSubject('${{sub}}', this)">${{sub}}</button>`;
    }});
}}
function selectSubject(sub, btn){{
    document.getElementById('admin_subject').value = sub;
    document.querySelectorAll('.subject-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
}}
</script>""")

    with DBSession() as db:
        pending_reqs = db.execute(sa.text("SELECT * FROM payments WHERE status='Pending'")).mappings().all()

    pending_html = "".join([f"<div class='card'><b>{r['name']}</b> for {r['type']}<br><small>Bank: {r.get('bank_used','N/A')} | Acc Name: {r.get('account_name','N/A')}</small><div style='display:flex;gap:5px'><form method=POST style='flex:1'><input type=hidden name=verify_id value={r['id']}><button class=btn>Verify 30 Days</button></form><form method=POST style='flex:1'><input type=hidden name=deny_id value={r['id']}><button class='btn red'>Deny</button></form></div></div>" for r in pending_reqs])

    # FIX: Added subject_grid div that was missing
    subject_grid = "<div id=subject_grid class=subject-grid><p style=color:gray>Select Class then Department</p></div>"

    form = f'\
<div class="card"><h2>Admin Panel</h2>{error}</div>\
<div class="card"><h2>Pending Payments</h2>{pending_html or "<p>No pending payments</p>"}</div>\
<div class="card"><h2>Change Admin Password</h2><form method="POST"><input type="password" name="old_pass" placeholder="Current Password" required><input type="password" name="new_pass" placeholder="New Password" required><button name="change_pass" class="btn orange">Change Password</button></form></div>\
<div class="card"><h2>Upload Lesson Note + Audio</h2><form method="POST" enctype=multipart/form-data>\
<label>Select Class</label><select name="lesson_class" required><option value="">Select Class</option>{"".join([f"<option>{c}</option>" for c in CLASSES])}</select>\
<label>Department</label><input name=lesson_dept placeholder="Science/Commercial/Art or leave blank for JSS">\
<label>Subject</label><input name=lesson_subject placeholder="Subject" required>\
<input name="lesson_title" placeholder="Lesson Title" required>\
<textarea name="lesson_notes" rows="8" placeholder="Paste lesson notes here..." required></textarea>\
<label>Upload Audio/Video</label><input type=file name=lesson_audio accept=audio/*,video/*>\
<button name="add_lesson" class="btn blue">Post Lesson</button></form></div>\
<div class="card"><h2>Post General Notice</h2><form method="POST">\
<input name="notice_title" placeholder="Notice Heading" required>\
<textarea name="new_notice" placeholder="Notice details" required></textarea>\
<button class="btn orange">Post Notice</button></form></div>\
<div class="card"><h2>Add Single Question</h2><form method="POST">\
<label>Select Class</label><select name="admin_class" id="admin_class" onchange="updateDept()" required><option value="">Select Class</option>{"".join([f"<option>{c}</option>" for c in CLASSES])}</select>\
<div id="admin_dept_div"></div><input type=hidden name=admin_dept_hidden id=admin_dept_hidden>\
<label>Select Subject - Click Button</label>{subject_grid}<input type=hidden name=admin_subject id=admin_subject required>\
<textarea name="q" placeholder="Question" required></textarea>\
<input name="a" placeholder="Option A" required><input name="b" placeholder="Option B" required><input name="c" placeholder="Option C" required><input name="d" placeholder="Option D" required>\
<label>Correct Answer</label><select name=ans required><option value="">Select Correct</option><option value=A>A</option><option value=B>B</option><option value=C>C</option><option value=D>D</option></select>\
<button name="add_question" class="btn">Post Question</button></form></div>'
    return render_template_string(BASE, title="Admin", header=Markup(get_header(nickname,user)), content=Markup(form), timer_script=js)

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
