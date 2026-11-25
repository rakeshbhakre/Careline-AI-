export const dayKey = value => new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(value));
export const timeLabel = value => new Intl.DateTimeFormat('en-IN',{timeZone:'Asia/Kolkata',hour:'numeric',minute:'2-digit',hour12:true}).format(new Date(value));
export const dateLabel = value => new Intl.DateTimeFormat('en-IN',{timeZone:'Asia/Kolkata',weekday:'short',day:'numeric',month:'short'}).format(new Date(value));
export function groupSlots(slots,day){return slots.filter(s=>dayKey(s.start_at)===day);}
