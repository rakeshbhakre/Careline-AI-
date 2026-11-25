"""Per-call patient details and confirmation state."""
import re
from dataclasses import dataclass, field

from ..appointments.service import normalize_phone

WORDS = dict(zip('zero one two three four five six seven eight nine'.split(), '0123456789'))
WORDS['oh'] = '0'

NAME_PREFIXES = (
    r"\bmy name is\s+",
    r"\b(?:the )?patient(?:'s|s)? name is\s+",
    r"\bname is\s+",
    r"\bthis is\s+",
    r"\bi am\s+",
    r"\bi'm\s+",
    r"\bit is for\s+",
    r"\bit's for\s+",
    r"\bappointment (?:is )?for\s+",
    r"\bbook(?:ing)? (?:an? )?appointment for\s+",
    r"\bfor my (?:mother|father|wife|husband|son|daughter|child|parent)\s+",
)
NAME_STOP = re.compile(r"\b(?:and|my phone|phone number|contact number|number is|my number|i need|i want|appointment|tomorrow|today|next week)\b", re.I)
NON_NAME_STARTS = {'looking', 'calling', 'booking', 'trying', 'going', 'requesting'}


def spoken_phone(text: str) -> str | None:
    text = re.sub(r'\b(' + '|'.join(WORDS) + r')\b', lambda m: WORDS[m[0]], text.lower())
    text = re.sub(r'\bplus\s*', '+', text)
    for match in re.finditer(r'(?<!\d)\+?\d(?:[\s().,-]*\d){9,14}(?!\d)', text):
        try:
            return normalize_phone(re.sub(r'[^\d+]', '', match[0]))
        except ValueError:
            continue
    return None


def _clean_name(value: str) -> str | None:
    value = NAME_STOP.split(value, maxsplit=1)[0]
    words = re.findall(r"[^\W\d_][^\W\d_'.’\-]*[.]?", value, flags=re.UNICODE)
    while words and words[0].lower().rstrip('.') in {'mr', 'mrs', 'ms', 'miss', 'dr', 'patient'}:
        words.pop(0)
    if not words or len(words) > 4 or words[0].lower() in NON_NAME_STARTS:
        return None
    return ' '.join(word.rstrip('.') for word in words).strip()


def _extract_patient_name(text: str) -> str | None:
    for prefix in NAME_PREFIXES:
        match = re.search(prefix + r"([^\d,;.!?]+)", text, flags=re.I)
        if match:
            name = _clean_name(match.group(1))
            if name:
                return name
    return None


def _normalized_phrase(text: str) -> str:
    text = text.lower().replace('’', "'")
    text = re.sub(r"[^\w']+", ' ', text, flags=re.UNICODE)
    return re.sub(r'\s+', ' ', text).strip()


def _is_affirmative(text: str) -> bool:
    phrase = _normalized_phrase(text)
    if re.search(r'\b(no|not|wrong|incorrect|different|change|rather)\b', phrase):
        return False
    return bool(re.search(r"\b(yes|yeah|yep|correct|right|confirmed|confirm|please use it|use this number|go ahead|book it)\b", phrase))


def _is_negative(text: str) -> bool:
    return bool(re.search(r'\b(no|not|wrong|incorrect|different|change|rather|cancel that)\b', _normalized_phrase(text)))


@dataclass
class CallSession:
    """State is created per WebRTC call and is never shared between callers."""

    patient_name: str | None = None
    phone: str | None = None
    phone_input_invalid: bool = False
    read_back: bool = False
    confirmed: bool = False
    user_turn_count: int = 0
    user_messages: list[str] = field(default_factory=list)
    awaiting_patient_name: bool = False
    available_slot_ids: set[int] = field(default_factory=set)
    pending_slot_id: int | None = None
    awaiting_booking_confirmation: bool = False
    booking_agreed: bool = False

    def observe_user(self, text: str):
        self.user_turn_count += 1
        self.user_messages.append(text)

        name = _extract_patient_name(text)
        if name:
            self.patient_name = name
            self.awaiting_patient_name = False
        elif self.awaiting_patient_name and not spoken_phone(text):
            name = _clean_name(text)
            if name:
                self.patient_name = name
                self.awaiting_patient_name = False

        number = spoken_phone(text)
        if number:
            self.phone = number
            self.phone_input_invalid = False
            self.read_back = self.confirmed = False
        elif re.search(r'\b(phone|number|contact)\b', text, re.I) and (
            re.search(r'\d', text) or re.search(r'\b(' + '|'.join(WORDS) + r')\b', text, re.I)
        ):
            self.phone_input_invalid = True
            self.confirmed = False
            self.read_back = False

        if self.awaiting_booking_confirmation:
            if _is_affirmative(text):
                self.booking_agreed = True
                self.awaiting_booking_confirmation = False
            elif _is_negative(text):
                self.pending_slot_id = None
                self.booking_agreed = False
                self.awaiting_booking_confirmation = False

        if self.read_back and not number:
            if _is_affirmative(text):
                self.confirmed = True
                self.read_back = False
            elif _is_negative(text):
                self.confirmed = False
                self.read_back = False

    def observe_assistant(self, text: str, interrupted: bool = False):
        if not self.patient_name and re.search(r'\b(name|patient)\b', text.lower()) and '?' in text:
            self.awaiting_patient_name = True

        if self.phone and not self.confirmed:
            confirms_phone = re.search(r'\b(correct|confirm|right|use this number)\b', text.lower())
            self.read_back = bool(not interrupted and spoken_phone(text) == self.phone and confirms_phone)

        if self.pending_slot_id is not None and not interrupted:
            asks_to_book = '?' in text and re.search(r'\b(book|schedule|make|reserve)\b', text.lower())
            if asks_to_book:
                self.awaiting_booking_confirmation = True

    def resolve_patient_name(self, candidate: str | None = None) -> str:
        if self.patient_name:
            return self.patient_name
        candidate = _clean_name(candidate or '')
        if candidate:
            normalized = _normalized_phrase(candidate)
            if any(normalized in _normalized_phrase(message) for message in self.user_messages):
                self.patient_name = candidate
                return candidate
        raise ValueError('Ask the caller for the patient name before booking.')

    def require_phone(self) -> str:
        if self.phone_input_invalid:
            raise ValueError('The caller-provided phone number was invalid. Ask for a valid number and read it back for confirmation.')
        if not self.confirmed or not self.phone:
            raise ValueError('Read back the spoken phone number and wait for explicit confirmation first.')
        return self.phone

    def require_booking_consent(self, slot_id: int):
        if self.pending_slot_id != slot_id:
            raise ValueError('Ask the caller to select and confirm an available appointment time first.')
        if not self.booking_agreed:
            raise ValueError('Ask whether the caller wants this appointment, then wait for their explicit yes.')


@dataclass
class UserTurnTracker:
    """Deduplicate repeated context frames without suppressing identical later turns."""

    last_fingerprint: tuple[int, str] | None = None

    def next_user_text(self, messages) -> str | None:
        user_messages = [m for m in messages if isinstance(m, dict) and m.get('role') == 'user' and isinstance(m.get('content'), str)]
        if not user_messages:
            return None
        latest = user_messages[-1]['content']
        fingerprint = (len(user_messages), latest)
        if fingerprint == self.last_fingerprint:
            return None
        self.last_fingerprint = fingerprint
        return latest
