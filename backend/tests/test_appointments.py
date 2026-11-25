import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from fastapi.testclient import TestClient
from src.config.settings import Settings
from src.database.db import Database
from src.database.seed import seed
from src.modules.appointments.repository import AppointmentRepository, BookingConflict
from src.modules.appointments.service import AppointmentService, normalize_phone
from src.main import create_app

PHONE = '+919000000001'


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


def test_booking_and_cancellation(service):
    async def run():
        slot = (await service.availability())[0]['id']
        booked = await service.book(slot, PHONE)
        assert booked['status'] == 'booked'
        assert slot not in [s['id'] for s in await service.availability()]
        cancelled = await service.cancel(PHONE, booked['id'])
        assert cancelled['status'] == 'cancelled'
        assert slot in [s['id'] for s in await service.availability()]
        assert (await service.book(slot, PHONE))['id'] != booked['id']
    asyncio.run(run())


def test_concurrent_booking(service):
    async def run():
        slot = (await service.availability())[0]['id']
        results = await asyncio.gather(service.book(slot, PHONE), service.book(slot, '+919000000002'), return_exceptions=True)
        assert sum(isinstance(r, dict) for r in results) == 1
        assert sum(isinstance(r, BookingConflict) for r in results) == 1
    asyncio.run(run())


def test_wrong_phone(service):
    async def run():
        booked = await service.book((await service.availability())[0]['id'], PHONE)
        with pytest.raises(BookingConflict):
            await service.cancel('+919000000002', booked['id'])
    asyncio.run(run())


def test_disambiguation(service):
    async def run():
        slots = await service.availability()
        for slot in slots[:2]:
            await service.book(slot['id'], PHONE)
        result = await service.cancel(PHONE)
        assert result['status'] == 'selection_required'
        assert len(result['appointments']) == 2
        assert all(a['status'] == 'booked' for a in result['appointments'])
    asyncio.run(run())


def test_phone_validation():
    assert normalize_phone('90000 00001') == PHONE
    with pytest.raises(ValueError):
        normalize_phone('123')


def test_invalid_slot(service):
    with pytest.raises(BookingConflict):
        asyncio.run(service.book(999999, PHONE))


def test_api(tmp_path):
    with TestClient(create_app(Settings(database_path=tmp_path / 'api.sqlite3'))) as client:
        assert client.get('/api/health').json()['status'] == 'ok'
        assert len(client.get('/api/doctors').json()) == 4
        assert len(client.get('/api/slots?doctor_id=1').json()) == 28
        assert client.get('/api/appointments').json() == []
        assert client.get('/api/slots?day=invalid').status_code == 422
        svc = client.app.state.appointments
        asyncio.run(svc.book(1, PHONE))
        row = client.get('/api/appointments').json()[0]
        assert row['phone_masked'] == '••••0001'
        assert 'phone_number' not in row
