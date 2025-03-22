import sqlite3

DB_PATH = "study.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # 스터디 기본 테이블
    cur.execute('''
    CREATE TABLE IF NOT EXISTS studies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        weekdays TEXT,
        time TEXT,
        voice_channel_id INTEGER
    )
    ''')

    # 출석 테이블
    cur.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        study_name TEXT,
        user_name TEXT,
        date TEXT,
        time TEXT  -- 체크인 시각
        status TEXT  -- 출석 상태 (출석, 지각, 결석)
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS study_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        study_name TEXT,
        user_name TEXT
    )
    ''')

    conn.commit()
    conn.close()



### 📘 Study 관련

def create_study(name, weekdays, time, voice_channel_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            INSERT INTO studies (name, weekdays, time, voice_channel_id)
            VALUES (?, ?, ?, ?)
        ''', (name, weekdays, time, voice_channel_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def delete_study(study_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM studies WHERE name = ?", (study_name,))
    cur.execute("DELETE FROM attendance WHERE study_name = ?", (study_name,))
    cur.execute("DELETE FROM study_members WHERE study_name = ?", (study_name,))
    conn.commit()
    conn.close()


def get_study_by_voice_channel_id(vc_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM studies WHERE voice_channel_id = ?", (vc_id,))
    results = cur.fetchall()
    conn.close()
    return [r[0] for r in results]

def get_study_info(study_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT weekdays, time, voice_channel_id FROM studies WHERE name = ?", (study_name,))
    result = cur.fetchone()
    conn.close()
    return {
        "weekdays": [int(d) for d in result[0].split(',')],
        "time": result[1],
        "voice_channel_id": result[2]
    } if result else None

def get_all_studies():
    conn = get_connection()
    cur = conn.cursor()

    # 스터디 기본 정보 조회
    cur.execute("SELECT name, weekdays, time FROM studies")
    rows = cur.fetchall()

    studies = []
    for name, weekdays, time in rows:
        # 참가자 목록 조회
        cur.execute("SELECT user_name FROM study_members WHERE study_name = ?", (name,))
        participants = [row[0] for row in cur.fetchall()]

        studies.append({
            "name": name,
            "weekdays": weekdays,
            "time": time,
            "participants": participants
        })

    conn.close()
    return studies

### ✅ Attendance 관련

def has_already_checked_in(study_name, user_name, date):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT 1 FROM attendance
        WHERE study_name = ? AND user_name = ? AND date = ?
    ''', (study_name, user_name, date))
    result = cur.fetchone()
    conn.close()
    return result is not None

def record_attendance(study_name, user_name, date, time_str, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO attendance (study_name, user_name, date, time, status)
        VALUES (?, ?, ?, ?, ?)
    ''', (study_name, user_name, date, time_str, status))
    conn.commit()
    conn.close()

def get_attendance_history(study_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT date, user_name, time, status
        FROM attendance
        WHERE study_name = ?
        ORDER BY date DESC
    ''', (study_name,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_attendance_by_date(study_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT date, user_name, time, status
        FROM attendance
        WHERE study_name = ?
        ORDER BY date DESC
    ''', (study_name,))
    rows = cur.fetchall()

    result = {}
    for date, user, time, status in rows:
        if date not in result:
            result[date] = {}
        result[date][user] = {"time": time, "status": status}
    conn.close()
    return result

def add_study_members(study_name, user_names):
    conn = get_connection()
    cur = conn.cursor()

    # 이미 등록된 사람 확인
    cur.execute('SELECT user_name FROM study_members WHERE study_name = ?', (study_name,))
    existing = set(row[0] for row in cur.fetchall())

    added_users = []

    for name in user_names:
        if name not in existing:
            cur.execute('''
                INSERT INTO study_members (study_name, user_name)
                VALUES (?, ?)
            ''', (study_name, name))
            added_users.append(name)

    conn.commit()
    conn.close()
    return added_users  # 실제 추가된 유저 리스트 반환

def get_study_members(study_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_name FROM study_members WHERE study_name = ?", (study_name,))
    members = [row[0] for row in cur.fetchall()]
    conn.close()
    return members