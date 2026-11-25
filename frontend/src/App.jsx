import {AudioLines} from 'lucide-react';
import ScheduleBoard from './features/schedule-board/ScheduleBoard';
import {useSchedule} from './features/schedule-board/useSchedule';
import PhoneScreen from './features/voice-call/PhoneScreen';
export default function App(){const schedule=useSchedule();return <><header className="header"><div className="brand"><div className="brand-icon"><AudioLines size={24}/></div><div><strong>careline<span>.</span></strong><small>Reception workspace</small></div></div><div className="connection"><i className={schedule.error?'offline':''}/>{schedule.error?'Backend offline':schedule.health?'Backend connected':'Checking backend'}</div></header><main><ScheduleBoard schedule={schedule}/><PhoneScreen configured={schedule.health?.voice==='configured'&&!schedule.error}/></main><footer className="page-footer">CARELINE / APPOINTMENT OPERATIONS <span>Local demonstration · Asia/Kolkata</span></footer></>}
