import asyncio
import re
from datetime import datetime, date
from zoneinfo import ZoneInfo
from .repository import AppointmentRepository, BookingConflict


def normalize_phone(value: str) -> str:
    phone = re.sub(r'[\s().-]', '', value)
    if re.fullmatch(r'[0-9]{10}', phone):
        phone = '+91' + phone
    if not re.fullmatch(r'\+[1-9][0-9]{7,14}', phone):
        raise ValueError('Provide a valid phone number including country code, or a 10-digit Indian number')
    return phone


def normalize_patient_name(value: str) -> str:
    name = ' '.join((value or '').strip().split())
    if not name or len(name) > 100 or any(not (char.isalpha() or char in " '-.") for char in name):
        raise ValueError('Provide the patient name before booking')
    return name


class AppointmentService:
    def __init__(self, repository: AppointmentRepository):
        self.repository = repository

    async def doctors(self):
        return await asyncio.to_thread(self.repository.doctors)

    async def availability(self, doctor_id=None, day: date | None = None):
        slots = await asyncio.to_thread(self.repository.available_slots, doctor_id)
        if day:
            slots = [s for s in slots if datetime.fromisoformat(s['start_at']).astimezone(ZoneInfo('Asia/Kolkata')).date() == day]
        return slots

    async def dashboard_appointments(self):
        rows = await asyncio.to_thread(self.repository.appointments)
        for row in rows:
            phone = row.pop('phone_number')
            row['phone_masked'] = '••••' + phone[-4:]
        return rows

    async def book(self, slot_id: int, phone: str, patient_name: str = ''):
        return await asyncio.to_thread(self.repository.book, slot_id, normalize_phone(phone), normalize_patient_name(patient_name))

    async def cancel(self, phone: str, appointment_id: int | None = None):
        phone = normalize_phone(phone)
        if appointment_id is None:
            matches = await asyncio.to_thread(self.repository.appointments, phone, True)
            if not matches:
                raise BookingConflict('No active future appointment found')
            if len(matches) > 1:
                return {'status': 'selection_required', 'appointments': [dict((k,v) for k,v in row.items() if k != 'phone_number') for row in matches]}
            appointment_id = matches[0]['id']
        return await asyncio.to_thread(self.repository.cancel, appointment_id, phone)
