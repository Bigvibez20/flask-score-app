from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'yoursecretkey'

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ----------------------------
# DATABASE INITIALIZATION
# ----------------------------
def init_db():
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                coach TEXT,
                logo TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                team_id INTEGER,
                goals INTEGER,
                medals TEXT,
                is_captain INTEGER,
                position TEXT,
                photo TEXT,
                FOREIGN KEY(team_id) REFERENCES teams(id)
            )
        ''')
        cursor.execute("SELECT * FROM admin WHERE username = 'admin'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO admin (username, password) VALUES (?, ?)", ('admin', 'password'))
        conn.commit()

# ----------------------------
# HOME PAGE (VIEWER)
# ----------------------------
@app.route('/')
def home():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM teams")
    teams = cursor.fetchall()

    team_data = []
    for team in teams:
        team_dict = {
            'id': team[0],
            'name': team[1],
            'coach': team[2],
            'logo': team[3] if len(team) > 3 else None
        }
        cursor.execute("SELECT * FROM players WHERE team_id=?", (team[0],))
        players = cursor.fetchall()
        player_list = []
        for p in players:
            player_dict = {
                'id': p[0],
                'name': p[1],
                'team_id': p[2],
                'goals': p[3],
                'medals': p[4],
                'is_captain': p[5],
                'position': p[6],
                'photo': p[7]
            }
            player_list.append(player_dict)
        team_dict['players'] = player_list
        team_data.append(team_dict)

    conn.close()
    return render_template('home.html', team_data=team_data)

# ----------------------------
# LOGIN
# ----------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pw = request.form['password']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin WHERE username=? AND password=?", (user, pw))
        admin = cursor.fetchone()
        conn.close()
        if admin:
            session['admin'] = True
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid login.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('home'))

# ----------------------------
# DASHBOARD
# ----------------------------
@app.route('/dashboard')
def dashboard():
    if not session.get('admin'):
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# ----------------------------
# MANAGE TEAMS
# ----------------------------
@app.route('/manage_teams', methods=['GET', 'POST'])
def manage_teams():
    if not session.get('admin'):
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        coach = request.form['coach']
        logo_file = request.files.get('logo')
        logo_filename = None

        if logo_file:
            logo_filename = secure_filename(logo_file.filename)
            logo_path = os.path.join(app.config['UPLOAD_FOLDER'], logo_filename)
            logo_file.save(logo_path)

        cursor.execute("INSERT INTO teams (name, coach, logo) VALUES (?, ?, ?)", (name, coach, logo_filename))
        conn.commit()

    cursor.execute("SELECT * FROM teams")
    teams = cursor.fetchall()
    conn.close()
    return render_template('manage_teams.html', teams=teams)

@app.route('/edit_team/<int:team_id>', methods=['POST'])
def edit_team(team_id):
    if not session.get('admin'):
        return redirect(url_for('login'))

    name = request.form['name']
    coach = request.form['coach']
    logo_file = request.files.get('logo')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if logo_file:
        logo_filename = secure_filename(logo_file.filename)
        logo_path = os.path.join(app.config['UPLOAD_FOLDER'], logo_filename)
        logo_file.save(logo_path)
        cursor.execute("UPDATE teams SET name=?, coach=?, logo=? WHERE id=?", (name, coach, logo_filename, team_id))
    else:
        cursor.execute("UPDATE teams SET name=?, coach=? WHERE id=?", (name, coach, team_id))

    conn.commit()
    conn.close()
    return redirect(url_for('manage_teams'))

@app.route('/delete_team/<int:team_id>')
def delete_team(team_id):
    if not session.get('admin'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM teams WHERE id=?", (team_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('manage_teams'))

# ----------------------------
# MANAGE PLAYERS
# ----------------------------
@app.route('/manage_players', methods=['GET', 'POST'])
def manage_players():
    if not session.get('admin'):
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        team_id = request.form['team_id']
        goals = request.form['goals']
        medals = request.form['medals']
        is_captain = 1 if request.form.get('is_captain') else 0
        position = request.form['position']
        photo_file = request.files.get('photo')
        photo_filename = None

        if photo_file:
            photo_filename = secure_filename(photo_file.filename)
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
            photo_file.save(photo_path)

        cursor.execute("""
            INSERT INTO players (name, team_id, goals, medals, is_captain, position, photo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, team_id, goals, medals, is_captain, position, photo_filename))
        conn.commit()

    cursor.execute("SELECT * FROM teams")
    teams = cursor.fetchall()

    cursor.execute("""
        SELECT players.id, players.name, teams.name, players.goals, players.medals,
               players.is_captain, players.position, players.photo, players.team_id
        FROM players
        LEFT JOIN teams ON players.team_id = teams.id
    """)
    players = cursor.fetchall()
    conn.close()
    return render_template('manage_players.html', players=players, teams=teams)

@app.route('/edit_player/<int:player_id>', methods=['POST'])
def edit_player(player_id):
    if not session.get('admin'):
        return redirect(url_for('login'))

    name = request.form['name']
    team_id = request.form['team_id']
    goals = request.form['goals']
    medals = request.form['medals']
    is_captain = 1 if request.form.get('is_captain') else 0
    position = request.form['position']
    photo_file = request.files.get('photo')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if photo_file:
        photo_filename = secure_filename(photo_file.filename)
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
        photo_file.save(photo_path)
        cursor.execute("""
            UPDATE players SET name=?, team_id=?, goals=?, medals=?, is_captain=?, position=?, photo=?
            WHERE id=?
        """, (name, team_id, goals, medals, is_captain, position, photo_filename, player_id))
    else:
        cursor.execute("""
            UPDATE players SET name=?, team_id=?, goals=?, medals=?, is_captain=?, position=?
            WHERE id=?
        """, (name, team_id, goals, medals, is_captain, position, player_id))

    conn.commit()
    conn.close()
    return redirect(url_for('manage_players'))

@app.route('/delete_player/<int:player_id>')
def delete_player(player_id):
    if not session.get('admin'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM players WHERE id=?", (player_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('manage_players'))

# ----------------------------
# MAIN
# ----------------------------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
