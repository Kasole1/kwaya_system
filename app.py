from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, timedelta
import sqlite3
import json
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'kwaya_bonifasi_system_2026'

DATABASE = 'kwaya.db'

# Create uploads folder if not exists
os.makedirs('static/uploads', exist_ok=True)
os.makedirs('static/images', exist_ok=True)

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # Meza ya wanakwaya
        conn.execute('''CREATE TABLE IF NOT EXISTS wanakwaya (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jina TEXT NOT NULL,
            simu TEXT NOT NULL,
            sauti TEXT,
            anwani TEXT,
            tarehe_jiunga DATE DEFAULT CURRENT_DATE,
            status TEXT DEFAULT 'active'
        )''')
        
        # Meza ya mahudhurio ya awali (simple)
        conn.execute('''CREATE TABLE IF NOT EXISTS mahudhurio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mwanakwaya_id INTEGER NOT NULL,
            tarehe DATE NOT NULL,
            alihudhuria BOOLEAN DEFAULT 1,
            FOREIGN KEY (mwanakwaya_id) REFERENCES wanakwaya(id)
        )''')
        
        # Meza ya ada
        conn.execute('''CREATE TABLE IF NOT EXISTS ada (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mwanakwaya_id INTEGER NOT NULL,
            kiasi REAL NOT NULL,
            mwezi TEXT NOT NULL,
            mwaka INTEGER NOT NULL,
            imelipwa BOOLEAN DEFAULT 0,
            FOREIGN KEY (mwanakwaya_id) REFERENCES wanakwaya(id)
        )''')
        
        # Meza ya mapato
        conn.execute('''CREATE TABLE IF NOT EXISTS mapato (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chanzo TEXT NOT NULL,
            kiasi REAL NOT NULL,
            maelezo TEXT,
            tarehe DATE DEFAULT CURRENT_DATE
        )''')
        
        # Meza ya ratiba (events)
        conn.execute('''CREATE TABLE IF NOT EXISTS ratiba (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tukio TEXT NOT NULL,
            tarehe DATE NOT NULL,
            mahali TEXT,
            maelezo TEXT
        )''')
        
        # Meza ya albamu
        conn.execute('''CREATE TABLE IF NOT EXISTS albamu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jina_albamu TEXT NOT NULL,
            mwaka INTEGER,
            nyimbo TEXT,
            maelezo TEXT
        )''')
        
        # Meza ya nyimbo (kwa ajili ya ratiba)
        conn.execute('''CREATE TABLE IF NOT EXISTS nyimbo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jina TEXT NOT NULL,
            mtunzi TEXT,
            maneno TEXT,
            key TEXT,
            time_signature TEXT,
            tempo TEXT,
            kundi TEXT NOT NULL,
            nota_pdf TEXT,
            midi_file TEXT,
            tarehe_ongezwa DATE DEFAULT CURRENT_DATE
        )''')
        
        # Meza ya watumiaji
        conn.execute('''CREATE TABLE IF NOT EXISTS watumiaji (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        )''')
        
        # Meza ya timetable zilizohifadhiwa
        conn.execute('''CREATE TABLE IF NOT EXISTS timetable_saved (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tukio TEXT NOT NULL,
            tarehe TEXT NOT NULL,
            jumapili_ngapi TEXT,
            mwaka_kanisa TEXT,
            data TEXT NOT NULL,
            tarehe_kuundwa DATE DEFAULT CURRENT_DATE
        )''')
        
        # ============ MEZA MPYA ZA MAHUDHURIO ============
        
        # Meza ya mahudhurio ya kina (tracking per event)
        conn.execute('''CREATE TABLE IF NOT EXISTS mahudhurio_detailed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mwanakwaya_id INTEGER NOT NULL,
            mwanakwaya_jina TEXT NOT NULL,
            sauti TEXT NOT NULL,
            tukio TEXT NOT NULL,
            tarehe DATE DEFAULT CURRENT_DATE,
            status TEXT DEFAULT 'absent',
            dakika_chelewa INTEGER DEFAULT 0,
            penalty REAL DEFAULT 0,
            imelipwa BOOLEAN DEFAULT 0,
            tarehe_penalty_double DATE,
            FOREIGN KEY (mwanakwaya_id) REFERENCES wanakwaya(id)
        )''')
        
        # Meza ya penalty settings per event type
        conn.execute('''CREATE TABLE IF NOT EXISTS penalty_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tukio TEXT UNIQUE NOT NULL,
            penalty_utoro REAL DEFAULT 20000,
            penalty_kwa_dakika REAL DEFAULT 1000,
            siku_za_kudouble INTEGER DEFAULT 10
        )''')
        
        # Meza ya tukio la sasa (current event being recorded)
        conn.execute('''CREATE TABLE IF NOT EXISTS current_event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tukio TEXT NOT NULL,
            tarehe DATE DEFAULT CURRENT_DATE
        )''')
        
        # Insert default penalty settings if not exists
        default_settings = [
            ('Misa', 20000, 1000, 10),
            ('Mazishi', 15000, 500, 10),
            ('Harusi', 25000, 1500, 10),
            ('Sherehe', 30000, 2000, 10),
            ('Mashindano', 50000, 3000, 10),
            ('Mazoezi', 5000, 500, 10),
            ('Mazoezi Ya Kwaya', 5000, 500, 10),
            ('Kwaya Ya Jumapili', 10000, 800, 10),
            ('Dominica', 10000, 800, 10)
        ]
        for setting in default_settings:
            conn.execute('''INSERT OR IGNORE INTO penalty_settings (tukio, penalty_utoro, penalty_kwa_dakika, siku_za_kudouble)
                        VALUES (?, ?, ?, ?)''', setting)
        
        # Check if current_event has data, if not add default
        current = conn.execute("SELECT * FROM current_event").fetchone()
        if not current:
            conn.execute("INSERT INTO current_event (tukio, tarehe) VALUES (?, date('now'))", ('Misa',))
        
        # Ongeza admin default
        admin = conn.execute("SELECT * FROM watumiaji WHERE username = 'admin'").fetchone()
        if not admin:
            conn.execute("INSERT INTO watumiaji (username, password, role) VALUES (?, ?, ?)",
                        ('admin', generate_password_hash('admin123'), 'admin'))
            print("✅ Admin created!")
        
        # Ongeza wanakwaya wa mfano kama hakuna
        waliopo = conn.execute("SELECT COUNT(*) as idadi FROM wanakwaya").fetchone()
        if waliopo['idadi'] == 0:
            wanakwaya_mfano = [
                ('Maria John', '0712345678', 'Soprano', 'Sombetini', 'active'),
                ('Anna Peter', '0723456789', 'Alto', 'Kijenge', 'active'),
                ('John Mushi', '0734567890', 'Tenor', 'Sombetini', 'active'),
                ('Peter Massawe', '0745678901', 'Bass', 'Kaloleni', 'active'),
                ('Esther Joseph', '0756789012', 'Soprano', 'Njiro', 'active'),
                ('Grace Lucy', '0767890123', 'Alto', 'Sombetini', 'active'),
                ('James Mboi', '0771234567', 'Tenor', 'Sekei', 'active'),
                ('Hadii Jane', '0781234567', 'Soprano', 'Themi', 'active'),
                ('John Kasole', '0791234567', 'Bass', 'Levolosi', 'active'),
            ]
            for w in wanakwaya_mfano:
                conn.execute("INSERT INTO wanakwaya (jina, simu, sauti, anwani, status) VALUES (?, ?, ?, ?, ?)", w)
        
        conn.commit()
        print("✅ Database ready!")

init_db()

# ============ AUTHENTICATION ROUTES ============

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        with get_db() as conn:
            user = conn.execute("SELECT * FROM watumiaji WHERE username = ?", (username,)).fetchone()
            
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                flash(f'Karibu {username}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Username au password si sahihi!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Umefanikiwa kutoka!', 'success')
    return redirect(url_for('login'))

# ============ DASHBOARD ============

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    with get_db() as conn:
        wanakwaya_count = conn.execute("SELECT COUNT(*) as count FROM wanakwaya WHERE status = 'active'").fetchone()
    
    return render_template('dashboard.html', 
                         wanakwaya_count=wanakwaya_count['count'],
                         username=session['username'])

# ============ KWAYA YETU ROUTES ============

@app.route('/kwaya_yetu/historia')
def historia_kwaya():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('historia_kwaya.html')

@app.route('/kwaya_yetu/somo_msimamizi')
def somo_msimamizi():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('somo_msimamizi.html')

@app.route('/kwaya_yetu/mwanzilishi')
def mwanzilishi():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('mwanzilishi.html')

@app.route('/kwaya_yetu/sifa/mwanakwaya')
def kuwa_mwanakwaya():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('sifa_vigezo.html')

@app.route('/kwaya_yetu/sifa/mwalimu')
def kuwa_mwalimu():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('sifa_vigezo.html')

@app.route('/kwaya_yetu/sifa/kiongozi')
def kuwa_kiongozi():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('sifa_vigezo.html')

@app.route('/kwaya_yetu/sifa/mfadhili')
def kuwa_mfadhili():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('sifa_vigezo.html')

@app.route('/kwaya_yetu/sifa/rafiki')
def kuwa_rafiki():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('sifa_vigezo.html')

@app.route('/kwaya_yetu/sifa/mlezi')
def kuwa_mlezi():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('sifa_vigezo.html')

@app.route('/kwaya_yetu/malengo/mfupi')
def malengo_mfupi():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('malengo.html')

@app.route('/kwaya_yetu/malengo/kati')
def malengo_kati():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('malengo.html')

@app.route('/kwaya_yetu/malengo/mrefu')
def malengo_mrefu():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('malengo.html')

@app.route('/mission')
def mission():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('mission_vision.html')

@app.route('/vision')
def vision():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('mission_vision.html')

@app.route('/core-values')
def core_values():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('mission_vision.html')

@app.route('/falsafa')
def falsafa():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('mission_vision.html')

@app.route('/principles')
def principles():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('mission_vision.html')

@app.route('/code-of-conduct')
def code_of_conduct():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('mission_vision.html')

@app.route('/weekly-calendar')
def weekly_calendar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('calendar.html')

@app.route('/monthly-calendar')
def monthly_calendar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('calendar.html')

@app.route('/yearly-calendar')
def yearly_calendar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('calendar.html')

# ============ API ROUTES FOR WANAKWAYA ============

@app.route('/api/wanakwaya')
def api_wanakwaya():
    if 'user_id' not in session:
        return jsonify([])
    
    with get_db() as conn:
        wanakwaya = conn.execute("SELECT * FROM wanakwaya ORDER BY id").fetchall()
        result = []
        for i, w in enumerate(wanakwaya):
            prefix = {'Soprano': 'S', 'Alto': 'A', 'Tenor': 'T', 'Bass': 'B'}.get(w['sauti'], 'X')
            voice_count = conn.execute("SELECT COUNT(*) as count FROM wanakwaya WHERE sauti = ? AND id <= ?", 
                                      (w['sauti'], w['id'])).fetchone()
            member_number = f"{prefix}{str(voice_count['count']).zfill(3)}"
            
            fees = conn.execute("SELECT SUM(kiasi) as total, SUM(CASE WHEN imelipwa=1 THEN kiasi ELSE 0 END) as paid FROM ada WHERE mwanakwaya_id = ?", 
                               (w['id'],)).fetchone()
            
            result.append({
                'id': w['id'],
                'jina': w['jina'],
                'simu': w['simu'],
                'sauti': w['sauti'],
                'anwani': w['anwani'],
                'tarehe_jiunga': w['tarehe_jiunga'],
                'member_number': member_number,
                'total_fees': fees['total'] or 0,
                'paid_fees': fees['paid'] or 0,
                'status': w['status'] if 'status' in w.keys() else 'active'
            })
        return jsonify(result)

@app.route('/api/wanakwaya/save', methods=['POST'])
def api_save_wanakwaya():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    member_id = request.form.get('member_id')
    jina = request.form['jina']
    simu = request.form['simu']
    sauti = request.form['sauti']
    anwani = request.form.get('anwani', '')
    
    with get_db() as conn:
        if member_id:
            conn.execute("UPDATE wanakwaya SET jina=?, simu=?, sauti=?, anwani=? WHERE id=?",
                        (jina, simu, sauti, anwani, member_id))
        else:
            conn.execute("INSERT INTO wanakwaya (jina, simu, sauti, anwani, status) VALUES (?, ?, ?, ?, 'active')",
                        (jina, simu, sauti, anwani))
        conn.commit()
    return jsonify({'success': True, 'message': 'Mwanakwaya amehifadhiwa kikamilifu'})

@app.route('/api/wanakwaya/suspend', methods=['POST'])
def api_suspend_wanakwaya():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.get_json()
    member_id = data.get('id')
    status = data.get('status')
    
    with get_db() as conn:
        conn.execute("UPDATE wanakwaya SET status = ? WHERE id = ?", (status, member_id))
        conn.commit()
    
    status_text = 'activated' if status == 'active' else 'suspended'
    return jsonify({'success': True, 'message': f'Mwanakwaya ame{status_text} kikamilifu', 'new_status': status})

@app.route('/api/get_wimbo/<int:id>')
def api_get_wimbo(id):
    if 'user_id' not in session:
        return jsonify({})
    
    with get_db() as conn:
        wimbo = conn.execute("SELECT * FROM nyimbo WHERE id = ?", (id,)).fetchone()
        if wimbo:
            return jsonify({
                'id': wimbo['id'],
                'jina': wimbo['jina'],
                'mtunzi': wimbo['mtunzi'],
                'key': wimbo['key'],
                'time_signature': wimbo['time_signature'],
                'tempo': wimbo['tempo'],
                'kundi': wimbo['kundi']
            })
    return jsonify({})

# ============ WANAKWAYA ROUTES ============

@app.route('/wanakwaya', methods=['GET', 'POST'])
def wanakwaya():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        jina = request.form['jina']
        simu = request.form['simu']
        sauti = request.form['sauti']
        anwani = request.form.get('anwani', '')
        
        with get_db() as conn:
            conn.execute("INSERT INTO wanakwaya (jina, simu, sauti, anwani, status) VALUES (?, ?, ?, ?, 'active')",
                        (jina, simu, sauti, anwani))
            conn.commit()
        flash('Mwanakwaya ameongezwa!', 'success')
        return redirect(url_for('wanakwaya'))
    
    with get_db() as conn:
        orodha = conn.execute("SELECT * FROM wanakwaya ORDER BY id DESC").fetchall()
    
    return render_template('wanakwaya.html', wanakwaya=orodha)

@app.route('/futa_mwanakwaya/<int:id>')
def futa_mwanakwaya(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    with get_db() as conn:
        conn.execute("DELETE FROM wanakwaya WHERE id = ?", (id,))
        conn.commit()
    flash('Mwanakwaya amefutwa!', 'success')
    return redirect(url_for('wanakwaya'))

@app.route('/edit_wanakwaya', methods=['POST'])
def edit_wanakwaya():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    wanakwaya_id = request.form['wanakwaya_id']
    jina = request.form['jina']
    simu = request.form['simu']
    sauti = request.form['sauti']
    anwani = request.form.get('anwani', '')
    
    with get_db() as conn:
        conn.execute("UPDATE wanakwaya SET jina = ?, simu = ?, sauti = ?, anwani = ? WHERE id = ?",
                    (jina, simu, sauti, anwani, wanakwaya_id))
        conn.commit()
    flash('Taarifa za mwanakwaya zimehaririwa!', 'success')
    return redirect(url_for('wanakwaya'))

# ============ MAHUDHURIO ROUTES (SIMPLE) ============

@app.route('/mahudhurio_simple', methods=['GET', 'POST'])
def mahudhurio_simple():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    tarehe_leo = datetime.now().strftime('%Y-%m-%d')
    
    if request.method == 'POST':
        mwanakwaya_id = request.form['mwanakwaya_id']
        tarehe = request.form['tarehe']
        
        with get_db() as conn:
            kipo = conn.execute("SELECT * FROM mahudhurio WHERE mwanakwaya_id = ? AND tarehe = ?",
                               (mwanakwaya_id, tarehe)).fetchone()
            if not kipo:
                conn.execute("INSERT INTO mahudhurio (mwanakwaya_id, tarehe) VALUES (?, ?)",
                           (mwanakwaya_id, tarehe))
                conn.commit()
                flash('Mahudhurio yamerekodiwa!', 'success')
            else:
                flash('Mwanakwaya huyo amesharekodiwa kwa tarehe hii!', 'info')
        
        return redirect(url_for('mahudhurio_simple'))
    
    with get_db() as conn:
        wanakwaya = conn.execute("SELECT * FROM wanakwaya WHERE status = 'active'").fetchall()
        mahudhurio_leo = conn.execute('''SELECT m.*, w.jina FROM mahudhurio m 
                                        JOIN wanakwaya w ON m.mwanakwaya_id = w.id 
                                        WHERE m.tarehe = ? ORDER BY w.jina''', (tarehe_leo,)).fetchall()
    
    return render_template('mahudhurio_simple.html', 
                         wanakwaya=wanakwaya, 
                         mahudhurio=mahudhurio_leo,
                         tarehe_leo=tarehe_leo)

# ============ MAHUDHURIO DETAILED ROUTES (ENHANCED) ============

@app.route('/mahudhurio')
def mahudhurio_enhanced():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    with get_db() as conn:
        # Get current event
        current_event = conn.execute("SELECT * FROM current_event ORDER BY id DESC LIMIT 1").fetchone()
        if not current_event:
            current_event = {'tukio': 'Misa', 'tarehe': datetime.now().strftime('%Y-%m-%d')}
        
        # Get all penalty settings
        penalty_settings = conn.execute("SELECT * FROM penalty_settings").fetchall()
        
        # Get all active members by voice
        wanakwaya_soprano = conn.execute("SELECT * FROM wanakwaya WHERE sauti = 'Soprano' AND status = 'active' ORDER BY jina").fetchall()
        wanakwaya_alto = conn.execute("SELECT * FROM wanakwaya WHERE sauti = 'Alto' AND status = 'active' ORDER BY jina").fetchall()
        wanakwaya_tenor = conn.execute("SELECT * FROM wanakwaya WHERE sauti = 'Tenor' AND status = 'active' ORDER BY jina").fetchall()
        wanakwaya_bass = conn.execute("SELECT * FROM wanakwaya WHERE sauti = 'Bass' AND status = 'active' ORDER BY jina").fetchall()
        
        # Get today's attendance records for this event
        today = datetime.now().strftime('%Y-%m-%d')
        attendance = {}
        records = conn.execute('''SELECT * FROM mahudhurio_detailed 
                                  WHERE tarehe = ? AND tukio = ?''', 
                               (today, current_event['tukio'])).fetchall()
        for rec in records:
            attendance[rec['mwanakwaya_id']] = {
                'status': rec['status'],
                'dakika_chelewa': rec['dakika_chelewa'],
                'penalty': rec['penalty']
            }
    
    return render_template('mahudhurio.html', 
                         soprano=wanakwaya_soprano,
                         alto=wanakwaya_alto,
                         tenor=wanakwaya_tenor,
                         bass=wanakwaya_bass,
                         current_event=current_event,
                         penalty_settings=penalty_settings,
                         attendance=attendance)

@app.route('/api/mahudhurio/update', methods=['POST'])
def api_update_attendance():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.get_json()
    member_id = data.get('member_id')
    status = data.get('status')
    dakika_chelewa = data.get('dakika_chelewa', 0)
    tukio = data.get('tukio')
    member_name = data.get('member_name')
    sauti = data.get('sauti')
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Get penalty settings for this event
    with get_db() as conn:
        settings = conn.execute("SELECT * FROM penalty_settings WHERE tukio = ?", (tukio,)).fetchone()
        if not settings:
            settings = {'penalty_utoro': 20000, 'penalty_kwa_dakika': 1000, 'siku_za_kudouble': 10}
        
        # Calculate penalty
        penalty = 0
        if status == 'absent':
            penalty = settings['penalty_utoro']
        elif status == 'late':
            penalty = dakika_chelewa * settings['penalty_kwa_dakika']
        
        # Calculate double penalty date
        double_date = (datetime.now() + timedelta(days=settings['siku_za_kudouble'])).strftime('%Y-%m-%d')
        
        # Check if record exists
        existing = conn.execute('''SELECT * FROM mahudhurio_detailed 
                                   WHERE mwanakwaya_id = ? AND tarehe = ? AND tukio = ?''',
                               (member_id, today, tukio)).fetchone()
        
        if existing:
            conn.execute('''UPDATE mahudhurio_detailed 
                            SET status = ?, dakika_chelewa = ?, penalty = ?, tarehe_penalty_double = ?
                            WHERE mwanakwaya_id = ? AND tarehe = ? AND tukio = ?''',
                        (status, dakika_chelewa, penalty, double_date, member_id, today, tukio))
        else:
            conn.execute('''INSERT INTO mahudhurio_detailed 
                            (mwanakwaya_id, mwanakwaya_jina, sauti, tukio, tarehe, status, dakika_chelewa, penalty, tarehe_penalty_double)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (member_id, member_name, sauti, tukio, today, status, dakika_chelewa, penalty, double_date))
        
        conn.commit()
    
    return jsonify({'success': True, 'penalty': penalty, 'double_date': double_date})

@app.route('/api/mahudhurio/settings/update', methods=['POST'])
def api_update_penalty_settings():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.get_json()
    tukio = data.get('tukio')
    penalty_utoro = data.get('penalty_utoro')
    penalty_kwa_dakika = data.get('penalty_kwa_dakika')
    siku_za_kudouble = data.get('siku_za_kudouble')
    
    with get_db() as conn:
        conn.execute('''INSERT OR REPLACE INTO penalty_settings 
                        (tukio, penalty_utoro, penalty_kwa_dakika, siku_za_kudouble)
                        VALUES (?, ?, ?, ?)''',
                    (tukio, penalty_utoro, penalty_kwa_dakika, siku_za_kudouble))
        conn.commit()
    
    return jsonify({'success': True})

@app.route('/api/mahudhurio/event/update', methods=['POST'])
def api_update_current_event():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.get_json()
    tukio = data.get('tukio')
    tarehe = data.get('tarehe')
    
    with get_db() as conn:
        conn.execute("DELETE FROM current_event")
        conn.execute("INSERT INTO current_event (tukio, tarehe) VALUES (?, ?)", (tukio, tarehe))
        conn.commit()
    
    return jsonify({'success': True})

@app.route('/api/mahudhurio/member/<int:id>')
def api_get_member_attendance(id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    with get_db() as conn:
        # Get member details
        member = conn.execute("SELECT * FROM wanakwaya WHERE id = ?", (id,)).fetchone()
        
        # Get all attendance records for this member
        records = conn.execute('''SELECT * FROM mahudhurio_detailed 
                                  WHERE mwanakwaya_id = ? 
                                  ORDER BY tarehe DESC''', (id,)).fetchall()
        
        # Calculate total penalty and days remaining
        total_penalty = 0
        for rec in records:
            if not rec['imelipwa']:
                total_penalty += rec['penalty']
        
        # Check if should be suspended (30 days without payment)
        last_penalty_date = None
        if records:
            last_penalty_date = records[0]['tarehe']
            days_since = (datetime.now() - datetime.strptime(last_penalty_date, '%Y-%m-%d')).days
        else:
            days_since = 0
        
        records_list = []
        for rec in records:
            records_list.append({
                'id': rec['id'],
                'tukio': rec['tukio'],
                'tarehe': rec['tarehe'],
                'status': rec['status'],
                'dakika_chelewa': rec['dakika_chelewa'],
                'penalty': rec['penalty'],
                'imelipwa': rec['imelipwa'],
                'double_date': rec['tarehe_penalty_double']
            })
        
        return jsonify({
            'success': True,
            'member': {
                'id': member['id'],
                'jina': member['jina'],
                'sauti': member['sauti'],
                'status': member['status']
            },
            'records': records_list,
            'total_penalty': total_penalty,
            'days_since_last_penalty': days_since,
            'should_be_suspended': days_since >= 30 and total_penalty > 0
        })

@app.route('/api/mahudhurio/pay/<int:id>', methods=['POST'])
def api_pay_penalty(id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    with get_db() as conn:
        conn.execute("UPDATE mahudhurio_detailed SET imelipwa = 1 WHERE id = ?", (id,))
        conn.commit()
    
    return jsonify({'success': True})

# ============ RATIBA EVENTS ROUTES ============

@app.route('/ratiba_events', methods=['GET', 'POST'])
def ratiba_events():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        tukio = request.form['tukio']
        tarehe = request.form['tarehe']
        mahali = request.form.get('mahali', '')
        maelezo = request.form.get('maelezo', '')
        
        with get_db() as conn:
            conn.execute("INSERT INTO ratiba (tukio, tarehe, mahali, maelezo) VALUES (?, ?, ?, ?)",
                        (tukio, tarehe, mahali, maelezo))
            conn.commit()
        flash('Ratiba imeongezwa!', 'success')
        return redirect(url_for('ratiba_events'))
    
    with get_db() as conn:
        orodha = conn.execute("SELECT * FROM ratiba WHERE tarehe >= DATE('now') ORDER BY tarehe ASC").fetchall()
    
    return render_template('ratiba_events.html', ratiba=orodha)

# ============ ADA ROUTES ============

@app.route('/ada', methods=['GET', 'POST'])
def ada():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        mwanakwaya_id = request.form['mwanakwaya_id']
        kiasi = request.form['kiasi']
        mwezi = request.form['mwezi']
        mwaka = request.form['mwaka']
        
        with get_db() as conn:
            conn.execute("INSERT INTO ada (mwanakwaya_id, kiasi, mwezi, mwaka) VALUES (?, ?, ?, ?)",
                        (mwanakwaya_id, kiasi, mwezi, mwaka))
            conn.commit()
        flash('Ada imeongezwa!', 'success')
        return redirect(url_for('ada'))
    
    with get_db() as conn:
        wanakwaya = conn.execute("SELECT * FROM wanakwaya WHERE status = 'active'").fetchall()
        orodha_ada = conn.execute('''SELECT a.*, w.jina FROM ada a 
                                    JOIN wanakwaya w ON a.mwanakwaya_id = w.id 
                                    ORDER BY a.id DESC''').fetchall()
    
    return render_template('ada.html', wanakwaya=wanakwaya, ada=orodha_ada)

@app.route('/lipa_ada/<int:id>')
def lipa_ada(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    with get_db() as conn:
        conn.execute("UPDATE ada SET imelipwa = 1 WHERE id = ?", (id,))
        conn.commit()
    flash('Ada imelipwa kikamilifu!', 'success')
    return redirect(url_for('ada'))

# ============ MAPATO ROUTES ============

@app.route('/mapato', methods=['GET', 'POST'])
def mapato():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        chanzo = request.form['chanzo']
        kiasi = request.form['kiasi']
        maelezo = request.form.get('maelezo', '')
        
        with get_db() as conn:
            conn.execute("INSERT INTO mapato (chanzo, kiasi, maelezo) VALUES (?, ?, ?)",
                        (chanzo, kiasi, maelezo))
            conn.commit()
        flash('Mapato yameongezwa!', 'success')
        return redirect(url_for('mapato'))
    
    with get_db() as conn:
        orodha = conn.execute("SELECT * FROM mapato ORDER BY tarehe DESC").fetchall()
        jumla = conn.execute("SELECT SUM(kiasi) as jumla FROM mapato").fetchone()
    
    return render_template('mapato.html', mapato=orodha, jumla=jumla['jumla'] or 0)

# ============ ALBAMU ROUTES ============

@app.route('/albamu', methods=['GET', 'POST'])
def albamu():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        jina_albamu = request.form['jina_albamu']
        mwaka = request.form['mwaka']
        nyimbo = request.form.get('nyimbo', '')
        maelezo = request.form.get('maelezo', '')
        
        with get_db() as conn:
            conn.execute("INSERT INTO albamu (jina_albamu, mwaka, nyimbo, maelezo) VALUES (?, ?, ?, ?)",
                        (jina_albamu, mwaka, nyimbo, maelezo))
            conn.commit()
        flash('Albamu imeongezwa!', 'success')
        return redirect(url_for('albamu'))
    
    with get_db() as conn:
        orodha = conn.execute("SELECT * FROM albamu ORDER BY mwaka DESC").fetchall()
    
    return render_template('albamu.html', albamu=orodha)

# ============ UONGOZI, KAMATI KUU, ASSETS ============

@app.route('/uongozi')
def uongozi():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('uongozi.html')

@app.route('/kamati_kuu')
def kamati_kuu():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('kamati_kuu.html')

@app.route('/assets')
def assets():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('assets.html')

# ============ RATIBA YA NYIMBO ROUTES ============

@app.route('/ratiba/mwaka/<mwaka>')
def ratiba_mwaka_kanisa(mwaka):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('mwaka_kanisa.html', mwaka=mwaka)

@app.route('/ratiba/makundi/<kundi>')
def ratiba_makundi_nyimbo(kundi):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    with get_db() as conn:
        nyimbo = conn.execute("SELECT * FROM nyimbo WHERE kundi = ? ORDER BY id DESC", (kundi,)).fetchall()
    
    return render_template('makundi_nyimbo.html', kundi=kundi, nyimbo=nyimbo)

@app.route('/ratiba/tengeneza')
def ratiba_tengeneza():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    with get_db() as conn:
        makundi_yote = ['Mwanzo', 'Shangilio', 'Zaburi', 'Maandamano', 'Misa', 
                        'Antifona', 'Sadaka', 'Komunyo', 'Shukrani', 'Mwisho']
        nyimbo_kwa_kundi = {}
        for k in makundi_yote:
            nyimbo_kwa_kundi[k] = conn.execute("SELECT id, jina FROM nyimbo WHERE kundi = ? ORDER BY jina", (k,)).fetchall()
    
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('tengeneza_ratiba.html', nyimbo_kwa_kundi=nyimbo_kwa_kundi, today=today)

@app.route('/ratiba/ongezwa_wimbo', methods=['GET', 'POST'])
def ratiba_ongezwa_wimbo():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        jina = request.form['jina']
        mtunzi = request.form.get('mtunzi', '')
        maneno = request.form.get('maneno', '')
        key = request.form.get('key', '')
        time_signature = request.form.get('time_signature', '')
        tempo = request.form.get('tempo', '')
        kundi = request.form['kundi']
        
        nota_pdf = ''
        midi_file = ''
        
        if 'nota_pdf' in request.files and request.files['nota_pdf'].filename:
            nota_pdf = request.files['nota_pdf'].filename
            request.files['nota_pdf'].save(f'static/uploads/{nota_pdf}')
        
        if 'midi_file' in request.files and request.files['midi_file'].filename:
            midi_file = request.files['midi_file'].filename
            request.files['midi_file'].save(f'static/uploads/{midi_file}')
        
        with get_db() as conn:
            conn.execute('''INSERT INTO nyimbo (jina, mtunzi, maneno, key, time_signature, tempo, kundi, nota_pdf, midi_file)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (jina, mtunzi, maneno, key, time_signature, tempo, kundi, nota_pdf, midi_file))
            conn.commit()
        
        flash('Wimbo umeongezwa kikamilifu!', 'success')
        return redirect(url_for('ratiba_makundi_nyimbo', kundi=kundi))
    
    return render_template('ongezwa_wimbo.html')

@app.route('/ratiba/wimbo/<int:id>')
def ratiba_view_wimbo(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    with get_db() as conn:
        wimbo = conn.execute("SELECT * FROM nyimbo WHERE id = ?", (id,)).fetchone()
    
    return render_template('view_wimbo.html', wimbo=wimbo)

@app.route('/ratiba/futa_wimbo/<int:id>')
def ratiba_futa_wimbo(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    with get_db() as conn:
        wimbo = conn.execute("SELECT kundi FROM nyimbo WHERE id = ?", (id,)).fetchone()
        kundi = wimbo['kundi']
        conn.execute("DELETE FROM nyimbo WHERE id = ?", (id,))
        conn.commit()
    
    flash('Wimbo umefutwa!', 'success')
    return redirect(url_for('ratiba_makundi_nyimbo', kundi=kundi))

# ============ API ROUTES FOR TIMETABLE ============

@app.route('/api/generate_timetable_v2', methods=['POST'])
def generate_timetable_v2():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.get_json()
    timetable = []
    
    section_names = {
        'mwanzo': 'MWANZO',
        'kyrie': 'KYRIE',
        'gloria': 'GLORIA',
        'sanctus': 'SANCTUS',
        'agnus': 'AGNUS DEI',
        'shangilio': 'SHANGILIO',
        'zaburi': 'ZABURI',
        'sadaka': 'SADAKA',
        'komunyo': 'KOMUNYO',
        'shukrani': 'SHUKRANI',
        'mwisho': 'MWISHO'
    }
    
    songs_data = data.get('songsData', {})
    
    with get_db() as conn:
        for section, songs in songs_data.items():
            if songs and len(songs) > 0:
                for idx, song in enumerate(songs):
                    if 'mtunzi' in song and song['mtunzi']:
                        timetable.append({
                            'section': section,
                            'sehemu': section_names.get(section, section),
                            'wimbo_id': song['id'],
                            'wimbo_jina': song['jina'],
                            'number': idx + 1,
                            'mtunzi': song.get('mtunzi', '-'),
                            'key': song.get('key', '-'),
                            'time_sig': song.get('time_sig', '-'),
                            'tempo': song.get('tempo', '-')
                        })
                    else:
                        wimbo = conn.execute("SELECT jina, mtunzi, key, time_signature, tempo FROM nyimbo WHERE id = ?", (song['id'],)).fetchone()
                        if wimbo:
                            timetable.append({
                                'section': section,
                                'sehemu': section_names.get(section, section),
                                'wimbo_id': song['id'],
                                'wimbo_jina': song['jina'],
                                'number': idx + 1,
                                'mtunzi': wimbo['mtunzi'] or '-',
                                'key': wimbo['key'] or '-',
                                'time_sig': wimbo['time_signature'] or '-',
                                'tempo': wimbo['tempo'] or '-'
                            })
    
    tukio = data.get('tukio', '')
    tarehe = data.get('tarehe', '')
    jumapili = data.get('jumapili', '')
    mwaka = data.get('mwaka', '')
    tukio_text = data.get('tukioText', '')
    
    with get_db() as conn:
        conn.execute('''INSERT INTO timetable_saved (tukio, tarehe, jumapili_ngapi, mwaka_kanisa, data)
                    VALUES (?, ?, ?, ?, ?)''',
                    (tukio_text, tarehe, jumapili, mwaka, json.dumps(timetable)))
        conn.commit()
    
    return jsonify({'success': True, 'timetable': timetable, 'tukio_text': tukio_text, 'tarehe': tarehe})

@app.route('/api/generate_timetable', methods=['POST'])
def generate_timetable():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.get_json()
    timetable = []
    
    section_names = {
        'mwanzo': 'MWANZO',
        'kyrie': 'KYRIE',
        'gloria': 'GLORIA',
        'sanctus': 'SANCTUS',
        'agnus': 'AGNUS DEI',
        'shangilio': 'SHANGILIO',
        'zaburi': 'ZABURI',
        'sadaka': 'SADAKA',
        'komunyo': 'KOMUNYO',
        'shukrani': 'SHUKRANI',
        'mwisho': 'MWISHO'
    }
    
    with get_db() as conn:
        for section, songs in data.items():
            if songs and len(songs) > 0:
                for idx, song in enumerate(songs):
                    wimbo = conn.execute("SELECT jina, mtunzi, key, time_signature, tempo FROM nyimbo WHERE id = ?", (song['id'],)).fetchone()
                    if wimbo:
                        timetable.append({
                            'section': section,
                            'sehemu': section_names.get(section, section),
                            'wimbo_id': song['id'],
                            'wimbo_jina': song['jina'],
                            'number': idx + 1,
                            'mtunzi': wimbo['mtunzi'] or '-',
                            'key': wimbo['key'] or '-',
                            'time_sig': wimbo['time_signature'] or '-',
                            'tempo': wimbo['tempo'] or '-'
                        })
    
    return jsonify({'success': True, 'timetable': timetable})

# ============ VIEW ONLY ROUTE ============

@app.route('/ratiba/view_only')
def ratiba_view_only():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('view_only_timetable.html')

# ============ RUN APP ============

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 MFUMO WA KWAYA MT. BONIFASI")
    print("📍 http://127.0.0.1:5000")
    print("👤 admin | 🔑 admin123")
    print("="*50 + "\n")
    app.run(debug=True, port=5000)