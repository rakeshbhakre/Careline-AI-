"""Voice adapter; appointment rules remain in the scheduling module."""
from datetime import date, datetime
from zoneinfo import ZoneInfo
from ..appointments.repository import BookingConflict
from .session import CallSession

TOOL_SPECS = [
    ('check_doctor_availability', 'Find available doctor slots. Omit doctor_id to list doctors and slots. Dates use IST.', {'doctor_id': {'type': 'integer', 'description': 'Doctor ID'}, 'day': {'type': 'string', 'description': 'YYYY-MM-DD'}}, []),
    ('book_appointment', 'Book the selected slot only after phone confirmation and caller agreement.', {'slot_id': {'type': 'integer', 'description': 'Slot ID returned by availability'}}, ['slot_id']),
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
                return {'status': 'ok', 'doctors': await self.service.doctors(), 'slots': [local_times(s) for s in slots[:32]], 'more_slots': len(slots) > 32}
            if name == 'book_appointment':
                phone = self.session.require_phone()
                result = await self.service.book(int(args['slot_id']), phone)
                return local_times(result)
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
