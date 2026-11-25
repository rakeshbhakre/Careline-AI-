"""Voice adapter; appointment rules remain in the scheduling module."""
from datetime import date, datetime
from zoneinfo import ZoneInfo
from ..appointments.repository import BookingConflict
from .session import CallSession

TOOL_SPECS = [
    ('check_doctor_availability', 'Find available doctor slots. Omit doctor_id to list doctors and slots. Dates use IST.', {'doctor_id': {'type': 'integer', 'description': 'Doctor ID'}, 'day': {'type': 'string', 'description': 'YYYY-MM-DD'}}, []),
    ('prepare_appointment', 'Select an actually available slot after the caller chooses it. This only prepares a summary; it does not book.', {'slot_id': {'type': 'integer', 'description': 'Slot ID returned by availability'}}, ['slot_id']),
    ('book_appointment', 'Book a prepared slot only after patient name and phone are verified and the caller explicitly agrees to that exact appointment.', {'slot_id': {'type': 'integer', 'description': 'Prepared slot ID'}, 'patient_name': {'type': 'string', 'description': 'Patient name the caller provided'}}, ['slot_id']),
    ('cancel_appointment', 'Cancel an appointment for the confirmed caller. Omit ID to resolve by phone; if several match, ask the caller to choose.', {'appointment_id': {'type': 'integer', 'description': 'Appointment ID if known'}}, []),
]


def local_times(row):
    row = {k: v for k, v in row.items() if k != 'phone_number'}
    for key in ('start_at', 'end_at'):
        if row.get(key):
            row[key] = datetime.fromisoformat(row[key]).astimezone(ZoneInfo('Asia/Kolkata')).isoformat()
    return row


class VoiceTools:
    def __init__(self, service, session: CallSession):
        self.service = service
        self.session = session

    async def execute(self, name, args):
        try:
            if name == 'check_doctor_availability':
                day = date.fromisoformat(args['day']) if args.get('day') else None
                slots = await self.service.availability(args.get('doctor_id'), day)
                offered_slots = slots[:32]
                self.session.available_slot_ids = {int(slot['id']) for slot in offered_slots}
                return {'status': 'ok', 'doctors': await self.service.doctors(), 'slots': [local_times(s) for s in offered_slots], 'more_slots': len(slots) > 32}
            if name == 'prepare_appointment':
                slot_id = int(args['slot_id'])
                if slot_id not in self.session.available_slot_ids:
                    return {'status': 'error', 'message': 'That slot was not offered in the current call. Check availability again.'}
                patient_name = self.session.resolve_patient_name(args.get('patient_name'))
                phone = self.session.require_phone()
                slots = await self.service.availability()
                slot = next((row for row in slots if int(row['id']) == slot_id), None)
                if slot is None:
                    return {'status': 'error', 'message': 'That slot is no longer available. Check availability again.'}
                self.session.pending_slot_id = slot_id
                self.session.booking_agreed = False
                self.session.awaiting_booking_confirmation = False
                prepared = local_times(slot)
                prepared.update({'status': 'ready_for_confirmation', 'patient_name': patient_name, 'phone_confirmed': True})
                return prepared
            if name == 'book_appointment':
                slot_id = int(args['slot_id'])
                if slot_id not in self.session.available_slot_ids:
                    return {'status': 'error', 'message': 'That slot was not offered in the current call. Check availability again.'}
                self.session.require_booking_consent(slot_id)
                patient_name = self.session.resolve_patient_name(args.get('patient_name'))
                phone = self.session.require_phone()
                result = await self.service.book(slot_id, phone, patient_name)
                self.session.pending_slot_id = None
                self.session.booking_agreed = False
                result = local_times(result)
                result['status'] = 'booked'
                return result
            if name == 'cancel_appointment':
                phone = self.session.require_phone()
                appointment_id = args.get('appointment_id')
                result = await self.service.cancel(phone, int(appointment_id) if appointment_id is not None else None)
                if result['status'] == 'selection_required':
                    return {'status': 'selection_required', 'appointments': [local_times(a) for a in result['appointments']]}
                return local_times(result)
            return {'status': 'error', 'message': 'Unknown tool'}
        except (ValueError, KeyError, TypeError, BookingConflict) as exc:
            return {'status': 'error', 'message': str(exc)}
