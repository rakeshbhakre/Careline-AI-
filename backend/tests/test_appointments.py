import asyncio
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from src.config.settings import Settings
from src.database.db import Database
from src.database.seed import seed
from src.main import create_app
from src.modules.appointments.repository import AppointmentRepository, BookingConflict
from src.modules.appointments.service import AppointmentService, normalize_phone

PHONE = '+919000000001'
PATIENT = 'Rakesh Bhakre'


@pytest.fixture
def service(tmp_path):
    db = Database(tmp_path / 'test.sqlite3')
    db.initialize()
    seed(db)
    seed(db)
    return AppointmentService(AppointmentRepository(db))


def test_seed_and_date_filter(service):
    async def run():
        assert len(await service.doctors()) == 4
        slots = await service.availability()
        assert len(slots) == 112
        day = datetime.fromisoformat(slots[0]['start_at']).astimezone(ZoneInfo('Asia/Kolkata')).date()
        assert len(await service.availability(1, day)) == 4
    asyncio.run(run())


def test_booking_and_cancellation_restore_slot(service):
    async def run():
        slot = (await service.availability())[0]['id']
        booked = await service.book(slot, PHONE, PATIENT)
        assert booked['status'] == 'booked'
        assert booked['patient_name'] == PATIENT
        assert slot not in [s['id'] for s in await service.availability()]
        cancelled = await service.cancel(PHONE, booked['id'])
        assert cancelled['status'] == 'cancelled'
        assert slot in [s['id'] for s in await service.availability()]
        assert (await service.book(slot, PHONE, PATIENT))['id'] != booked['id']
    asyncio.run(run())


def test_concurrent_duplicate_booking_is_rejected(service):
    async def run():
        slot = (await service.availability())[0]['id']
        results = await asyncio.gather(
            service.book(slot, PHONE, PATIENT),
            service.book(slot, '+919000000002', 'Sam Patel'),
            return_exceptions=True,
        )
        assert sum(isinstance(result, dict) for result in results) == 1
        assert sum(isinstance(result, BookingConflict) for result in results) == 1
    asyncio.run(run())


def test_wrong_phone_cannot_cancel(service):
    async def run():
        booked = await service.book((await service.availability())[0]['id'], PHONE, PATIENT)
        with pytest.raises(BookingConflict):
            await service.cancel('+919000000002', booked['id'])
    asyncio.run(run())


def test_disambiguation_for_multiple_active_appointments(service):
    async def run():
        slots = await service.availability()
        for slot in slots[:2]:
            await service.book(slot['id'], PHONE, PATIENT)
        result = await service.cancel(PHONE)
        assert result['status'] == 'selection_required'
        assert len(result['appointments']) == 2
        assert all(appointment['status'] == 'booked' for appointment in result['appointments'])
    asyncio.run(run())


def test_phone_validation():
    assert normalize_phone('90000 00001') == PHONE
    with pytest.raises(ValueError):
        normalize_phone('123')


def test_invalid_slot(service):
    with pytest.raises(BookingConflict):
        asyncio.run(service.book(999999, PHONE, PATIENT))


def test_blank_patient_name_is_rejected(service):
    async def run():
        slot = (await service.availability())[0]['id']
        with pytest.raises(ValueError, match='patient name'):
            await service.book(slot, PHONE, '')
    asyncio.run(run())


def test_api_returns_patient_name_but_not_full_phone(tmp_path):
    with TestClient(create_app(Settings(database_path=tmp_path / 'api.sqlite3'))) as client:
        assert client.get('/api/health').json()['status'] == 'ok'
        assert len(client.get('/api/doctors').json()) == 4
        assert len(client.get('/api/slots?doctor_id=1').json()) == 28
        assert client.get('/api/appointments').json() == []
        assert client.get('/api/slots?day=invalid').status_code == 422
        service = client.app.state.appointments
        asyncio.run(service.book(1, PHONE, PATIENT))
        row = client.get('/api/appointments').json()[0]
        assert row['patient_name'] == PATIENT
        assert row['phone_masked'].endswith('0001')
        assert 'phone_number' not in row


def test_existing_database_migration_preserves_appointments(tmp_path):
    path = tmp_path / 'existing.sqlite3'
    with sqlite3.connect(path) as connection:
        connection.executescript('''
            CREATE TABLE doctors(id INTEGER PRIMARY KEY, name TEXT NOT NULL, specialty TEXT NOT NULL);
            CREATE TABLE slots(id INTEGER PRIMARY KEY, doctor_id INTEGER NOT NULL, start_at TEXT NOT NULL, end_at TEXT NOT NULL);
            CREATE TABLE appointments(id INTEGER PRIMARY KEY, slot_id INTEGER NOT NULL, phone_number TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'booked', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, cancelled_at TEXT);
            INSERT INTO doctors VALUES (1, 'Dr. Ananya Mehta', 'Cardiology');
            INSERT INTO slots VALUES (1, 1, '2099-01-01T04:30:00+00:00', '2099-01-01T05:00:00+00:00');
            INSERT INTO appointments(id, slot_id, phone_number) VALUES (7, 1, '+919000000001');
        ''')

    db = Database(path)
    db.initialize()
    with db.connect() as connection:
        row = connection.execute('SELECT id, patient_name, phone_number FROM appointments WHERE id=7').fetchone()
    assert dict(row) == {'id': 7, 'patient_name': '', 'phone_number': PHONE}
