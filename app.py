import os, sqlite3, time, json
from functools import wraps
from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "motiz_secret_key_v14"  # CHANGE THIS IN PRODUCTION
DB_PATH = "motiz.db"

# ========= CONFIG =========
CLASSES = ["JSS1","JSS2","JSS3","SSS1","SSS2","SSS3"]
DEPARTMENTS = {
    "JSS1": ["General"], "JSS2": ["General"], "JSS3": ["General"],
    "SSS1": ["Science","Commercial","Art"],
    "SSS2": ["Science","Commercial","Art"],
    "SSS3": ["Science","Commercial","Art"]
}
SUBJECTS = {
    "JSS1": ["Mathematics","English","Basic Science","Basic Tech","Social Studies","Civic","CRS","Agric","Business Studies","Computer"],
    "JSS2": ["Mathematics","English","Basic Science","Basic Tech","Social Studies","Civic","CRS","Agric","Business Studies","Computer"],
    "JSS3": ["Mathematics","English","Basic Science","Basic Tech","Social Studies","Civic","CRS","Agric","Business Studies","Computer"],
    "SSS1_Science": ["Mathematics","English","Physics","Chemistry","Biology","Further Maths","Geography","Civic","CRS","Computer"],
    "SSS2_Science": ["Mathematics","English","Physics","Chemistry","Biology","Further Maths","Geography","Civic","CRS","Computer"],
    "SSS3_Science": ["Mathematics","English","Physics","Chemistry","Biology","Further Maths","Geography","Civic","CRS","Computer"],
    "SSS1_Commercial": ["Mathematics","English","Economics","Accounting","Commerce","Government","Civic","CRS","Computer","Marketing"],
    "SSS2_Commercial": ["Mathematics","English","Economics","Accounting","Commerce","Government","Civic","CRS","Computer","Marketing"],
    "SSS3_Commercial": ["Mathematics","English","Economics","Accounting","Commerce","Government","Civic","CRS","Computer","Marketing"],
    "SSS1_Art": ["Mathematics","English","Literature","Government","History","CRS","Civic","Geography","Fine Art","Computer"],
    "SSS2_Art": ["Mathematics","English","Literature","Government","History","CRS","Civic","Geography","Fine Art","Computer"],
    "SSS3_Art": ["Mathematics","English","Literature","Government","History","CRS","Civic","Geography","Fine Art","Computer"],
}

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = generate_password_hash("admin123") # CHANGE THIS

# ========= DB =========
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, 
        class TEXT, dept TEXT, correct INTEGER DEFAULT 0, wrong INTEGER DEFAULT 0,
        lesson_expiry TEXT, questions_used INTEGER DEFAULT 0, last_question_reset TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY, class TEXT, dept TEXT, subject TEXT,
        question TEXT, opt_a TEXT, opt_b TEXT, opt_c TEXT, opt_d TEXT,
        answer TEXT, explanation TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY, class TEXT, dept TEXT, subject TEXT,
        title TEXT, notes TEXT, video_link TEXT, created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS notices (id INTEGER PRIMARY KEY, text TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY, username TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY, username TEXT, login_time TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS friends (id INTEGER PRIMARY KEY, user1 TEXT, user2 TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, sender TEXT, receiver TEXT, group_id INTEGER, text TEXT, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS groups (id INTEGER PRIMARY KEY, name TEXT)''')
    conn.commit(); conn.close()

init_db()

# ========= HELPERS =========
def get_header():
    # FINAL 6 BUTTON NAVBAR + FLASH MESSAGES + WHATSAPP STYLE
    return '''
    <style>
        body{font-family:Arial;margin:0;background:#f8fafc;}
        .nav{background:#1e3a8a;color:white;padding:12px;display:flex;gap:20px;flex-wrap:wrap;justify-content:center;position:sticky;top:0;z-index:10;}
        .nav a{color:white;text-decoration:none;font-weight:bold;}
        .nav a:hover{text-decoration:underline;}
        .container{padding:20px;max-width:900px;margin:auto;}
        .flash{padding:10px;margin:10px 0;border-radius:5px;background:#dcfce7;border:1px solid green;}
        /* WhatsApp Chat Style */
        .chat-box{background:#e5ddd5;padding:15px;border-radius:8px;height:450px;overflow-y:auto;}
        .msg-me{text-align:right;margin:6px 0;}
        .msg-me span{background:#dcf8c6;padding:8px 12px;border-radius:15px;display:inline-block;max-width:70%;text-align:left;}
        .msg-other{text-align:left;margin:6px 0;}
        .msg-other span{background:#fff;border:1px solid #ddd;padding:8px 12px;border-radius:15px;display:inline-block;max-width:70%;text-align:left;}
    </style>
    <div class="nav">
        <a href="/main">🏠 Home</a>
        <a href="/exam">✍️ CBT</a>
        <a href="/lessons">🎓 Lessons</a>
        <a href="/community">🌍 Community</a>
        <a href="/chat">💬 Chat</a>
        <a href="/me">👤 Me</a>
    </div>
    <div class="container">
    {% with messages = get_flashed_messages() %}
      {% if messages %}{% for message in messages %}<div class="flash">{{ message }}</div>{% endfor %}{% endif %}
    {% endwith %}
    '''

def get_footer():
    return '</div>'

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'username' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrap

def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'admin' not in session: return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return wrap

def reset_daily_questions(username):
    # Reset questions_used every new day
    conn = get_db()
    user = conn.execute("SELECT last_question_reset FROM users WHERE username=?", (username,)).fetchone()
    today = datetime.now().strftime("%Y-%m-%d")
    if not user['last_question_reset'] or user['last_question_reset'] != today:
        conn.execute("UPDATE users SET questions_used=0, last_question_reset=? WHERE username=?", (today, username))
        conn.commit()
    conn.close()

# ========= AUTH ROUTES =========
@app.route("/")
def index(): return redirect(url_for('login'))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        u=request.form['username']; p=request.form['password']
        conn=get_db(); user=conn.execute("SELECT * FROM users WHERE username=?",(u,)).fetchone(); conn.close()
        if user and check_password_hash(user['password'],p):
            session['username']=u; session['class']=user['class']; session['dept']=user['dept']
            conn=get_db(); conn.execute("INSERT INTO attendance(username,login_time) VALUES(?,?)",(u,datetime.now().isoformat())); conn.commit(); conn.close()
            reset_daily_questions(u)
            return redirect(url_for('main'))
        flash("Invalid login")
    return render_template_string(get_header()+f'''
    <h2>Login</h2>
    <form method=post style="border:1px solid #ddd;padding:20px;border-radius:8px;background:white;">
        Username: <input name=username required style="width:100%;padding:8px;margin:5px 0;"><br>
        Password: <input name=password type=password required style="width:100%;padding:8px;margin:5px 0;"><br>
        <button style="background:#1e3a8a;color:white;padding:10px;border:none;width:100%;">Login</button>
    </form>
    <p>Don't have account? <a href=/register>Register</a></p>
    <p>Admin: <a href=/admin_login>Login here</a></p>
    {get_footer()}
    ''')

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        u=request.form['username']; p=generate_password_hash(request.form['password'])
        c=request.form['class']; d=request.form['dept']
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            conn=get_db(); conn.execute("INSERT INTO users(username,password,class,dept,last_question_reset) VALUES(?,?,?,?,?)",(u,p,c,d,today))
            conn.commit(); conn.close(); flash("Registered Successfully"); return redirect(url_for('login'))
        except: flash("Username already exists")
    
    class_options="".join([f'<option>{cl}</option>' for cl in CLASSES])
    
    return render_template_string(get_header()+f'''
    <h2>Register</h2>
    <form method=post style="border:1px solid #ddd;padding:20px;border-radius:8px;background:white;">
        Username: <input name=username required style="width:100%;padding:8px;margin:5px 0;"><br>
        Password: <input name=password type=password required style="width:100%;padding:8px;margin:5px 0;"><br>
        Class: <select name=class style="width:100%;padding:8px;margin:5px 0;">{class_options}</select><br>
        Dept: <select name=dept style="width:100%;padding:8px;margin:5px 0;">
            <option>General</option><option>Science</option><option>Commercial</option><option>Art</option>
        </select><br>
        <button style="background:green;color:white;padding:10px;border:none;width:100%;">Register</button>
    </form>
    {get_footer()}
    ''')

@app.route("/admin_login", methods=["GET","POST"])
def admin_login():
    if request.method=="POST":
        if request.form['username']==ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, request.form['password']):
            session['admin']=ADMIN_USERNAME; return redirect(url_for('admin'))
        flash("Wrong admin credentials")
    
    return render_template_string('''
    <style>body{font-family:Arial;background:#f1f5f9;display:flex;justify-content:center;align-items:center;height:100vh;}</style>
    <div style="border:1px solid #ddd;padding:30px;border-radius:10px;background:white;">
    <h2>🔒 Admin Login</h2>
    <form method=post>
        Username: <input name=username required><br><br>
        Password: <input name=password type=password required><br><br>
        <button style="background:#1e3a8a;color:white;padding:10px;width:100%;">Login</button>
    </form>
    </div>
    ''')

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for('login'))
# ========= STUDENT ROUTES =========

@app.route("/main")
@login_required
def main():
    reset_daily_questions(session['username']) # Reset daily
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=?", (session['username'],)).fetchone()
    notices = conn.execute("SELECT * FROM notices ORDER BY id DESC LIMIT 5").fetchall()
    conn.close()
    
    notice_html = "".join([f"<li style='background:#fef3c7;padding:10px;margin:5px 0;border-radius:5px;'>{n['text']}</li>" for n in notices]) or "<li>No notices yet</li>"
    
    return render_template_string(get_header() + f'''
    <h2>🏠 Welcome {session['username']}</h2>
    <div style="border:1px solid #ddd;padding:15px;border-radius:10px;background:white;margin-bottom:20px;">
        <h3>Your Stats</h3>
        <p><b>Class:</b> {user['class']} | <b>Dept:</b> {user['dept']}</p>
        <p>✅ Correct: {user['correct']} | ❌ Wrong: {user['wrong']}</p>
        <p><b>Questions Left Today:</b> {20 - user['questions_used']}/20</p>
        <p><b>Lesson Access:</b> {user['lesson_expiry'][:10] if user['lesson_expiry'] else 'None'}</p>
    </div>
    <h3>📢 School Notices</h3>
    <ul style="list-style:none;padding:0;">{notice_html}</ul>
    {get_footer()}
    ''')

# ========= CBT EXAM =========
@app.route("/exam", methods=["GET","POST"])
@login_required
def exam():
    reset_daily_questions(session['username'])
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=?", (session['username'],)).fetchone()
    
    if user['questions_used'] >= 20:
        conn.close()
        return render_template_string(get_header() + "<h3>⚠️ Daily Limit Reached</h3><p>You have used your 20 questions for today. Come back tomorrow.</p><a href=/main>Back to Home</a>" + get_footer())
    
    if request.method == "POST" and 'subject' in request.form:
        class_ = request.form['class']; dept = request.form['dept']; subject = request.form['subject']
        questions = conn.execute("SELECT * FROM questions WHERE class=? AND dept=? AND subject=? ORDER BY RANDOM() LIMIT 20",
                                 (class_, dept, subject)).fetchall()
        conn.close()
        if len(questions) < 5: 
            return render_template_string(get_header() + "<h3>Not enough questions for this subject. Admin should add at least 5.</h3><a href=/exam>Back</a>" + get_footer())
        session['exam'] = [dict(q) for q in questions]
        session['exam_start'] = time.time()
        return redirect(url_for('take_exam'))

    classes_opt = "".join([f"<option>{c}</option>" for c in CLASSES])
    depts_opt = "".join([f"<option>{d}</option>" for d in DEPARTMENTS.get(user['class'], ["General"])])
    subjects_opt = "".join([f"<option>{s}</option>" for s in SUBJECTS.get(f"{user['class']}_{user['dept']}", SUBJECTS.get(user['class'],[]))])
    conn.close()
    
    return render_template_string(get_header() + f'''
    <h2>✍️ Take CBT</h2>
    <p>20 Questions | 20 Minutes Timer | {20 - user['questions_used']} left today</p>
    <form method=post style="border:1px solid #ddd;padding:20px;border-radius:8px;background:white;">
        <b>Class:</b> <select name=class style="padding:8px;">{classes_opt}</select><br><br>
        <b>Dept:</b> <select name=dept style="padding:8px;">{depts_opt}</select><br><br>
        <b>Subject:</b> <select name=subject style="padding:8px;">{subjects_opt}</select><br><br>
        <button style="background:#1e3a8a;color:white;padding:12px;border:none;border-radius:5px;width:100%;">Start Exam</button>
    </form>
    {get_footer()}
    ''')

@app.route("/take_exam", methods=["GET","POST"])
@login_required
def take_exam():
    if 'exam' not in session: return redirect(url_for('exam'))
    if time.time() - session['exam_start'] > 1200: # 20 mins
        session.pop('exam'); 
        return render_template_string(get_header() + "<h2>Time Up!</h2><a href=/exam>Try again</a>" + get_footer())
    
    questions = session['exam']
    if request.method == "POST":
        score = 0; correct=0; wrong=0
        conn = get_db()
        for i,q in enumerate(questions):
            ans = request.form.get(f"q{i}")
            if ans == q['answer']: score+=5; correct+=1
            else: wrong+=1
        conn.execute("UPDATE users SET correct=correct+?, wrong=wrong+?, questions_used=questions_used+? WHERE username=?",
                     (correct,wrong,len(questions),session['username']))
        conn.commit(); conn.close()
        session.pop('exam')
        return render_template_string(get_header() + f"<h2>Result: {score}/100</h2><p>✅ {correct} Correct | ❌ {wrong} Wrong</p><a href=/exam>Take Another</a>" + get_footer())
    
    form_html = ""
    for i,q in enumerate(questions):
        form_html += f"<div style='margin-bottom:20px;padding:10px;border:1px solid #eee;border-radius:5px;background:white;'><h4>{i+1}. {q['question']}</h4>"
        for opt in ['A','B','C','D']:
            form_html += f'<input type=radio name=q{i} value={opt} required> {q[f"opt_{opt.lower()}"]}<br>'
        form_html += "</div>"
    
    return render_template_string(get_header() + f'''
    <h2>Exam In Progress - 20 Minutes</h2>
    <form method=post>{form_html}<button style="background:green;color:white;padding:12px;border:none;width:100%;">Submit Exam</button></form>
    {get_footer()}
    ''')

# ========= LESSONS =========
@app.route("/lessons")
@login_required
def lessons():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=?", (session['username'],)).fetchone()
    lessons = conn.execute("SELECT * FROM lessons WHERE class=? AND dept=? ORDER BY id DESC", 
                           (user['class'], user['dept'])).fetchall()
    conn.close()
    
    lesson_html = ""
    for l in lessons:
        expiry = user['lesson_expiry']
        can_view = expiry and datetime.fromisoformat(expiry) > datetime.now()
        link = f"<a href=/view_lesson/{l['id']} style='background:green;color:white;padding:5px 10px;border-radius:3px;text-decoration:none;'>▶️ View</a>" if can_view else "<span style='color:red;'>🔒 Locked</span>"
        lesson_html += f"<li style='padding:12px;border:1px solid #ddd;margin:8px 0;border-radius:5px;background:white;'><b>{l['subject']}</b>: {l['title']} - {link}</li>"
    
    return render_template_string(get_header() + f'''
    <h2>🎓 Lessons for {user['class']} {user['dept']}</h2>
    <p><i>Clicking a lesson gives you 7 days access</i></p>
    <ul style="list-style:none;padding:0;">{lesson_html or "<li>No lessons yet</li>"}</ul>
    {get_footer()}
    ''')

@app.route("/view_lesson/<int:id>")
@login_required
def view_lesson(id):
    conn = get_db()
    lesson = conn.execute("SELECT * FROM lessons WHERE id=?", (id,)).fetchone()
    if not lesson: return "Lesson not found"
    
    # Give 7 days access when they click
    conn.execute("UPDATE users SET lesson_expiry=? WHERE username=?", 
                 ((datetime.now()+timedelta(days=7)).isoformat(), session['username']))
    conn.commit(); conn.close()
    
    return render_template_string(get_header() + f'''
    <h2>{lesson['title']}</h2>
    <p><b>Subject:</b> {lesson['subject']}</p>
    <div style="background:white;padding:15px;border-radius:8px;border:1px solid #ddd;line-height:1.6;">{lesson['notes']}</div>
    {f'<iframe src="{lesson["video_link"]}" width=100% height=350 style="margin-top:15px;border:none;border-radius:8px;"></iframe>' if lesson['video_link'] else ''}
    <p style="color:orange;margin-top:10px;"><i>⏰ This lesson expires in 7 days</i></p>
    <a href=/lessons>⬅️ Back to Lessons</a>
    {get_footer()}
    ''')
# ========= COMMUNITY =========
@app.route("/community", methods=["GET","POST"])
@login_required
def community():
    conn = get_db()
    if request.method == "POST":
        text = request.form['text']
        if text.strip():
            conn.execute("INSERT INTO messages(sender,text,timestamp) VALUES(?,?,?)", 
                         (session['username'], text, datetime.now().isoformat()))
            conn.commit()
    
    posts = conn.execute("SELECT * FROM messages WHERE receiver IS NULL AND group_id IS NULL ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    
    posts_html = "".join([f"<div style='border:1px solid #ddd;padding:12px;margin:8px 0;border-radius:8px;background:white;'><b style='color:#1e3a8a;'>{p['sender']}</b><br>{p['text']}<br><small style='color:gray;'>{p['timestamp'][:16].replace('T',' ')}</small></div>" for p in posts])
    
    return render_template_string(get_header() + f'''
    <h2>🌍 Community</h2>
    <form method=post style="background:white;padding:15px;border-radius:8px;border:1px solid #ddd;margin-bottom:20px;">
        <textarea name=text placeholder="What's on your mind?" required style="width:100%;height:70px;padding:8px;border:1px solid #ccc;border-radius:5px;"></textarea><br>
        <button style="background:#1e3a8a;color:white;padding:10px;border:none;border-radius:5px;margin-top:5px;">Post</button>
    </form>
    <h3>Recent Posts</h3>
    {posts_html or "<p>No posts yet. Be the first!</p>"}
    {get_footer()}
    ''')

# ========= CHAT - DM + GROUPS CLICKABLE =========
@app.route("/chat")
@login_required
def chat():
    conn = get_db()
    user = session['username']
    
    # Get friends for DM
    friends = conn.execute("SELECT user2 as friend FROM friends WHERE user1=? AND status='accepted' UNION SELECT user1 as friend FROM friends WHERE user2=? AND status='accepted'", (user,user)).fetchall()
    
    # Get groups
    groups = conn.execute("SELECT * FROM groups").fetchall()
    conn.close()
    
    friends_html = "".join([f"<li style='padding:8px;border-bottom:1px solid #eee;'><a href=/dm/{f['friend']} style='text-decoration:none;'>💬 {f['friend']}</a></li>" for f in friends]) or "<li style='padding:8px;'>No friends yet</li>"
    
    # Groups are now clickable
    groups_html = "".join([f"<li style='padding:8px;border-bottom:1px solid #eee;'><a href=/group/{g['id']} style='text-decoration:none;'>👥 {g['name']}</a></li>" for g in groups]) or "<li style='padding:8px;'>No groups yet</li>"
    
    return render_template_string(get_header() + f'''
    <h2>💬 Chat</h2>
    <div style="display:flex;gap:20px;flex-wrap:wrap;">
        <div style="flex:1;min-width:300px;border:1px solid #ddd;padding:15px;border-radius:8px;background:white;">
            <h3>Direct Messages</h3>
            <ul style="list-style:none;padding:0;">{friends_html}</ul>
        </div>
        <div style="flex:1;min-width:300px;border:1px solid #ddd;padding:15px;border-radius:8px;background:white;">
            <h3>Group Chats</h3>
            <ul style="list-style:none;padding:0;">{groups_html}</ul>
        </div>
    </div>
    {get_footer()}
    ''')

@app.route("/dm/<friend>", methods=["GET","POST"])
@login_required
def dm(friend):
    conn = get_db()
    if request.method == "POST":
        text = request.form['text']
        if text.strip():
            conn.execute("INSERT INTO messages(sender,receiver,text,timestamp) VALUES(?,?,?,?)", 
                         (session['username'], friend, text, datetime.now().isoformat()))
            conn.commit()
    
    msgs = conn.execute("SELECT * FROM messages WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id", 
                        (session['username'],friend,friend,session['username'])).fetchall()
    conn.close()
    
    # WhatsApp bubbles
    msgs_html = ""
    for m in msgs:
        if m['sender'] == session['username']:
            msgs_html += f"<div class='msg-me'><span>{m['text']}</span></div>"
        else:
            msgs_html += f"<div class='msg-other'><span>{m['text']}</span></div>"
    
    return render_template_string(get_header() + f'''
    <h2>Chat with {friend}</h2>
    <div class="chat-box">{msgs_html or "<p style='text-align:center;color:gray;'>No messages yet</p>"}</div>
    <form method=post style="margin-top:10px;display:flex;gap:10px;">
        <input name=text placeholder="Type message" required style="flex:1;padding:10px;border:1px solid #ccc;border-radius:5px;">
        <button style="background:#1e3a8a;color:white;padding:10px 20px;border:none;border-radius:5px;">Send</button>
    </form>
    <a href=/chat>⬅️ Back to Chat</a>
    {get_footer()}
    ''')

@app.route("/group/<int:group_id>", methods=["GET","POST"])
@login_required
def group_chat(group_id):
    conn = get_db()
    group = conn.execute("SELECT * FROM groups WHERE id=?", (group_id,)).fetchone()
    if not group: return "Group not found"
    
    if request.method == "POST":
        text = request.form['text']
        if text.strip():
            conn.execute("INSERT INTO messages(sender,group_id,text,timestamp) VALUES(?,?,?,?)", 
                         (session['username'], group_id, text, datetime.now().isoformat()))
            conn.commit()
    
    # Get all messages for this group
    msgs = conn.execute("SELECT * FROM messages WHERE group_id=? ORDER BY id", (group_id,)).fetchall()
    conn.close()
    
    # WhatsApp bubbles for group too
    msgs_html = ""
    for m in msgs:
        if m['sender'] == session['username']:
            msgs_html += f"<div class='msg-me'><span><b>You:</b> {m['text']}</span></div>"
        else:
            msgs_html += f"<div class='msg-other'><span><b style='color:#1e3a8a;'>{m['sender']}:</b> {m['text']}</span></div>"
    
    return render_template_string(get_header() + f'''
    <h2>Group: {group['name']}</h2>
    <div class="chat-box">{msgs_html or "<p style='text-align:center;color:gray;'>No messages yet</p>"}</div>
    <form method=post style="margin-top:10px;display:flex;gap:10px;">
        <input name=text placeholder="Type message" required style="flex:1;padding:10px;border:1px solid #ccc;border-radius:5px;">
        <button style="background:#1e3a8a;color:white;padding:10px 20px;border:none;border-radius:5px;">Send</button>
    </form>
    <a href=/chat>⬅️ Back to Chat</a>
    {get_footer()}
    ''')

# ========= ME - PROFILE + ADD FRIEND + FRIENDS + LOGOUT INSIDE =========
@app.route("/me")
@login_required
def me():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=?", (session['username'],)).fetchone()
    
    # Friends
    friends = conn.execute("SELECT user2 as friend FROM friends WHERE user1=? AND status='accepted' UNION SELECT user1 as friend FROM friends WHERE user2=? AND status='accepted'", (user['username'],user['username'])).fetchall()
    requests = conn.execute("SELECT user1 as req FROM friends WHERE user2=? AND status='pending'", (user['username'],)).fetchall()
    conn.close()
    
    friends_html = "".join([f"<li style='padding:5px;'>{f['friend']}</li>" for f in friends]) or "<li>No friends yet</li>"
    req_html = "".join([f"<li style='padding:5px;'>{r['req']} <a href=/accept/{r['req']} style='color:green;font-weight:bold;'>Accept</a></li>" for r in requests]) or "<li>No requests</li>"
    
    return render_template_string(get_header() + f'''
    <h2>👤 Me</h2>
    
    <div style="border:1px solid #ddd;padding:20px;border-radius:10px;margin-bottom:15px;background:white;">
        <h3>My Profile</h3>
        <p><b>Name:</b> {user['username']}</p>
        <p><b>Class:</b> {user['class']} | <b>Dept:</b> {user['dept']}</p>
        <p><b>Score:</b> ✅ {user['correct']} | ❌ {user['wrong']}</p>
        <p><b>Questions Left Today:</b> {20 - user['questions_used']}/20</p>
        <p><b>Lesson Access Until:</b> {user['lesson_expiry'][:10] if user['lesson_expiry'] else 'None'}</p>
    </div>
    
    <div style="border:1px solid #ddd;padding:20px;border-radius:10px;margin-bottom:15px;background:white;">
        <h3>Add Friend</h3>
        <form method=post action=/add_friend style="display:flex;gap:5px;">
            <input name=friend_username placeholder="Enter username" required style="flex:1;padding:8px;border:1px solid #ccc;border-radius:5px;">
            <button style="background:green;color:white;border:none;padding:8px 15px;border-radius:5px;">Send</button>
        </form>
        
        <h3 style="margin-top:15px;">Friend Requests</h3>
        <ul style="list-style:none;padding:0;">{req_html}</ul>
        
        <h3>My Friends</h3>
        <ul style="list-style:none;padding:0;">{friends_html}</ul>
    </div>
    
    <div style="border:1px solid #ddd;padding:20px;border-radius:10px;background:white;">
        <h3>Account</h3>
        <a href="/logout" style="background:red;color:white;padding:12px 25px;text-decoration:none;border-radius:5px;display:inline-block;font-weight:bold;">🚪 Logout</a>
    </div>
    {get_footer()}
    ''')

@app.route("/accept/<friend>")
@login_required
def accept(friend):
    conn = get_db()
    conn.execute("UPDATE friends SET status='accepted' WHERE user1=? AND user2=?", (friend, session['username']))
    conn.commit(); conn.close()
    flash(f"You are now friends with {friend}")
    return redirect(url_for('me'))

@app.route("/add_friend", methods=["POST"])
@login_required
def add_friend():
    friend = request.form['friend_username'].strip()
    conn=get_db()
    # Check if user exists
    u = conn.execute("SELECT * FROM users WHERE username=?", (friend,)).fetchone()
    if not u: 
        flash("User not found"); 
        conn.close()
        return redirect(url_for('me'))
    if friend == session['username']: 
        flash("You can't add yourself"); 
        conn.close()
        return redirect(url_for('me'))
    
    # Check if already friends or pending
    check = conn.execute("SELECT * FROM friends WHERE (user1=? AND user2=?) OR (user1=? AND user2=?)", 
                         (session['username'], friend, friend, session['username'])).fetchone()
    if check:
        flash("Request already sent or you are already friends")
    else:
        conn.execute("INSERT INTO friends(user1,user2,status) VALUES(?,?,?)", (session['username'], friend, 'pending'))
        flash(f"Friend request sent to {friend}")
    
    conn.commit(); conn.close()
    return redirect(url_for('me'))
# ========= GROUPED ADMIN PANEL =========
@app.route("/admin")
@admin_required
def admin():
    return render_template_string('''
    <style>
        body{font-family:Arial;background:#f1f5f9;margin:0;}
        .admin-container{padding:20px;max-width:1200px;margin:auto;}
        .group{border:2px solid #1e3a8a;margin:20px 0;padding:20px;border-radius:12px;background:white;}
        .group h2{background:#1e3a8a;color:white;padding:12px;border-radius:8px;margin-top:0;}
        .btn-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;margin-top:15px;}
        .btn{background:#2563eb;color:white;padding:14px;border:none;border-radius:6px;text-decoration:none;text-align:center;display:block;font-weight:bold;}
        .btn:hover{background:#1d4ed8;transform:scale(1.02);}
    </style>
    <div class="admin-container">
        <h1>🔒 Admin Panel</h1>
        <a href="/admin_logout" style="color:red;font-weight:bold;">Logout Admin</a>
        
        <!-- GROUP 1: CBT -->
        <div class="group">
            <h2>📝 GROUP 1: CBT - ADD QUESTIONS</h2>
            <div class="btn-grid">
                <a class="btn" href="/admin_add_question/JSS1/General">Add questions for JSS 1</a>
                <a class="btn" href="/admin_add_question/JSS2/General">Add questions for JSS 2</a>
                <a class="btn" href="/admin_add_question/JSS3/General">Add questions for JSS 3</a>
                <a class="btn" href="/admin_add_question/SSS1/Science">Add questions for SSS 1 Science</a>
                <a class="btn" href="/admin_add_question/SSS2/Science">Add questions for SSS 2 Science</a>
                <a class="btn" href="/admin_add_question/SSS3/Science">Add questions for SSS 3 Science</a>
                <a class="btn" href="/admin_add_question/SSS1/Commercial">Add questions for SSS 1 Commercial</a>
                <a class="btn" href="/admin_add_question/SSS2/Commercial">Add questions for SSS 2 Commercial</a>
                <a class="btn" href="/admin_add_question/SSS3/Commercial">Add questions for SSS 3 Commercial</a>
                <a class="btn" href="/admin_add_question/SSS1/Art">Add questions for SSS 1 Art</a>
                <a class="btn" href="/admin_add_question/SSS2/Art">Add questions for SSS 2 Art</a>
                <a class="btn" href="/admin_add_question/SSS3/Art">Add questions for SSS 3 Art</a>
            </div>
        </div>
        
        <!-- GROUP 2: LESSONS -->
        <div class="group">
            <h2>🎓 GROUP 2: LESSONS - POST LESSONS</h2>
            <div class="btn-grid">
                <a class="btn" href="/admin_add_lesson/JSS1/General">Add JSS 1 lesson</a>
                <a class="btn" href="/admin_add_lesson/JSS2/General">Add JSS 2 lesson</a>
                <a class="btn" href="/admin_add_lesson/JSS3/General">Add JSS 3 lesson</a>
                <a class="btn" href="/admin_add_lesson/SSS1/Science">Add SSS 1 Science lesson</a>
                <a class="btn" href="/admin_add_lesson/SSS2/Science">Add SSS 2 Science lesson</a>
                <a class="btn" href="/admin_add_lesson/SSS3/Science">Add SSS 3 Science lesson</a>
                <a class="btn" href="/admin_add_lesson/SSS1/Commercial">Add SSS 1 Commercial lesson</a>
                <a class="btn" href="/admin_add_lesson/SSS2/Commercial">Add SSS 2 Commercial lesson</a>
                <a class="btn" href="/admin_add_lesson/SSS3/Commercial">Add SSS 3 Commercial lesson</a>
                <a class="btn" href="/admin_add_lesson/SSS1/Art">Add SSS 1 Art lesson</a>
                <a class="btn" href="/admin_add_lesson/SSS2/Art">Add SSS 2 Art lesson</a>
                <a class="btn" href="/admin_add_lesson/SSS3/Art">Add SSS 3 Art lesson</a>
            </div>
        </div>
        
        <!-- GROUP 3: STUDENT MANAGEMENT -->
        <div class="group">
            <h2>👥 GROUP 3: STUDENT MANAGEMENT</h2>
            <div class="btn-grid">
                <a class="btn" href="/admin_confirm_payment">Confirm payment</a>
                <a class="btn" href="/admin_attendance">View attendance</a>
                <a class="btn" href="/admin_post_notice">Post notice</a>
            </div>
        </div>
        
        <!-- GROUP 4: SETTINGS -->
        <div class="group">
            <h2>🔒 GROUP 4: ADMIN SETTINGS</h2>
            <div class="btn-grid">
                <a class="btn" href="/admin_change_password">Change admin password</a>
            </div>
        </div>
    </div>
    ''')

@app.route("/admin_logout")
def admin_logout():
    session.pop('admin',None); return redirect(url_for('admin_login'))

# ========= ADMIN FUNCTIONS =========
@app.route("/admin_add_question/<class_>/<dept>", methods=["GET","POST"])
@admin_required
def admin_add_question(class_, dept):
    subjects = SUBJECTS.get(f"{class_}_{dept}", SUBJECTS.get(class_,[]))
    if request.method=="POST":
        conn=get_db()
        # FIXED: 10 columns = 10 placeholders
        conn.execute("INSERT INTO questions(class,dept,subject,question,opt_a,opt_b,opt_c,opt_d,answer,explanation) VALUES(?,?,?,?,?,?)",
            (class_,dept,request.form['subject'],request.form['question'],request.form['a'],request.form['b'],request.form['c'],request.form['d'],request.form['answer'],request.form['explanation']))
        conn.commit(); conn.close(); flash("Question Added Successfully")
        return redirect(url_for('admin'))
    subj_opt="".join([f"<option>{s}</option>" for s in subjects])
    return render_template_string(f'''
    <style>body{{padding:20px;font-family:Arial;background:#f8fafc;}} input,textarea,select{{width:100%;padding:8px;margin:5px 0;border:1px solid #ccc;border-radius:4px;}}</style>
    <h2>Add Question for {class_} {dept}</h2>
    <form method=post style="background:white;padding:20px;border-radius:8px;">
        Subject:<select name=subject>{subj_opt}</select><br>
        Question:<textarea name=question required rows=3></textarea><br>
        A:<input name=a required><br>
        B:<input name=b required><br>
        C:<input name=c required><br>
        D:<input name=d required><br>
        Answer:<select name=answer><option>A</option><option>B</option><option>C</option><option>D</option></select><br>
        Explanation:<textarea name=explanation rows=2></textarea><br>
        <button style="background:green;color:white;padding:10px;border:none;width:100%;">Post Question</button>
    </form>
    <a href=/admin>⬅️ Back to Admin</a>
    ''')

@app.route("/admin_add_lesson/<class_>/<dept>", methods=["GET","POST"])
@admin_required
def admin_add_lesson(class_, dept):
    subjects = SUBJECTS.get(f"{class_}_{dept}", SUBJECTS.get(class_,[]))
    if request.method=="POST":
        conn=get_db()
        conn.execute("INSERT INTO lessons(class,dept,subject,title,notes,video_link,created_at) VALUES(?,?,?,?,?,?,?)",
            (class_,dept,request.form['subject'],request.form['title'],request.form['notes'],request.form['video'],datetime.now().isoformat()))
        conn.commit(); conn.close(); flash("Lesson Added Successfully")
        return redirect(url_for('admin'))
    subj_opt="".join([f"<option>{s}</option>" for s in subjects])
    return render_template_string(f'''
    <style>body{{padding:20px;font-family:Arial;background:#f8fafc;}} input,textarea,select{{width:100%;padding:8px;margin:5px 0;border:1px solid #ccc;border-radius:4px;}}</style>
    <h2>Add Lesson for {class_} {dept}</h2>
    <form method=post style="background:white;padding:20px;border-radius:8px;">
        Subject:<select name=subject>{subj_opt}</select><br>
        Title:<input name=title required><br>
        Notes:<textarea name=notes rows=10 placeholder="Paste lesson content here"></textarea><br>
        Video Link (YouTube Embed):<input name=video placeholder="https://www.youtube.com/embed/..."><br>
        <button style="background:green;color:white;padding:10px;border:none;width:100%;">Post Lesson</button>
    </form>
    <a href=/admin>⬅️ Back to Admin</a>
    ''')

@app.route("/admin_confirm_payment")
@admin_required
def admin_confirm_payment():
    conn=get_db()
    pending=conn.execute("SELECT * FROM payments WHERE status='pending'").fetchall()
    conn.close()
    html="".join([f"<li style='padding:10px;border:1px solid #ddd;margin:5px 0;background:white;border-radius:5px;'>{p['username']} <a href=/approve/{p['id']} style='background:green;color:white;padding:5px 10px;text-decoration:none;float:right;'>Approve</a></li>" for p in pending])
    return render_template_string(f'<h2>Confirm Payment</h2><ul style="list-style:none;padding:0;">{html or "<li>No pending payments</li>"}</ul><a href=/admin>⬅️ Back</a>')

@app.route("/approve/<id>")
@admin_required
def approve(id):
    conn=get_db()
    p=conn.execute("SELECT * FROM payments WHERE id=?",(id,)).fetchone()
    if p:
        conn.execute("UPDATE payments SET status='approved' WHERE id=?",(id,))
        conn.execute("UPDATE users SET lesson_expiry=? WHERE username=?",((datetime.now()+timedelta(days=30)).isoformat(),p['username']))
    conn.commit(); conn.close()
    flash(f"Approved {p['username']} for 30 days")
    return redirect(url_for('admin_confirm_payment'))

@app.route("/admin_attendance")
@admin_required
def admin_attendance():
    conn=get_db(); data=conn.execute("SELECT * FROM attendance ORDER BY id DESC LIMIT 100").fetchall(); conn.close()
    html="".join([f"<tr><td>{a['username']}</td><td>{a['login_time'][:16].replace('T',' ')}</td></tr>" for a in data])
    return render_template_string(f'''
    <h2>Attendance Log - Last 100</h2>
    <table border=1 style="width:100%;border-collapse:collapse;background:white;"><tr style="background:#1e3a8a;color:white;"><th>Username</th><th>Login Time</th></tr>{html}</table>
    <a href=/admin>⬅️ Back</a>
    ''')

@app.route("/admin_post_notice", methods=["GET","POST"])
@admin_required
def admin_post_notice():
    if request.method=="POST":
        conn=get_db(); conn.execute("INSERT INTO notices(text,created_at) VALUES(?,?)",(request.form['text'],datetime.now().isoformat())); conn.commit(); conn.close(); flash("Notice Posted")
        return redirect(url_for('admin'))
    return render_template_string('<h2>Post School Notice</h2><form method=post style="background:white;padding:20px;border-radius:8px;"><textarea name=text rows=5 style="width:100%;" required></textarea><br><button style="background:#1e3a8a;color:white;padding:10px;">Send Notice</button></form><a href=/admin>⬅️ Back</a>')

@app.route("/admin_change_password", methods=["GET","POST"])
@admin_required
def admin_change_password():
    global ADMIN_PASSWORD_HASH
    if request.method=="POST":
        ADMIN_PASSWORD_HASH=generate_password_hash(request.form['password']); flash("Admin Password Changed")
        return redirect(url_for('admin'))
    return render_template_string('<h2>Change Admin Password</h2><form method=post style="background:white;padding:20px;border-radius:8px;">New Password:<input name=password type=password required><br><br><button>Change</button></form><a href=/admin>⬅️ Back</a>')

# ========= RUN =========
if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
