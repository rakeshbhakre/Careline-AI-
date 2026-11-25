import sqlite3
from datetime import datetime, timezone
from ...database.db import Database


class BookingConflict(Exception):
    pass


class AppointmentRepository:
    def __init__(self, db: Database):
        self.db = db

    def doctors(self):
        with self.db.connect() as conn:
            return [dict(row) for row in conn.execute('SELECT * FROM doctors ORDER BY name')]

    def available_slots(self, doctor_id=None):
        sql = '''SELECT s.*, d.name AS doctor_name, d.specialty FROM slots s
            JOIN doctors d ON d.id=s.doctor_id
            WHERE s.start_at > ? AND NOT EXISTS
            (SELECT 1 FROM appointments a WHERE a.slot_id=s.id AND a.status='booked')'''
        params = [datetime.now(timezone.utc).isoformat()]
        if doctor_id is not None:
            sql += ' AND s.doctor_id=?'
            params.append(doctor_id)
        with self.db.connect() as conn:
            return [dict(row) for row in conn.execute(sql + ' ORDER BY s.start_at, s.id', params)]

    def appointments(self, phone=None, active_only=False):
        sql = '''SELECT a.*, s.start_at, s.end_at, d.name AS doctor_name
            FROM appointments a JOIN slots s ON s.id=a.slot_id
            JOIN doctors d ON d.id=s.doctor_id WHERE 1=1'''
        params = []
        if phone is not None:
            sql += ' AND a.phone_number=?'
            params.append(phone)
        if active_only:
            sql += " AND a.status='booked' AND s.start_at > ?"
            params.append(datetime.now(timezone.utc).isoformat())
        with self.db.connect() as conn:
            return [dict(row) for row in conn.execute(sql + ' ORDER BY a.id DESC', params)]

    def book(self, slot_id, phone):
        try:
            with self.db.connect() as conn:
                conn.execute('BEGIN IMMEDIATE')
                slot = conn.execute('SELECT * FROM slots WHERE id=? AND start_at > ?', (slot_id, datetime.now(timezone.utc).isoformat())).fetchone()
                if slot is None:
                    raise BookingConflict('Slot does not exist or has expired')
                cursor = conn.execute('INSERT INTO appointments(slot_id,phone_number) VALUES (?,?)', (slot_id, phone))
                result = dict(conn.execute('SELECT * FROM appointments WHERE id=?', (cursor.lastrowid,)).fetchone())
            return result
        except sqlite3.IntegrityError as exc:
            raise BookingConflict('Slot is already booked') from exc

    def cancel(self, appointment_id, phone):
        with self.db.connect() as conn:
            cursor = conn.execute("""UPDATE appointments SET status='cancelled', cancelled_at=CURRENT_TIMESTAMP
                WHERE id=? AND phone_number=? AND status='booked'
                AND slot_id IN (SELECT id FROM slots WHERE start_at > ?)""", (appointment_id, phone, datetime.now(timezone.utc).isoformat()))
            if cursor.rowcount != 1:
                raise BookingConflict('No matching active future appointment')
            return dict(conn.execute('SELECT * FROM appointments WHERE id=?', (appointment_id,)).fetchone())
