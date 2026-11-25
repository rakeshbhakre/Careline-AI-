import {useEffect,useRef} from 'react';
import {AudioLines,Mic,MicOff,Phone,PhoneOff,ShieldCheck} from 'lucide-react';
import {dateLabel,timeLabel} from '../schedule-board/format';
import {useVoiceCall} from './useVoiceCall';

export default function PhoneScreen({configured,onAppointmentChange}){
 const audio=useRef(null);const bottom=useRef(null);const call=useVoiceCall(audio,onAppointmentChange);
 const active=['connecting','ready'].includes(call.state);const ready=call.state==='ready';
 useEffect(()=>{bottom.current?.scrollIntoView({block:'nearest'});},[call.messages,call.partial]);
 const timer=`${String(Math.floor(call.seconds/60)).padStart(2,'0')}:${String(call.seconds%60).padStart(2,'0')}`;
 const appointment=call.booking;
 return <aside className="phone" aria-label="Voice receptionist">
  <div className="phone-top"><span>VOICE RECEPTION</span><span className="phone-dot"/></div>
  <div className="agent"><div className={'agent-icon '+(call.speaking?'talking':'')}><AudioLines size={34}/></div><h2>Careline assistant</h2><p aria-live="polite">{ready?`Connected · ${timer}`:call.state==='connecting'?'Connecting…':call.state==='ended'?'Call ended':call.state==='error'?'Connection failed':'Ready for your call'}</p><div className="activity" aria-live="polite">{call.speaking?`${call.speaking} speaking`:ready?'Listening for your request':'Appointment reception'}</div><div className={'audio-status '+call.audioState} aria-live="polite">{call.audioState==='playing'?'Assistant audio is playing':call.audioState==='connected'?'Assistant audio track connected':call.audioState==='blocked'?'Browser blocked assistant audio':'Waiting for assistant audio'}</div></div>
  {(call.patient.patient_name||call.patient.phone_number)&&<div className="caller-details" aria-live="polite"><span className="eyebrow">CALL DETAILS</span>{call.patient.patient_name&&<div><small>Patient</small><strong>{call.patient.patient_name}</strong></div>}{call.patient.phone_number&&<div><small>{call.patient.phone_confirmed?'Confirmed contact':'Contact to confirm'}</small><strong>{call.patient.phone_number}</strong></div>}</div>}
  <div className="transcript-heading">LIVE TRANSCRIPT <span>{call.messages.length}</span></div>
  <div className="transcript" aria-live="polite">{!call.messages.length&&!call.partial&&<p className="transcript-empty">Your conversation will appear here when you start a call.</p>}{call.messages.map((m,i)=><div key={i} className={'message '+m.role.toLowerCase()}><small>{m.role}</small><p>{m.text}</p></div>)}{call.partial&&<div className="message caller partial"><small>Caller · listening</small><p>{call.partial}</p></div>}<div ref={bottom}/></div>
  {appointment&&<section className="booking-confirmation" aria-live="polite"><span className="eyebrow">APPOINTMENT {appointment.status==='cancelled'?'CANCELLED':'CONFIRMED'}</span><strong>{appointment.doctor_name}</strong><span>{dateLabel(appointment.start_at)} · {timeLabel(appointment.start_at)}</span>{appointment.patient_name&&<span>Patient: {appointment.patient_name}</span>}{call.patient.phone_number&&<span>Contact: {call.patient.phone_number}</span>}</section>}
  {call.error&&<p role="alert" className="call-error">{call.error}</p>}{!configured&&!active&&<p className="call-error">Voice credentials are not configured on the backend.</p>}
  <audio ref={audio} autoPlay playsInline controls={!!call.error||call.audioState==='blocked'} className={call.error||call.audioState==='blocked'?'audio-controls':'hidden-audio'}/>
  <div className="call-actions">{active?<><button className="round" onClick={call.toggleMute} disabled={!ready} aria-label={call.muted?'Unmute microphone':'Mute microphone'}>{call.muted?<MicOff/>:<Mic/>}</button><button className="round hangup" onClick={call.end} aria-label="End call"><PhoneOff/></button></>:<button className="start-call" onClick={call.start} disabled={!configured}><Phone size={18}/> Try call</button>}</div>
  <div className="phone-footer"><ShieldCheck size={14}/> Demo only · use fictional phone numbers</div>
 </aside>;
}
