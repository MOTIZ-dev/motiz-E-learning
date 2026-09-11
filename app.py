from flask import Flask, render_template_string, request, redirect, session
from markupsafe import Markup
from datetime import date, datetime, timedelta
import random, json, os, urllib.parse
from functools import wraps
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import pytz

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', "motiz_secret_key_2026_v21")
app.config['PROPAGATE_EXCEPTIONS'] = True

# ====== RENDER DATABASE CONNECTION ======
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise Exception("DATABASE_URL environment variable is not set")

engine = sa.create_engine(DATABASE_URL)
DBSession = sessionmaker(bind=engine)

# ====== SETTINGS - FINAL LOCKED ======
PALMPAY_ACCOUNT = "8908025244"
PALMPAY_NAME = "HAMZAT KOLADE AJIMOTI"
PALMPAY_BANK = "PALMPAY"
LESSON_PRICE = 1000
QUESTION_PRICE = 500
ADMIN_PASS = os.environ.get('ADMIN_PASS', "24434")
FREE_Q = 30 # 30 FREE QUESTIONS
PAID_Q = 70 # 70 PAID QUESTIONS
TIMER_PER_QUESTION = 60 # 1 MINUTE PER QUESTION
NIGERIA_TZ = pytz.timezone('Africa/Lagos')

# ====== YOUR EXACT SUBJECT LIST ======
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

# ====== CREATE TABLES + INITIAL DATA ======
def init_db():
    with engine.connect() as conn:
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, nickname TEXT UNIQUE, name TEXT, password TEXT, class TEXT, dept TEXT, q_cycle TEXT DEFAULT 'free', q_used INTEGER DEFAULT 0, lesson_expiry DATE, correct INTEGER DEFAULT 0, wrong INTEGER DEFAULT 0, friends TEXT DEFAULT '[]', referred_by TEXT DEFAULT NULL, referral_count INTEGER DEFAULT 0, free_days INTEGER DEFAULT 0, is_verified BOOLEAN DEFAULT FALSE);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS payments (id SERIAL PRIMARY KEY, nickname TEXT, name TEXT, type TEXT, status TEXT, bank_used TEXT, account_name TEXT, date_paid TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS friend_requests (id SERIAL PRIMARY KEY, from_nickname TEXT, to_nickname TEXT, status TEXT DEFAULT 'Pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, nickname TEXT, name TEXT, text TEXT, likes TEXT DEFAULT '[]', comments TEXT DEFAULT '[]', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS dms (id SERIAL PRIMARY KEY, from_nickname TEXT, to_nickname TEXT, text TEXT, time TEXT, read_by TEXT DEFAULT '[]');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS groups (id SERIAL PRIMARY KEY, name TEXT, creator TEXT, members TEXT DEFAULT '[]', messages TEXT DEFAULT '[]');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS lessons (id SERIAL PRIMARY KEY, class TEXT, dept TEXT, subject TEXT, title TEXT, notes TEXT, date TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS questions (id SERIAL PRIMARY KEY, key TEXT, q TEXT, options TEXT, ans TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS referrals (id SERIAL PRIMARY KEY, referrer TEXT, referred TEXT, paid BOOLEAN DEFAULT FALSE, bonus_given BOOLEAN DEFAULT FALSE);"))
        conn.commit()

        q_count = conn.execute(sa.text("SELECT COUNT(*) FROM questions")).scalar()
        if q_count == 0:
            # 10 sample questions per subject so 30 free can work
            for cls in ["JSS1","JSS2","JSS3"]:
                for sub in JSS_SUBJECTS:
                    key = f"{cls}_{sub}"
                    for i in range(10):
                        conn.execute(sa.text("INSERT INTO questions (key,q,options,ans) VALUES (:k,:q,:o,:a)"),{"k":key,"q":f"Sample Q{i+1} for {sub}: What is 2+2?","o":json.dumps(["3","4","5","6"]),"a":"4"})
            for cls in ["SS1","SS2","SS3"]:
                for dept in ["Science","Commercial","Art"]:
                    for sub in SUBJECTS[f"{cls}_{dept}"]:
                        key = f"{cls}_{dept}_{sub}"
                        for i in range(10):
                            conn.execute(sa.text("INSERT INTO questions (key,q,options,ans) VALUES (:k,:q,:o,:a)"),{"k":key,"q":f"Sample Q{i+1} for {sub}: Function of mitochondria?","o":json.dumps(["Protein synthesis","Cell respiration","Cell division","Waste removal"]),"a":"Cell respiration"})
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

def get_user():
    nickname = session.get("nickname")
    if not nickname: return None, None
    with DBSession() as db:
        user = db.execute(sa.text("SELECT * FROM users WHERE nickname=:u"), {"u": nickname}).mappings().first()
        if user:
            user = dict(user)
            user['friends'] = json.loads(user.get('friends', '[]'))
        return nickname, user

def delete_old_posts_and_notices():
    global NOTICES
    with DBSession() as db:
        cutoff = datetime.now(NIGERIA_TZ) - timedelta(hours=24)
        db.execute(sa.text("DELETE FROM posts WHERE created_at < :c"), {"c": cutoff})
        db.commit()
    new_notices = []
    for n in NOTICES:
        try:
            notice_time = datetime.fromisoformat(n.get('created_at').replace('Z','+00:00'))
            if notice_time > cutoff:
                new_notices.append(n)
        except:
            new_notices.append(n) # keep old notices if date format is bad
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

# ====== BASE HTML ======
BASE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title><style>:root{--bg:#f0f2f5;--card:white;--text:#333;--primary:#0f3460} body.dark{--bg:#121212;--card:#1e1e1e;--text:#eee}
body{font-family:Segoe UI;background:var(--bg);color:var(--text);margin:0;padding:0;padding-bottom:80px}
.header{background:var(--primary);color:white;padding:10px;text-align:center;position:fixed;top:0;width:100%;z-index:1000;display:flex;justify-content:space-between;align-items:center}
.header h1{margin:0;font-size:0.85rem;flex:1;text-align:center;line-height:1.1;white-space:nowrap}
.theme-btn{border:none;background:transparent;color:white;font-size:1.3rem;cursor:pointer;margin-right:10px}
.exit-btn{background:#e94560;color:white;border:none;padding:5px 10px;border-radius:5px;text-decoration:none;font-size:0.8rem;margin-left:10px}
.nav{display:flex;gap:5px;background:#16213e;padding:5px;flex-wrap:wrap;position:fixed;top:50px;width:100%;overflow-x:auto;z-index:999}
.nav a{color:white;text-decoration:none;padding:5px 8px;border-radius:10px;border:1px solid #fff3;font-size:0.8rem}
.container{padding:10px;padding-top:105px}
.card{background:var(--card);padding:12px;margin:8px 0;border-radius:10px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}
.btn{background:#28a745;color:white;padding:12px 15px;text-decoration:none;border-radius:8px;display:block;margin:8px 0;text-align:center;font-weight:bold;border:none;width:100%;cursor:pointer}
.btn.red{background:#e94560}.btn.blue{background:#2196f3}.btn.orange{background:#ff9800}.btn.gray{background:#6c757d;font-size:0.9rem;padding:8px}
input,select,textarea{width:100%;padding:10px;margin:5px 0;border-radius:5px;border:1px solid #ccc;box-sizing:border-box;font-size:1rem;background:var(--card);color:var(--text)}
.success{color:green;background:#d4edda;padding:10px;border-radius:5px}.error{color:red;background:#f8d7da;padding:10px;border-radius:5px}
.badge{background:#28a745;color:white;padding:2px 6px;border-radius:10px;font-size:0.7rem;margin-left:5px}
.notice-title{font-size:1.1rem;font-weight:bold;color:var(--primary);margin-bottom:5px}
.chat-msg{display:flex;margin:8px 0}.chat-msg.me{justify-content:flex-end}.chat-msg.other{justify-content:flex-start}
.bubble{padding:10px 15px;border-radius:18px;max-width:70%}.me.bubble{background:#2196f3;color:white;border-bottom-right-radius:5px}
.other.bubble{background:#e0e0e0;color:#333;border-bottom-left-radius:5px}body.dark.other.bubble{background:#333;color:#eee}
.friend-card{display:flex;align-items:center;gap:10px;padding:12px;background:var(--card);border-radius:10px;margin:8px 0;text-decoration:none;color:var(--text)}
.friend-avatar{width:45px;height:45px;border-radius:50%;background:var(--primary);color:white;display:flex;align-items:center;justify-content:center;font-weight:bold}
.notification{position:absolute;top:-5px;right:-5px;background:red;color:white;border-radius:50%;width:18px;height:18px;font-size:0.7rem;display:flex;align-items:center;justify-content:center}
.readonly-box{width:100%;padding:12px;background:#eee;border:1px dashed #999;font-size:1.1rem;font-weight:bold;text-align:center;user-select:all}
</style></head><body>{{header}}<div class="container">{{content}}</div><script>{{timer_script}}</script></body></html>"""

def get_header(nickname,user, show_nav=True):
    if not user: return ""
    exit_html = '<a href="/main" class="exit-btn">⬅️</a>'
    theme_html = '<button class="theme-btn" onclick="document.body.classList.toggle(\'dark\')">🌙</button>'
    verified = '<span class=badge>✓ Verified</span>' if user.get('is_verified') else ""
    nav_html = """<div class="nav"><a href="/main">🏠 Home</a><a href="/exam">✍️ CBT</a><a href="/lessons">🎓 Lessons</a><a href="/community">🌍 Community</a><a href="/chat">💬 Chat</a><a href="/me">👤 Me</a></div>""" if show_nav else ""
    return f"""<div class="header">{exit_html}<h1>MOTIZ E-LEARNING {verified}</h1>{theme_html}</div>{nav_html}"""

@app.route('/')
def splash():
    return render_template_string("""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Welcome</title><meta http-equiv="refresh" content="10;url=/login">
<style>body{margin:0;background:linear-gradient(135deg,#0f3460,#16213e);color:white;font-family:Segoe UI;display:flex;justify-content:center;align-items:center;height:100vh;flex-direction:column;text-align:center;overflow:hidden;position:relative}
.logo{font-size:2.8rem;font-weight:bold;animation:glow 2s ease-in-out infinite alternate;line-height:1.2;z-index:10;margin-top:120px}
.subtext{font-size:1.1rem;margin-top:10px;opacity:0.9;z-index:10}
.progress-bar{width:200px;height:8px;background:#fff3;border-radius:10px;overflow:hidden;margin-top:20px}
.progress-fill{height:100%;width:0%;background:white;animation:load 10s linear forwards}
@keyframes load{0%{width:0%}100%{width:100%}}
@keyframes glow{from{text-shadow:0 0 10px #fff}to{text-shadow:0 0 30px #2196f3}}
.bulb{position:absolute;top:35%;left:50%;transform:translate(-50%,-50%);font-size:4rem;z-index:10}
</style></head><body>
<div class="bulb">📖</div>
<div class="logo">MOTIZ E-LEARNING INSTITUTION</div><div class="subtext">Learn. Practice. Excel.</div><div class="progress-bar"><div class="progress-fill"></div></div></body></html>""")

@app.route('/register', methods=["GET","POST"])
def register():
    if get_user()[1]: return redirect("/main")
    error = "";
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
    pinned_html = ""
    if PINNED_NOTICE:
        try: pin = json.loads(PINNED_NOTICE); pinned_html = f"<div class='card' style='border:2px solid gold'><div class=notice-title>📌 {pin['title']}</div>{pin['text']}</div>"
        except: pinned_html = f"<div class='card' style='border:2px solid gold'><b>📌 PINNED:</b> {PINNED_NOTICE}</div>"
    notices_html = "".join([f"<div class='card'><div class=notice-title>📢 {n['title']}</div>{n['text']}</div>" for n in NOTICES])
    return render_template_string(BASE, title="Home", header=Markup(get_header(nickname,user, show_nav=True)), content=Markup(f"<div class='card'><h2>Welcome {user['name']}</h2><p><b>Class:</b> {user['class']} {user.get('dept','')}</p></div>{pinned_html}<h3>General Notice</h3>{notices_html}<a class=btn href=/exam>Start CBT Exam</a>"), timer_script="")
@app.route('/logout')
def logout():
    session.clear()
    return redirect("/login")

@app.route('/exam') # AUTO CLASS + SHOW PAYMENT AFTER 30Q
@login_required
def exam(nickname, user):
    key = f"{user['class']}_{user['dept']}" if user['dept'] else user['class']
    subs = SUBJECTS.get(key, [])
    if not subs: return render_template_string(BASE, title="Error", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup("<div class=error>No subjects for your class yet</div>"), timer_script="")

    # IF FREE USER FINISHED 30Q, SHOW PAYMENT IN CBT CENTER
    if user['q_cycle']=="free" and user['q_used'] >= FREE_Q:
        with DBSession() as db: pending = db.execute(sa.text("SELECT * FROM payments WHERE nickname=:u AND type='questions' AND status='Pending'"), {"u": nickname}).scalar()
        if pending:
            content = "<div class=card><h2>⏳ Payment Under Review</h2><p>Admin is verifying your payment. You will get 70 more questions once approved.</p></div>"
        else:
            content = f'<div class=card><h2>🔒 Unlock 70 More Questions</h2><p>You have used all 30 free questions.</p><p><b>Pay &#8358;{QUESTION_PRICE} to continue</b></p><p><b>Bank:</b> {PALMPAY_BANK}<br><b>Account Number:</b><input class=readonly-box readonly value="{PALMPAY_ACCOUNT}"><br><b>Account Name:</b> {PALMPAY_NAME}</p><form method=POST action=/confirm/questions><input name=bank_used placeholder="Bank you used to transfer" required><input name=account_name placeholder="Account Name you used" required><button class=btn>I Have Paid</button></form></div>'
        return render_template_string(BASE, title="CBT Payment", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")

    sub_btns = "".join([f"<a class='btn blue' href=/start/{urllib.parse.quote(key)}/{urllib.parse.quote(s)}>📚 {s}</a>" for s in subs])
    limit_text = f"You have {FREE_Q - user['q_used']} free questions left" if user['q_cycle']=="free" else f"Paid Access: {PAID_Q - (user['q_used'] - FREE_Q)} questions left"
    return render_template_string(BASE, title="CBT", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class='card'><h2>Subjects for {user['class']} {user.get('dept','')}</h2><p>{limit_text}</p>{sub_btns}</div>"), timer_script="")

@app.route('/start/<path:key>/<path:sub>', methods=["GET","POST"])
@login_required
def start(nickname, user, key, sub):
    key = urllib.parse.unquote(key); sub = urllib.parse.unquote(sub)

    # DETERMINE LIMIT: 30 FREE OR 100 TOTAL
    total_limit = FREE_Q if user['q_cycle']=="free" else FREE_Q + PAID_Q
    if user['q_used'] >= total_limit: return redirect("/exam")

    with DBSession() as db: q_list = db.execute(sa.text("SELECT * FROM questions WHERE key=:k"), {"k": f"{key}_{sub}"}).mappings().all()
    if len(q_list) == 0: return render_template_string(BASE, title="Error", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=error>No questions for {sub} yet. Contact Admin</div>"), timer_script="")

    session_key = f"exam_{key}_{sub}"; answers_key = f"answers_{key}_{sub}"
    if request.method == "GET":
        questions = list(q_list); random.shuffle(questions)
        session[session_key] = questions[:total_limit]; session[answers_key] = {}; session['q_index'] = 0

    questions = session.get(session_key, []); answers = session.get(answers_key, {}); q_index = session.get('q_index', 0)

    if request.method == "POST":
        if "save_answer" in request.form and request.form.get("answer"):
            session[answers_key][str(q_index)] = request.form.get("answer"); session.modified = True
        if "next" in request.form:
            if str(q_index) not in answers: session[answers_key][str(q_index)] = "SKIPPED" # Save if user skipped
            session['q_index'] = q_index + 1
        if "prev" in request.form: session['q_index'] = q_index - 1
        if "submit_exam" in request.form: return redirect("/result")
        if "timeout" in request.form: # AUTO MARK WRONG AFTER 60S
            if str(q_index) not in answers: session[answers_key][str(q_index)] = "TIMEOUT" # Only mark timeout if no answer
            session.modified = True
            session['q_index'] = q_index + 1
        return redirect(f"/start/{urllib.parse.quote(key)}/{urllib.parse.quote(sub)}")

    if q_index >= len(questions): return redirect("/result")
    q = questions[q_index]; q['options'] = json.loads(q['options']); saved_ans = answers.get(str(q_index))

    # 60 SECONDS TIMER WITH AUTO SAVE + AUTO SUBMIT - FIXED v2
    timer_js = Markup(f"""let timeLeft = {TIMER_PER_QUESTION};
    const timerEl = document.createElement('div');
    timerEl.style.cssText='position:fixed;top:60px;right:10px;background:#ff9800;color:white;padding:8px 12px;border-radius:8px;font-weight:bold;z-index:1001';
    document.body.appendChild(timerEl);
    let submitted = false;
    function updateTimer(){{
        let m = Math.floor(timeLeft / 60); let s = timeLeft % 60; s = s < 10? '0' + s : s;
        timerEl.innerHTML = '⏰ ' + m + ':' + s;
        if(timeLeft <= 0 &&!submitted){{
            submitted = true;
            let form = document.getElementById('exam_form');
            let input = document.createElement('input');
            input.type = 'hidden'; input.name = 'save_answer'; input.value = '1';
            form.appendChild(input);
            form.submit();
            setTimeout(()=>{{if(!submitted){{document.getElementById('timeout_form').submit();}}}}, 200);
        }}
        timeLeft--;
    }}
    updateTimer(); setInterval(updateTimer, 1000);""")

    options_html = "".join([f"<label style='display:block;padding:10px;margin:8px 0;background:var(--bg);border-radius:8px'><input type=radio name=answer value='{opt}' {'checked' if saved_ans==opt else ''}> {opt}</label>" for opt in q['options']])
    prev_btn = f"<button name=prev class='btn gray' {'disabled' if q_index==0 else ''}>⬅️ Prev</button>" if q_index > 0 else ""
    next_btn = f"<button name=next class='btn blue'>Next ➡️</button>" if q_index < len(questions)-1 else f"<button name=submit_exam class='btn orange'>Submit Exam</button>"

    content = f"<div class='card'><h2>{sub}</h2><h3>Question {q_index+1} of {len(questions)}</h3><p><b>{q['q']}</b></p>\
    <form method=POST id=exam_form>{options_html}<div style='display:flex;gap:10px'>{prev_btn}{next_btn}</div></form>\
    <form method=POST id=timeout_form style=display:none><input type=hidden name=timeout value=1></form></div>"

    return render_template_string(BASE, title=sub, header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script=timer_js)

@app.route('/result')
@login_required
def result(nickname, user):
    try: session_key = [k for k in session.keys() if k.startswith('exam_')][0]; answers_key = [k for k in session.keys() if k.startswith('answers_')][0]
    except: return redirect("/exam")
    questions = session.get(session_key, []); answers = session.get(answers_key, {}); correct = 0; result_html = ""
    for i, q in enumerate(questions):
        q['options'] = json.loads(q['options']); user_ans = answers.get(str(i))
        if user_ans == q['ans']: correct += 1
        result_html += f"<div class='card'><h4>Q{i+1}: {q['q']}</h4><p><b>Your Answer:</b> {user_ans or 'Not Answered'}</p><p><b>Correct Answer:</b> {q['ans']}</p></div>"
    total = len(questions); wrong = total - correct
    with DBSession() as db: db.execute(sa.text("UPDATE users SET q_used=q_used+:t, correct=correct+:c, wrong=wrong+:w WHERE nickname=:u"), {"t": total, "c": correct, "w": wrong, "u": nickname}); db.commit()
    percent = round((correct/total)*100, 1) if total>0 else 0; grade = "A" if percent>=70 else "B" if percent>=60 else "C" if percent>=50 else "F"
    session.pop(session_key, None); session.pop(answers_key, None)
    return render_template_string(BASE, title="Result", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class='card'><h2>🎉 Your Result</h2><p><b>Score:</b> {correct}/{total}</p><p><b>Percentage:</b> {percent}%</p><p><b>Grade:</b> {grade}</p></div>{result_html}<a class=btn href=/exam>Start New Exam</a>"), timer_script="")

@app.route('/confirm/<t>', methods=["POST"])
@login_required
def confirm(nickname, user, t):
    with DBSession() as db: db.execute(sa.text("INSERT INTO payments (nickname, name, type, status, bank_used, account_name, date_paid) VALUES (:u, :n, :t, 'Pending', :b, :a, :d)"), {"u": nickname, "n": user["name"], "t": t, "b": request.form["bank_used"], "a": request.form["account_name"], "d": str(date.today())}); db.commit()
    return render_template_string(BASE, title="Sent", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup("<div class='card'><h2>✅ Request Sent</h2><p>Admin will verify within 24hrs</p><a class=btn href=/exam>Back to CBT</a></div>"), timer_script="")

@app.route('/lessons')
@login_required
def lessons(nickname, user):
    try: expired = not user.get('lesson_expiry') or date.today() > datetime.strptime(user['lesson_expiry'], "%Y-%m-%d").date()
    except: expired = True
    if expired:
        # SHOW PAYMENT INSIDE LESSONS PAGE - 15 DAYS
        content = f'<div class=card><h2>🔒 Unlock Lessons for 15 Days</h2><p><b>Pay &#8358;{LESSON_PRICE}</b></p><p><b>Bank:</b> {PALMPAY_BANK}<br><b>Account Number:</b><input class=readonly-box readonly value="{PALMPAY_ACCOUNT}"><br><b>Account Name:</b> {PALMPAY_NAME}</p><form method=POST action=/confirm/lessons><input name=bank_used placeholder="Bank you used to transfer" required><input name=account_name placeholder="Account Name you used" required><button class=btn>I Have Paid</button></form></div>'
        return render_template_string(BASE, title="Lessons Payment", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")

    access_banner = f"<div class=success>✅ Access Active till {user['lesson_expiry']}</div>"
    with DBSession() as db:
        lessons = db.execute(sa.text("SELECT * FROM lessons WHERE class=:c ORDER BY id DESC"), {"c": user['class']}).mappings().all()
    lessons_html = "".join([f"<div class=card><h3>📖 {l['subject']} - {l['title']}</h3><p>{l['notes']}</p><small>Posted: {l['date']}</small></div>" for l in lessons])
    if not lessons_html: lessons_html = "<p>No lessons for your class yet</p>"
    return render_template_string(BASE, title="Lessons", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>My Lessons</h2>{access_banner}</div>{lessons_html}"), timer_script="")
@app.route('/community', methods=["GET","POST"])
@login_required
def community(nickname, user):
    with DBSession() as db:
        if request.method=="POST":
            if "new_post" in request.form: db.execute(sa.text("INSERT INTO posts (nickname, name, text, likes, comments) VALUES (:u, :n, :t, '[]', '[]')"),{"u": nickname, "n": user["name"], "t": request.form["post"]})
            elif "delete_post" in request.form:
                pid = request.form["delete_post"]
                owner = db.execute(sa.text("SELECT nickname FROM posts WHERE id=:id"), {"id": pid}).scalar()
                if owner == nickname: db.execute(sa.text("DELETE FROM posts WHERE id=:id"), {"id": pid})
            elif "comment_post_id" in request.form:
                p = db.execute(sa.text("SELECT comments FROM posts WHERE id=:id"), {"id": request.form["comment_post_id"]}).scalar(); comments = json.loads(p); comments.append({"user": user["name"], "text": request.form["comment_text"]})
                db.execute(sa.text("UPDATE posts SET comments=:c WHERE id=:id"), {"c": json.dumps(comments), "id": request.form["comment_post_id"]})
            elif "like_post_id" in request.form:
                p = db.execute(sa.text("SELECT likes FROM posts WHERE id=:id"), {"id": request.form["like_post_id"]}).scalar(); likes = json.loads(p); likes.remove(nickname) if nickname in likes else likes.append(nickname)
                db.execute(sa.text("UPDATE posts SET likes=:l WHERE id=:id"), {"l": json.dumps(likes), "id": request.form["like_post_id"]})
            db.commit(); return redirect("/community")
        posts = db.execute(sa.text("SELECT * FROM posts ORDER BY id DESC")).mappings().all()
    posts_html = ""
    for p in posts:
        likes_count = len(json.loads(p['likes'])); comments_data = json.loads(p['comments']); comments_html = "".join([f'<div><b>{c["user"]}:</b> {c["text"]}</div>' for c in comments_data]) or '<p>No comments</p>'
        delete_btn = f"<form method=POST style='display:inline'><input type=hidden name=delete_post value={p['id']}><button class='btn red' style='padding:3px 8px;font-size:0.7rem'>Delete</button></form>" if p['nickname'] == nickname else ""
        posts_html += f"<div class=card><b>{p['name']}</b>: {p['text']} {delete_btn}<form method=POST><input type=hidden name=like_post_id value={p['id']}><button class=btn.gray>🩷 {likes_count}</button></form>{comments_html}<form method=POST><input type=hidden name=comment_post_id value={p['id']}><input name=comment_text placeholder='Write comment...' required><button class='btn gray'>Send</button></form></div>"
    return render_template_string(BASE, title="Community", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>Community</h2><form method=POST><textarea name=post placeholder='Whats on your mind?' required></textarea><button class=btn>Post</button><input type=hidden name=new_post value=1></form></div>{posts_html}"), timer_script="")

@app.route('/me') # PACKED: PROFILE + CBT STATS + FRIENDS + LOGOUT
@login_required
def me(nickname, user):
    with DBSession() as db:
        incoming = db.execute(sa.text("SELECT * FROM friend_requests WHERE to_nickname=:u AND status='Pending'"), {"u": nickname}).mappings().all()
        all_users = db.execute(sa.text("SELECT * FROM users WHERE nickname!=:u"), {"u": nickname}).mappings().all()
    incoming_html = "".join([f"<div class=card><b>{r['from_nickname']}</b><form method=POST action=/friends><input type=hidden name=accept_user value={r['from_nickname']}><button class=btn>Accept</button></form></div>" for r in incoming])
    friends_html = "".join([f"<div class=card>👤 {f}</div>" for f in user['friends']]) or "<p>No friends yet</p>"
    all_users_html = "".join([f"<div class=card><b>{u['name']}</b><form method=POST action=/friends><input type=hidden name=send_request value={u['nickname']}><button class=btn.blue>Add Friend</button></form></div>" for u in all_users if u['nickname'] not in user['friends']])

    stats = f"<div class=card><h3>📊 CBT Stats</h3><p><b>Correct:</b> {user['correct']}</p><p><b>Wrong:</b> {user['wrong']}</p><p><b>Q Used:</b> {user['q_used']}</p><p><b>Lesson Expiry:</b> {user['lesson_expiry']}</p></div>"

    content = f"<div class=card><h2>My Profile</h2><p><b>Name:</b> {user['name']}</p><p><b>Nickname:</b> @{user['nickname']}</p><p><b>Class:</b> {user['class']} {user.get('dept','')}</p></div>{stats}<div class=card><h2>Friend Requests</h2>{incoming_html or '<p>No requests</p>'}</div><div class=card><h2>My Friends</h2>{friends_html}</div><div class=card><h2>Add Friend</h2>{all_users_html}</div><a class='btn red' href=/logout>🚪 Logout</a>"
    return render_template_string(BASE, title="Me", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")

@app.route('/chat') # PACKED DM + GROUPS
@login_required
def chat(nickname, user):
    with DBSession() as db:
        friends_html = ""
        for f in user['friends']:
            name = db.execute(sa.text("SELECT name FROM users WHERE nickname=:u"), {"u": f}).scalar()
            initial = name[0].upper() if name else "?"
            dms = db.execute(sa.text("SELECT * FROM dms WHERE to_nickname=:u AND from_nickname=:f"), {"u": nickname, "f": f}).mappings().all()
            unread = len([d for d in dms if nickname not in json.loads(d.get('read_by','[]'))])
            bell = f'<span class=notification>🔔</span>' if unread > 0 else ''
            friends_html += f"<a class=friend-card href=/dm/{f} style='position:relative'>{bell}<div class=friend-avatar>{initial}</div><div style='flex:1'><b>{name}</b></div></a>"

        my_groups = db.execute(sa.text("SELECT * FROM groups")).mappings().all()
        groups_html = ""
        for g in my_groups:
            if nickname in json.loads(g['members']):
                messages = json.loads(g['messages'])
                unread = len([m for m in messages if nickname not in m.get('read_by',[])])
                bell = f'<span class=notification>🔔</span>' if unread > 0 else ''
                groups_html += f"<a class=friend-card href=/group/{g['id']} style='position:relative'>{bell}<div class=friend-avatar>👥</div><div style='flex:1'><b>{g['name']}</b></div></a>"

    content = f"<div class=card><h2>DM - My Friends</h2>{friends_html or '<p>Add friends to start chat</p>'}</div><div class=card><h2>Groups</h2>{groups_html or '<p>No groups yet</p>'}<form method=POST action=/groups><input name=group_name placeholder='Create Group Name' required><button name=create_group class=btn.blue>Create Group</button></form></div>"
    return render_template_string(BASE, title="Chat", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")

@app.route('/friends', methods=["GET","POST"]) # FOR POST HANDLING ONLY
@login_required
def friends(nickname, user):
    with DBSession() as db:
        if request.method=="POST":
            if "send_request" in request.form: db.execute(sa.text("INSERT INTO friend_requests (from_nickname, to_nickname) VALUES (:f, :t)"), {"f": nickname, "t": request.form["send_request"]}); db.commit()
            elif "accept_user" in request.form:
                from_user = request.form["accept_user"];
                if from_user not in user['friends']: user['friends'].append(from_user)
                db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(user['friends']), "u": nickname})
                from_friends = json.loads(db.execute(sa.text("SELECT friends FROM users WHERE nickname=:u"), {"u": from_user}).scalar() or '[]');
                if nickname not in from_friends: from_friends.append(nickname)
                db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(from_friends), "u": from_user})
                db.execute(sa.text("DELETE FROM friend_requests WHERE from_nickname=:f AND to_nickname=:t"), {"f": from_user, "t": nickname}); db.commit()
    return redirect("/me")

@app.route('/dm/<to_nickname>', methods=["GET","POST"])
@login_required
def dm_chat(nickname, user, to_nickname):
    if to_nickname not in user['friends']: return redirect("/chat")
    with DBSession() as db:
        if request.method=="POST":
            msg_text = request.form["msg"]
            db.execute(sa.text("INSERT INTO dms (from_nickname, to_nickname, text, time, read_by) VALUES (:f, :t, :txt, :time, :r)"),
                       {"f": nickname, "t": to_nickname, "txt": msg_text, "time": datetime.now(NIGERIA_TZ).strftime("%H:%M"), "r": json.dumps([nickname])})
            db.commit(); return redirect(f"/dm/{to_nickname}")
        chat = db.execute(sa.text("SELECT * FROM dms WHERE (from_nickname=:u AND to_nickname=:t) OR (from_nickname=:t AND to_nickname=:u) ORDER BY id"),{"u": nickname, "t": to_nickname}).mappings().all()
        for m in chat:
            if m['to_nickname'] == nickname:
                try: read_list = json.loads(m.get('read_by','[]'))
                except: read_list = []
                if nickname not in read_list:
                    read_list.append(nickname)
                    db.execute(sa.text("UPDATE dms SET read_by=:r WHERE id=:id"), {"r": json.dumps(read_list), "id": m['id']})
        db.commit()
        to_name = db.execute(sa.text("SELECT name FROM users WHERE nickname=:u"), {"u": to_nickname}).scalar()
    msgs = "".join([f"<div class='chat-msg {'me' if m['from_nickname']==nickname else 'other'}'><div class=bubble><b>{m['from_nickname']}:</b> {m['text']} <small>{m['time']}</small></div></div>" for m in chat])
    content = f"<div class=card><div class=chat-box>{msgs or '<p style=text-align:center;color:gray>No messages yet</p>'}</div><form method=POST><input name=msg placeholder='Type message...' required style=width:100%><button class=btn.gray style=margin-top:8px>Send</button></form></div>"
    return render_template_string(BASE, title=f"Chat with {to_name}", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")

@app.route('/groups', methods=["GET","POST"])
@login_required
def groups(nickname, user):
    with DBSession() as db:
        if request.method=="POST":
            if "create_group" in request.form:
                db.execute(sa.text("INSERT INTO groups (name, creator, members, messages) VALUES (:n, :c, :m, :msg)"),
                           {"n": request.form["group_name"], "c": nickname, "m": json.dumps([nickname]), "msg": json.dumps([])})
                db.commit()
            return redirect("/chat")
    return redirect("/chat")

@app.route('/group/<int:gid>', methods=["GET","POST"])
@login_required
def group_chat(nickname, user, gid):
    with DBSession() as db:
        group = db.execute(sa.text("SELECT * FROM groups WHERE id=:id"), {"id": gid}).mappings().first()
        if not group or nickname not in json.loads(group['members']): return redirect("/chat")
        members = json.loads(group['members']); messages = json.loads(group['messages']); is_creator = group['creator']==nickname
        if request.method=="POST":
            if "send_msg" in request.form:
                messages.append({"user": user["name"], "text": request.form["msg"], "time": datetime.now(NIGERIA_TZ).strftime("%H:%M"), "read_by": [nickname]})
                db.execute(sa.text("UPDATE groups SET messages=:m WHERE id=:id"), {"m": json.dumps(messages), "id": gid})
            db.commit(); return redirect(f"/group/{gid}")
        updated = False
        for m in messages:
            if 'read_by' not in m: m['read_by'] = []
            if nickname not in m['read_by']: m['read_by'].append(nickname); updated = True
        if updated: db.execute(sa.text("UPDATE groups SET messages=:m WHERE id=:id"), {"m": json.dumps(messages), "id": gid}); db.commit()
        msgs = "".join([f"<div class='chat-msg {'me' if m['user']==user['name'] else 'other'}'><div class=bubble><b>{m['user']}:</b> {m['text']} <small>{m['time']}</small></div></div>" for m in messages])
    content = f"<div class=card><h2>{group['name']}</h2></div><div class=card><div class=chat-box>{msgs or '<p>No messages yet</p>'}</div><form method=POST><input name=msg placeholder='Type message...' required style=width:70%;display:inline-block><button name=send_msg class=btn.gray style=width:28%;display:inline-block>Send</button></form></div>"
    return render_template_string(BASE, title=group['name'], header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")
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
    q_class = request.args.get('q_class'); q_dept = request.args.get('q_dept')
    l_class = request.args.get('l_class'); l_dept = request.args.get('l_dept')

    if request.method=="POST":
        with DBSession() as db:
            # PAYMENT VERIFY - 15 DAYS NOW
            if "verify_id" in request.form:
                req = db.execute(sa.text("SELECT * FROM payments WHERE id=:id"), {"id": request.form["verify_id"]}).mappings().first()
                if req["type"] == "questions": db.execute(sa.text("UPDATE users SET q_cycle='paid' WHERE nickname=:u"), {"u": req["nickname"]})
                if req["type"] == "lessons": db.execute(sa.text("UPDATE users SET lesson_expiry=:d WHERE nickname=:u"), {"d": str(date.today() + timedelta(days=15)), "u": req["nickname"]}) # 15 DAYS
                db.execute(sa.text("UPDATE payments SET status='Verified' WHERE id=:id"), {"id": request.form["verify_id"]})
                db.commit(); error = "<div class=success>Payment Verified</div>"
            if "deny_id" in request.form: db.execute(sa.text("UPDATE payments SET status='Denied' WHERE id=:id"), {"id": request.form["deny_id"]}); db.commit(); error = "<div class=error>Payment Denied</div>"

            # ADD QUESTION - FULL FORM
            if "add_question" in request.form:
                cls = request.form['admin_class']; dept = request.form.get('admin_dept',''); sub = request.form['admin_subject']; key = f"{cls}_{dept}_{sub}" if dept else f"{cls}_{sub}"
                options = [request.form["a"],request.form["b"],request.form["c"],request.form["d"]]
                correct_ans = options[int(request.form["correct_ans"])]
                db.execute(sa.text("INSERT INTO questions (key, q, options, ans) VALUES (:k, :q, :o, :a)"),{"k": key, "q": request.form["q"], "o": json.dumps(options), "a": correct_ans}); db.commit(); error = f"<div class=success>Question Added for {sub}</div>"

            # ADD LESSON - FULL FORM
            if "add_lesson" in request.form: db.execute(sa.text("INSERT INTO lessons (class, dept, subject, title, notes, date) VALUES (:c, :d, :s, :t, :n, :date)"),{"c": request.form['lesson_class'], "d": request.form.get('lesson_dept',''), "s": request.form['lesson_subject'], "t": request.form['lesson_title'], "n": request.form['lesson_notes'], "date": str(date.today())}); db.commit(); error = "<div class=success>Lesson Posted</div>"

            if "change_pass" in request.form:
                if request.form["old_pass"]!= ADMIN_PASS: error = "<div class=error>Old password is wrong</div>"
                else: ADMIN_PASS = request.form["new_pass"]; set_setting("admin_pass", ADMIN_PASS); error = "<div class=success>Admin Password Changed</div>"

    with DBSession() as db:
        pending_reqs = db.execute(sa.text("SELECT * FROM payments WHERE status='Pending'")).mappings().all()

    pending_html = "".join([f"<div class='card'><b>{r['name']}</b> for {r['type']}<br><small>Bank: {r.get('bank_used','N/A')} | Acc: {r.get('account_name','N/A')} | Date: {r.get('date_paid','N/A')}</small><div style='display:flex;gap:5px'><form method=POST style='flex:1'><input type=hidden name=verify_id value={r['id']}><button class=btn>Verify</button></form><form method=POST style='flex:1'><input type=hidden name=deny_id value={r['id']}><button class='btn red'>Deny</button></form></div></div>" for r in pending_reqs])

    # 24 BUTTONS FOR QUESTIONS + LESSONS - URL ENCODED
    q_buttons = ""; l_buttons = ""
    for cls in ["JSS1","JSS2","JSS3"]:
        q_buttons += f"<a href=/admin?q_class={urllib.parse.quote(cls)} class=btn.gray>Add Q {cls}</a>"
        l_buttons += f"<a href=/admin?l_class={urllib.parse.quote(cls)} class=btn.gray>Add Lesson {cls}</a>"
    for cls in ["SS1","SS2","SS3"]:
        for dept in ["Science","Commercial","Art"]:
            q_buttons += f"<a href=/admin?q_class={urllib.parse.quote(cls)}&q_dept={urllib.parse.quote(dept)} class=btn.gray>Add Q {cls} {dept}</a>"
            l_buttons += f"<a href=/admin?l_class={urllib.parse.quote(cls)}&l_dept={urllib.parse.quote(dept)} class=btn.gray>Add Lesson {cls} {dept}</a>"

    # SHOW ADD QUESTION FORM IF CLASS SELECTED
    add_q_form = ""
    if q_class:
        q_class = urllib.parse.unquote(q_class); q_dept = urllib.parse.unquote(q_dept) if q_dept else ""
        subs = SUBJECTS.get(f"{q_class}_{q_dept}") if q_dept else SUBJECTS.get(q_class)
        sub_options = "".join([f"<option>{s}</option>" for s in subs])
        add_q_form = f"<div class=card><h3>Add Question for {q_class} {q_dept or ''}</h3><form method=POST><input type=hidden name=admin_class value='{q_class}'><input type=hidden name=admin_dept value='{q_dept or ''}'><select name=admin_subject required><option value=''>Select Subject</option>{sub_options}</select><textarea name=q placeholder='Question' required></textarea><input name=a placeholder='Option A' required><input name=b placeholder='Option B' required><input name=c placeholder='Option C' required><input name=d placeholder='Option D' required><select name=correct_ans required><option value=0>A</option><option value=1>B</option><option value=2>C</option><option value=3>D</option></select><button name=add_question class=btn>Save Question</button></form></div>"

    # SHOW ADD LESSON FORM IF CLASS SELECTED
    add_l_form = ""
    if l_class:
        l_class = urllib.parse.unquote(l_class); l_dept = urllib.parse.unquote(l_dept) if l_dept else ""
        subs = SUBJECTS.get(f"{l_class}_{l_dept}") if l_dept else SUBJECTS.get(l_class)
        sub_options = "".join([f"<option>{s}</option>" for s in subs])
        add_l_form = f"<div class=card><h3>Add Lesson for {l_class} {l_dept or ''}</h3><form method=POST><input type=hidden name=lesson_class value='{l_class}'><input type=hidden name=lesson_dept value='{l_dept or ''}'><select name=lesson_subject required><option value=''>Select Subject</option>{sub_options}</select><input name=lesson_title placeholder='Lesson Title' required><textarea name=lesson_notes placeholder='Lesson Notes' rows=6 required></textarea><button name=add_lesson class=btn>Post Lesson</button></form></div>"

    form = f'\
<div class="card"><h2>Admin Panel - 4 GROUPS - 28 BUTTONS</h2>{error}</div>\
{add_q_form}{add_l_form}\
<div class="card"><h2>📝 GROUP 1: CBT - ADD QUESTIONS</h2><p>12 Buttons</p><div style="display:grid;grid-template-columns:1fr 1fr;gap:5px">{q_buttons}</div></div>\
<div class="card"><h2>🎓 GROUP 2: LESSONS - POST LESSONS</h2><p>12 Buttons</p><div style="display:grid;grid-template-columns:1fr 1fr;gap:5px">{l_buttons}</div></div>\
<div class="card"><h2>👥 GROUP 3: STUDENT MANAGEMENT</h2><h3>25. Confirm Payment</h3>{pending_html or "<p>No pending payments</p>"}<h3>26. View Attendance</h3><p>Coming soon</p><h3>27. Post Notice</h3><p>Coming soon</p></div>\
<div class="card"><h2>🔒 GROUP 4: ADMIN SETTINGS</h2><h3>28. Change Admin Password</h3><form method="POST"><input type="password" name="old_pass" placeholder="Current Password" required><input type="password" name="new_pass" placeholder="New Password" required><button name="change_pass" class="btn orange">Change Password</button></form></div>'

    return render_template_string(BASE, title="Admin", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(form), timer_script="")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
