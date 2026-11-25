CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    specialty TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS slots (
    id INTEGER PRIMARY KEY,
    doctor_id INTEGER NOT NULL REFERENCES doctors(id),
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    CHECK (end_at > start_at),
    UNIQUE (doctor_id, start_at)
);
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY,
    slot_id INTEGER NOT NULL REFERENCES slots(id),
    phone_number TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'booked' CHECK (status IN ('booked', 'cancelled')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cancelled_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS unique_active_booking
ON appointments(slot_id) WHERE status = 'booked';
CREATE INDEX IF NOT EXISTS appointment_phone ON appointments(phone_number, status);
