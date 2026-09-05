import sqlite3
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'afirmasi.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS journals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            energy_before TEXT DEFAULT '',
            mood_before TEXT DEFAULT '',
            affirmation TEXT NOT NULL,
            action_plan TEXT DEFAULT '',
            energy_after TEXT DEFAULT '',
            mood_after TEXT DEFAULT '',
            gratitude_before TEXT DEFAULT '',
            gratitude_after TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

ENERGY_LEVELS = [
    ('low', 'Rendah 💧'),
    ('medium', 'Sedang ⚡'),
    ('high', 'Tinggi 🌟'),
]

MOOD_LEVELS = [
    ('sad', 'Sedih 🌧️'),
    ('neutral', 'Netral ⚪'),
    ('happy', 'Senang ☀️'),
    ('excited', 'Bersemangat 🔥'),
]

AFFIRMATIONS = [
    "Aku adalah magnet bagi hal-hal bagus dalam hidupku.",
    "Setiap hari membawa peluang baru untuk bertumbuh.",
    "Aku berhasil dan layak menerima kebahagiaan.",
    "Energi positif mengalir ke dalam dan keluar dari tubuhku.",
    "Aku bersyukur atas semua yang telah kudapat hari ini.",
    "Aku mampu dan kuat untuk menaklukkan setiap tantangan.",
    "Hari ini aku memilih untuk bahagia dan bersyukur.",
    "Aku menarik keberkahan dan kebahagiaan ke dalam hidupku.",
    "Setiap langkah kecilku mengarah ke arah yang lebih baik.",
    "Aku adalah pencipta kebahagiaan dan ketenangan dalam hidupku.",
]

@app.route('/')
def index():
    conn = get_db()
    c = conn.cursor()

    filter_type = request.args.get('filter', 'all')
    sort = request.args.get('sort', 'desc')
    search = request.args.get('search', '')

    query = "SELECT * FROM journals WHERE 1=1"
    params = []

    if filter_type != 'all':
        query += " AND energy_before = ?"
        params.append(filter_type)

    if search:
        query += " AND (affirmation LIKE ? OR action_plan LIKE ? OR gratitude_before LIKE ? OR gratitude_after LIKE ?)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term, search_term])

    order = "DESC" if sort == "desc" else "ASC"
    query += f" ORDER BY created_at {order}"

    c.execute(query, params)
    entries = c.fetchall()

    conn.close()
    return render_template(
        'index.html',
        entries=entries,
        energy_levels=ENERGY_LEVELS,
        mood_levels=MOOD_LEVELS,
        affirmations=AFFIRMATIONS,
        active_filter=filter_type,
        search_term=search,
        sort=sort
    )

@app.route('/add', methods=['POST'])
def add_journal():
    try:
        conn = get_db()
        c = conn.cursor()

        energy_before = request.form.get('energy_before', '')
        mood_before = request.form.get('mood_before', '')
        affirmation = request.form.get('affirmation', '').strip()
        custom_affirmation = request.form.get('custom_affirmation', '').strip()
        action_plan = request.form.get('action_plan', '').strip()
        energy_after = request.form.get('energy_after', energy_before)
        mood_after = request.form.get('mood_after', mood_before)
        gratitude_before = request.form.get('gratitude_before', '').strip()
        gratitude_after = request.form.get('gratitude_after', '').strip()

        final_affirmation = custom_affirmation if custom_affirmation else affirmation

        if not final_affirmation:
            flash('Silakan tuliskan (atau pilih) afirmasi energi positif!', 'error')
            return redirect(url_for('index'))

        today = datetime.now().strftime('%Y-%m-%d')

        c.execute('''
            INSERT INTO journals (date, energy_before, mood_before, affirmation, action_plan,
                energy_after, mood_after, gratitude_before, gratitude_after)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            today, energy_before, mood_before, final_affirmation, action_plan,
            energy_after, mood_after, gratitude_before, gratitude_after
        ))
        conn.commit()
        conn.close()

        flash('Jurnal berhasil disimpan! ✨', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/journal/<int:journal_id>')
def view_journal(journal_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM journals WHERE id = ?", (journal_id,))
    entry = c.fetchone()
    conn.close()

    if entry is None:
        flash('Jurnal tidak ditemukan.', 'error')
        return redirect(url_for('index'))

    return render_template('view.html', entry=entry, energy_levels=ENERGY_LEVELS, mood_levels=MOOD_LEVELS)

@app.route('/delete/<int:journal_id>', methods=['POST'])
def delete_journal(journal_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM journals WHERE id = ?", (journal_id,))
    conn.commit()
    conn.close()
    flash('Jurnal dihapus.', 'success')
    return redirect(url_for('index'))

@app.route('/api/stats')
def api_stats():
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) as count FROM journals")
    total = c.fetchone()['count']

    c.execute('''
        SELECT strftime('%Y-%m', date) as month, COUNT(*) as count
        FROM journals
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
    ''')
    monthly = [dict(row) for row in c.fetchall()]

    conn.close()
    return jsonify({'total': total, 'monthly': monthly})

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5007, debug=True, use_reloader=False)