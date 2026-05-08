from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'kwaya_bonifasi_system_2026'

DATABASE = 'kwaya.db'

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
            tarehe_jiunga DATE DEFAULT CURRENT_DATE
        )''')
        
        # Add status column if not exists
        try:
            conn.execute("ALTER TABLE wanakwaya ADD COLUMN status TEXT DEFAULT 'active'")
        except:
            pass
        
        # Meza ya mahudhurio
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
        
        # Meza ya ratiba
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
        
        # Meza ya watumiaji
        conn.execute('''CREATE TABLE IF NOT EXISTS watumiaji (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        )''')
        
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
                ('Maria John', '0712345678', 'Soprano', 'Sombetini, Arusha', 'active'),
                ('Anna Peter', '0723456789', 'Alto', 'Kijenge, Arusha', 'active'),
                ('John Mushi', '0734567890', 'Tenor', 'Sombetini, Arusha', 'active'),
                ('Peter Massawe', '0745678901', 'Bass', 'Kaloleni, Arusha', 'active'),
                ('Esther Joseph', '0756789012', 'Soprano', 'Njiro, Arusha', 'active'),
                ('Grace Lucy', '0767890123', 'Alto', 'Sombetini, Arusha', 'active'),
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
        wanakwaya_count = conn.execute("SELECT COUNT(*) as count FROM wanakwaya").fetchone()
    
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

# Sifa/Vigezo - All in one page with tabs
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

# Malengo - All in one page with tabs
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

# ============ MISSION & VISION ============

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

# ============ CALENDAR ROUTES ============

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
        try:
            conn.execute("ALTER TABLE wanakwaya ADD COLUMN status TEXT DEFAULT 'active'")
        except:
            pass
        conn.execute("UPDATE wanakwaya SET status = ? WHERE id = ?", (status, member_id))
        conn.commit()
    
    status_text = 'activated' if status == 'active' else 'suspended'
    return jsonify({'success': True, 'message': f'Mwanakwaya ame{status_text} kikamilifu', 'new_status': status})

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

# ============ MAHUDHURIO ROUTES ============

@app.route('/mahudhurio', methods=['GET', 'POST'])
def mahudhurio():
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
        
        return redirect(url_for('mahudhurio'))
    
    with get_db() as conn:
        wanakwaya = conn.execute("SELECT * FROM wanakwaya WHERE status = 'active'").fetchall()
        mahudhurio_leo = conn.execute('''SELECT m.*, w.jina FROM mahudhurio m 
                                        JOIN wanakwaya w ON m.mwanakwaya_id = w.id 
                                        WHERE m.tarehe = ? ORDER BY w.jina''', (tarehe_leo,)).fetchall()
    
    return render_template('mahudhurio.html', 
                         wanakwaya=wanakwaya, 
                         mahudhurio=mahudhurio_leo,
                         tarehe_leo=tarehe_leo)

# ============ RATIBA ROUTES ============

@app.route('/ratiba', methods=['GET', 'POST'])
def ratiba():
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
        return redirect(url_for('ratiba'))
    
    with get_db() as conn:
        orodha = conn.execute("SELECT * FROM ratiba WHERE tarehe >= DATE('now') ORDER BY tarehe ASC").fetchall()
    
    return render_template('ratiba.html', ratiba=orodha)

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

# ============ RUN APP ============

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 MFUMO WA KWAYA MT. BONIFASI")
    print("📍 http://127.0.0.1:5000")
    print("👤 admin | 🔑 admin123")
    print("="*50 + "\n")
    app.run(debug=True, port=5000)