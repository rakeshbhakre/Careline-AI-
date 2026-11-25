from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from .db import Database

DOCTORS = [(1, 'Dr. Ananya Mehta', 'Cardiology'), (2, 'Dr. Priya Rao', 'Dermatology'), (3, 'Dr. Neel Shah', 'General medicine'), (4, 'Dr. Arjun Patel', 'Orthopedics')]


def seed(db: Database):
    today = datetime.now(ZoneInfo('Asia/Kolkata')).date()
    with db.connect() as conn:
        conn.executemany('INSERT OR IGNORE INTO doctors VALUES (?, ?, ?)', DOCTORS)
        for offset in range(1, 8):
            day = today + timedelta(days=offset)
            for doctor_id, _, _ in DOCTORS:
                for hour in (10, 11, 14, 15):
                    start = datetime(day.year, day.month, day.day, hour, tzinfo=ZoneInfo('Asia/Kolkata'))
                    end = start + timedelta(minutes=30)
                    conn.execute('INSERT OR IGNORE INTO slots(doctor_id,start_at,end_at) VALUES (?,?,?)', (doctor_id, start.astimezone(timezone.utc).isoformat(), end.astimezone(timezone.utc).isoformat()))
