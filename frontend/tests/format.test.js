import test from 'node:test';
import assert from 'node:assert/strict';
import {dayKey,groupSlots,timeLabel} from '../src/features/schedule-board/format.js';
test('IST day boundary is applied to UTC timestamps',()=>{assert.equal(dayKey('2026-11-24T19:00:00Z'),'2026-11-25');assert.equal(dayKey('2026-11-24T18:00:00Z'),'2026-11-24');});
test('filter slots by local calendar day',()=>{const slots=[{id:1,start_at:'2026-11-24T19:00:00Z'},{id:2,start_at:'2026-11-24T18:00:00Z'}];assert.deepEqual(groupSlots(slots,'2026-11-25').map(s=>s.id),[1]);});
