import asyncio

import pytest
from fastapi.testclient import TestClient

from src.config.settings import Settings
from src.database.db import Database
from src.database.seed import seed
from src.main import create_app
from src.modules.appointments.repository import AppointmentRepository
from src.modules.appointments.service import AppointmentService
from src.modules.voice_agent.session import CallSession, UserTurnTracker, spoken_phone
from src.modules.voice_agent.tools import VoiceTools

PHONE = '+919000000001'
ALTERNATE = '+919000000002'
PATIENT = 'Rakesh Bhakre'


def setup_service(path):
    db = Database(path)
    db.initialize()
    seed(db)
    return AppointmentService(AppointmentRepository(db))


def confirm_phone(session, phone=PHONE):
    session.observe_assistant(f'I heard {phone}. Should I use this number for your appointment, or would you prefer a different number?')
    assert session.read_back
    session.observe_user('Yes, use this number.')
    assert session.require_phone() == phone


def test_spoken_phone_formats_and_rejects_non_phone_text():
    assert spoken_phone('My number is nine zero zero zero zero zero zero zero zero one') == PHONE
    assert spoken_phone('90000 00001') == PHONE
    assert spoken_phone('plus nine one nine zero zero zero zero zero zero zero zero one') == PHONE
    assert spoken_phone('At 10:30 tomorrow') is None


def test_first_provided_phone_and_patient_name_are_captured_once():
    session = CallSession()
    session.observe_user('My name is Rakesh Bhakre, and my contact number is 9000000001.')
    assert session.patient_name == PATIENT
    assert session.phone == PHONE
    confirm_phone(session)
    assert session.patient_name == PATIENT
    assert session.confirmed


def test_alternative_phone_replaces_declined_number_and_must_be_confirmed():
    session = CallSession()
    session.observe_user('My name is Rakesh Bhakre, my number is 9000000001.')
    session.observe_assistant(f'I heard {PHONE}. Should I use this number for your appointment, or would you prefer a different number?')
    session.observe_user('No, use 9000000002 instead.')
    assert session.phone == ALTERNATE
    assert not session.confirmed
    confirm_phone(session, ALTERNATE)


def test_confirmation_requires_matching_readback_and_explicit_yes():
    session = CallSession()
    session.observe_user('9000000001')
    session.observe_user('yes')
    assert not session.confirmed
    session.observe_assistant(f'I heard {ALTERNATE}. Should I use this number for your appointment?')
    session.observe_user('yes')
    assert not session.confirmed
    session.observe_assistant(f'I heard {PHONE}. Should I use this number for your appointment?')
    session.observe_user('No, I want a different number.')
    assert not session.confirmed
    session.observe_assistant(f'I heard {PHONE}. Should I use this number for your appointment?')
    session.observe_user('Yes, that is correct.')
    assert session.require_phone() == PHONE


def test_invalid_number_cannot_be_used_for_booking():
    session = CallSession()
    session.observe_user('My name is Rakesh Bhakre and my number is 123.')
    with pytest.raises(ValueError, match='invalid'):
        session.require_phone()


def test_booking_requires_selected_live_slot_and_explicit_consent(tmp_path):
    service = setup_service(tmp_path / 'voice.sqlite3')
    session = CallSession()
    tools = VoiceTools(service, session)

    async def run():
        session.observe_user(f'My name is {PATIENT} and my number is 9000000001.')
        confirm_phone(session)
        available = await tools.execute('check_doctor_availability', {'doctor_id': 1})
        assert available['status'] == 'ok'
        slot = available['slots'][0]
        premature = await tools.execute('book_appointment', {'slot_id': slot['id'], 'patient_name': PATIENT})
        assert premature['status'] == 'error'
        assert await service.dashboard_appointments() == []

        prepared = await tools.execute('prepare_appointment', {'slot_id': slot['id']})
        assert prepared['status'] == 'ready_for_confirmation'
        assert prepared['doctor_name'] == 'Dr. Ananya Mehta'
        assert prepared['patient_name'] == PATIENT
        session.observe_assistant('Would you like me to book Dr. Ananya Mehta at that time?')
        session.observe_user('Yes, please book it.')
        booked = await tools.execute('book_appointment', {'slot_id': slot['id'], 'patient_name': PATIENT})
        assert booked['status'] == 'booked'
        assert booked['patient_name'] == PATIENT
        assert booked['start_at'].endswith('+05:30')
        row = (await service.dashboard_appointments())[0]
        assert row['patient_name'] == PATIENT
        assert row['phone_masked'].endswith('0001')
        assert 'phone_number' not in row

        cancelled = await tools.execute('cancel_appointment', {'appointment_id': booked['id']})
        assert cancelled['status'] == 'cancelled'
        assert slot['id'] in [item['id'] for item in await service.availability(1)]

    asyncio.run(run())


def test_session_isolation_and_user_turn_deduplication():
    one = CallSession()
    two = CallSession()
    one.observe_user('My name is Rakesh Bhakre and my number is 9000000001.')
    confirm_phone(one)
    assert one.patient_name == PATIENT and one.phone == PHONE and one.confirmed
    assert two.patient_name is None and two.phone is None and not two.confirmed

    tracker = UserTurnTracker()
    turn_one = [{'role': 'user', 'content': 'yes'}]
    assert tracker.next_user_text(turn_one) == 'yes'
    assert tracker.next_user_text([dict(turn_one[0])]) is None
    assert tracker.next_user_text(turn_one + [{'role': 'assistant', 'content': 'Checking that'}]) is None
    assert tracker.next_user_text(turn_one + [{'role': 'user', 'content': 'yes'}]) == 'yes'


def test_greeting_and_booking_prompt_requires_one_time_collection():
    from src.modules.voice_agent.prompt import system_prompt

    prompt = system_prompt()
    assert 'greet once' in prompt
    assert 'do not ask for it again' in prompt
    assert 'Should I use this number for your appointment, or would you prefer a different number?' in prompt
    assert 'Only then call book_appointment' in prompt


def test_runtime_uses_installed_pipecat_universal_context_aggregators():
    from pipecat.processors.aggregators.llm_context import LLMContext
    from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair, LLMUserAggregatorParams

    assert LLMContext is not None
    assert LLMContextAggregatorPair is not None
    assert LLMUserAggregatorParams is not None


def test_voice_offer_missing_credentials(tmp_path):
    settings = Settings(database_path=tmp_path / 'api.sqlite3', elevenlabs_api_key='', elevenlabs_voice_id='', google_api_key='', groq_api_key='')
    with TestClient(create_app(settings)) as client:
        assert client.post('/api/voice/offer', json={}).status_code == 503
        assert client.get('/api/health').json()['voice'] == 'missing_credentials'
