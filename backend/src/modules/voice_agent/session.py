"""Conservative, per-call phone confirmation based on conversation turns."""
import re
from dataclasses import dataclass
from ..appointments.service import normalize_phone

WORDS = dict(zip('zero one two three four five six seven eight nine'.split(), '0123456789'))
WORDS['oh'] = '0'


def spoken_phone(text: str) -> str | None:
    text = re.sub(r'\b(' + '|'.join(WORDS) + r')\b', lambda m: WORDS[m[0]], text.lower())
    text = re.sub(r'\bplus\s*', '+', text)
    for match in re.finditer(r'(?<!\d)\+?\d(?:[\s().,-]*\d){9,14}(?!\d)', text):
        try:
            return normalize_phone(re.sub(r'[^\d+]', '', match[0]))
        except ValueError:
            continue
    return None


@dataclass
class CallSession:
    phone: str | None = None
    read_back: bool = False
    confirmed: bool = False

    def observe_user(self, text: str):
        number = spoken_phone(text)
        if number:
            self.phone = number
            self.read_back = self.confirmed = False
            return
        phrase = re.sub(r'[^a-z ]', '', text.lower()).strip()
        if re.search(r'\b(no|wrong|incorrect|change|different|not)\b', phrase):
            self.read_back = self.confirmed = False
            return
        if self.read_back and phrase in {'yes', 'yes please', 'yes correct', 'yes thats correct', 'thats correct', 'correct', 'yes that is correct', 'that is correct', 'yes it is', 'i confirm', 'confirmed'}:
            self.confirmed = True
            self.read_back = False
        elif self.read_back:
            self.read_back = False

    def observe_assistant(self, text: str, interrupted: bool = False):
        if not self.confirmed:
            self.read_back = bool(not interrupted and self.phone and spoken_phone(text) == self.phone and re.search(r'\b(correct|confirm|right)\b', text.lower()))

    def require_phone(self) -> str:
        if not self.confirmed or not self.phone:
            raise ValueError('Read back the spoken phone number and wait for explicit confirmation first.')
        return self.phone
