import {useEffect,useRef,useState} from 'react';
import {PipecatClient} from '@pipecat-ai/client-js';
import {SmallWebRTCTransport} from '@pipecat-ai/small-webrtc-transport';
import {API} from '../../services/api';

export function useVoiceCall(audioRef,onAppointmentChange){
 const client=useRef(null);
 const [state,setState]=useState('idle');
 const [messages,setMessages]=useState([]);
 const [partial,setPartial]=useState('');
 const [error,setError]=useState('');
 const [muted,setMuted]=useState(false);
 const [seconds,setSeconds]=useState(0);
 const [speaking,setSpeaking]=useState('');
 const [audioState,setAudioState]=useState('waiting');
 const [patient,setPatient]=useState({patient_name:'',phone_number:'',phone_confirmed:false});
 const [booking,setBooking]=useState(null);
 const botBuffer=useRef('');
 const remoteAudio=useRef(null);
 const unifiedBotOutput=useRef(false);

 const append=(role,text)=>{if(text?.trim())setMessages(m=>[...m,{role,text:text.trim()}]);};
 useEffect(()=>{if(state!=='ready')return;const started=Date.now();const id=setInterval(()=>setSeconds(Math.floor((Date.now()-started)/1000)),1000);return()=>clearInterval(id);},[state]);
 useEffect(()=>()=>{const c=client.current;client.current=null;c?.disconnect().catch(()=>{});},[]);

 async function start(){
  if(client.current)return;
  setMessages([]);setPartial('');setError('');setSeconds(0);setMuted(false);setSpeaking('');setAudioState('waiting');setPatient({patient_name:'',phone_number:'',phone_confirmed:false});setBooking(null);setState('connecting');
  botBuffer.current='';unifiedBotOutput.current=false;remoteAudio.current=new MediaStream();
  let c;
  const current=()=>client.current===c;
  try{
   c=new PipecatClient({transport:new SmallWebRTCTransport({webrtcRequestParams:{endpoint:`${API}/api/voice/offer`}}),enableMic:true,enableCam:false,callbacks:{
    onBotReady:data=>{if(current()){const [major,minor]=String(data?.version||'0.0').split('.').map(Number);unifiedBotOutput.current=major>1||(major===1&&minor>=4);setState('ready');}},
    onDisconnected:()=>{if(current()){client.current=null;setState('ended');setSpeaking('');setAudioState('waiting');remoteAudio.current=null;if(audioRef.current)audioRef.current.srcObject=null;}},
    onUserTranscript:t=>{if(!current())return;if(t.final){append('Caller',t.text);setPartial('');}else setPartial(t.text);},
    onBotOutput:t=>{if(!current()||!unifiedBotOutput.current||!t.text)return;if(t.aggregated_by==='word')botBuffer.current+=t.text;else append('Assistant',t.text);},
    onBotLlmText:t=>{if(current()&&!unifiedBotOutput.current)botBuffer.current+=t.text||'';},
    onBotLlmStopped:()=>{if(current()&&!unifiedBotOutput.current){append('Assistant',botBuffer.current);botBuffer.current='';}},
    onServerMessage:data=>{if(!current()||!data)return;if(data.type==='careline.patient')setPatient({patient_name:data.patient_name||'',phone_number:data.phone_number||'',phone_confirmed:!!data.phone_confirmed});else if(data.type==='careline.appointment_booked'){setBooking(data.appointment||null);if(data.appointment?.patient_name||data.phone_number)setPatient(p=>({...p,patient_name:data.appointment?.patient_name||p.patient_name,phone_number:data.phone_number||p.phone_number,phone_confirmed:true}));onAppointmentChange?.();}else if(data.type==='careline.appointment_cancelled'){setBooking(b=>b?{...b,status:'cancelled'}:b);onAppointmentChange?.();}},
    onBotStartedSpeaking:()=>{if(current())setSpeaking('Assistant');},
    onBotStoppedSpeaking:()=>{if(current()){if(unifiedBotOutput.current&&botBuffer.current){append('Assistant',botBuffer.current);botBuffer.current='';}setSpeaking('');}},
    onUserStartedSpeaking:()=>{if(current())setSpeaking('Caller');},onUserStoppedSpeaking:()=>{if(current())setSpeaking('');},
    onTrackStarted:(track,participant)=>{if(!current()||track.kind!=='audio'||participant?.local)return;const stream=remoteAudio.current||new MediaStream();for(const previous of stream.getAudioTracks())if(previous!==track)stream.removeTrack(previous);if(!stream.getTracks().includes(track))stream.addTrack(track);remoteAudio.current=stream;if(audioRef.current){if(audioRef.current.srcObject!==stream)audioRef.current.srcObject=stream;audioRef.current.muted=false;audioRef.current.volume=1;setAudioState('connected');audioRef.current.play().then(()=>{if(current())setAudioState('playing');}).catch(()=>{if(current()){setAudioState('blocked');setError('Voice audio arrived, but browser playback was blocked. Use the audio controls to start it.');}});}},
    onTrackStopped:(track,participant)=>{const stream=remoteAudio.current;if(!current()||track.kind!=='audio'||participant?.local||!stream)return;stream.removeTrack(track);if(!stream.getAudioTracks().length){if(audioRef.current)audioRef.current.srcObject=null;setAudioState('waiting');}},
    onError:e=>{if(current())setError(typeof e==='string'?e:e?.message||'Voice service reported an error.');}
   }});client.current=c;await c.connect();
  }catch(e){if(current()||!c){client.current=null;setError(e.message||'Unable to connect');setState('error');}try{await c?.disconnect();}catch{}}
 }
 async function end(){const c=client.current;client.current=null;setState('ended');setSpeaking('');setPartial('');if(unifiedBotOutput.current&&botBuffer.current)append('Assistant',botBuffer.current);botBuffer.current='';try{await c?.disconnect();}catch(e){setError(e.message);}if(audioRef.current)audioRef.current.srcObject=null;remoteAudio.current=null;setAudioState('waiting');}
 async function toggleMute(){try{await client.current?.enableMic(muted);setMuted(!muted);}catch(e){setError(e.message);}}
 return {state,messages,partial,error,muted,seconds,speaking,audioState,patient,booking,start,end,toggleMute};
}
