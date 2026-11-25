import {useState} from 'react';
import {CalendarDays,ChevronRight,Clock,RefreshCw,Stethoscope} from 'lucide-react';
import {dayKey,timeLabel,dateLabel,groupSlots} from './format';
export default function ScheduleBoard({schedule}){
 const {doctors,slots,appointments,loading,error,refresh}=schedule;
 const days=[...new Set([...slots,...appointments].map(s=>dayKey(s.start_at)))].sort();
 const [selected,setSelected]=useState(''); const day=days.includes(selected)?selected:days[0];
 const available=groupSlots(slots,day); const booked=appointments.filter(a=>a.status==='booked');
 return <section className="schedule" aria-label="Scheduling dashboard">
 <div className="section-heading"><div><span className="eyebrow">Reception / 01</span><h1>Schedule</h1><p>Doctor availability and appointment activity.</p></div><button className="icon-button" onClick={refresh} aria-label="Refresh schedule"><RefreshCw size={18}/></button></div>
 {error&&<div role="alert" className="notice">Schedule unavailable: {error}. Start the backend and retry.</div>}
 <div className="stats"><div><Stethoscope size={17}/><span>Doctors</span><strong>{loading?'—':doctors.length}</strong></div><div><Clock size={17}/><span>Open slots · all days</span><strong>{loading?'—':slots.length}</strong></div><div><CalendarDays size={17}/><span>Active bookings</span><strong>{loading?'—':booked.length}</strong></div></div>
 <div className="panel"><div className="panel-heading"><h2>Availability</h2><span>IST</span></div><div className="dates">{days.map(d=><button key={d} className={day===d?'date active':'date'} onClick={()=>setSelected(d)} aria-pressed={day===d}>{dateLabel(d+'T12:00:00+05:30')}</button>)}</div>
 {loading?<p className="empty">Loading schedule…</p>:!doctors.length?<p className="empty">No doctor records.</p>:doctors.map((doctor,i)=><div className="doctor" key={doctor.id}><div className={'avatar avatar-'+i%4}>{doctor.name.replace(/^Dr\.?\s*/,'').split(' ').map(n=>n[0]).slice(0,2).join('')}</div><div className="doctor-name"><strong>{doctor.name}</strong><span>{doctor.specialty}</span></div><div className="slots">{available.filter(s=>s.doctor_id===doctor.id).map(s=><span className="slot" key={s.id}>{timeLabel(s.start_at)}</span>)}{!available.some(s=>s.doctor_id===doctor.id)&&<span className="muted">No open slots</span>}</div><ChevronRight size={15} className="doctor-chevron"/></div>)}
 </div><div className="panel"><div className="panel-heading"><h2>Appointments</h2><span>{appointments.length} records</span></div><div className="table-scroll"><table><thead><tr><th>Doctor</th><th>Appointment</th><th>Patient / contact</th><th>Status</th></tr></thead><tbody>{appointments.map(a=><tr key={a.id}><td>{a.doctor_name}</td><td>{dateLabel(a.start_at)} · {timeLabel(a.start_at)}</td><td>{a.patient_name||'—'}<br/><span className="muted">{a.phone_masked}</span></td><td><span className={'status '+a.status}>{a.status}</span></td></tr>)}</tbody></table></div>{!appointments.length&&<p className="empty">{loading?'Loading…':'No appointments yet. Book one through the voice agent.'}</p>}</div></section>;
}
