import asyncio
from fastapi.testclient import TestClient
from src.config.settings import Settings
from src.database.db import Database
from src.database.seed import seed
from src.main import create_app
from src.modules.appointments.repository import AppointmentRepository
from src.modules.appointments.service import AppointmentService
from src.modules.voice_agent.session import CallSession, spoken_phone
from src.modules.voice_agent.tools import VoiceTools

PHONE = '+919000000001'


def test_spoken_number_formats():
    assert spoken_phone('My number is nine zero zero zero zero zero zero zero zero one') == PHONE
    assert spoken_phone('My number is 90000 00001') == PHONE
    assert spoken_phone('plus nine one nine zero zero zero zero zero zero zero zero one') == PHONE
    assert spoken_phone('At 10:30 tomorrow') is None


def test_confirmation_requires_readback():
    session = CallSession()
    session.observe_user('9000000001')
    session.observe_user('yes')
    assert not session.confirmed
    session.observe_assistant('9000000002, is that correct?')
    session.observe_user('yes')
    assert not session.confirmed
    session.observe_assistant('9000000001, is that correct?', interrupted=True)
    session.observe_user('yes')
    assert not session.confirmed
    session.observe_assistant('9000000001, is that correct?')
    session.observe_user('yes')
    assert session.require_phone() == PHONE
    session.observe_user('9000000002')
    assert not session.confirmed


def test_voice_tools_full_flow(tmp_path):
    db = Database(tmp_path / 'voice.sqlite3')
    db.initialize()
    seed(db)
    service = AppointmentService(AppointmentRepository(db))
    session = CallSession()
    tools = VoiceTools(service, session)
    async def run():
        available = await tools.execute('check_doctor_availability', {'doctor_id': 1})
        assert available['status'] == 'ok'
        slot = available['slots'][0]['id']
        assert available['slots'][0]['start_at'].endswith('+05:30')
        assert (await tools.execute('book_appointment', {'slot_id': slot, 'phone_confirmed': True}))['status'] == 'error'
        session.observe_user('9000000001')
        session.observe_assistant('9000000001, is that correct?')
        session.observe_user('yes')
        booked = await tools.execute('book_appointment', {'slot_id': slot, 'phone_number': '+919000000002'})
        assert booked['status'] == 'booked'
        assert 'phone_number' not in booked
        assert (await service.dashboard_appointments())[0]['phone_masked'] == '••••0001'
        stranger = VoiceTools(service, CallSession())
        assert (await stranger.execute('cancel_appointment', {'appointment_id': booked['id']}))['status'] == 'error'
        assert (await tools.execute('cancel_appointment', {}))['status'] == 'cancelled'
        assert slot in [s['id'] for s in await service.availability(1)]
    asyncio.run(run())


def test_voice_offer_missing_credentials(tmp_path):
    settings = Settings(database_path=tmp_path / 'api.sqlite3', elevenlabs_api_key='', elevenlabs_voice_id='', google_api_key='', groq_api_key='')
    with TestClient(create_app(settings)) as client:
        assert client.post('/api/voice/offer', json={}).status_code == 503
        assert client.get('/api/health').json()['voice'] == 'missing_credentials'
