import {useEffect,useRef,useState} from 'react';
import {PipecatClient} from '@pipecat-ai/client-js';
import {SmallWebRTCTransport} from '@pipecat-ai/small-webrtc-transport';
import {API} from '../../services/api';
export function useVoiceCall(audioRef){
 const client=useRef(null); const [state,setState]=useState('idle'); const [messages,setMessages]=useState([]); const [partial,setPartial]=useState(''); const [error,setError]=useState(''); const [muted,setMuted]=useState(false); const [seconds,setSeconds]=useState(0); const [speaking,setSpeaking]=useState(''); const botBuffer=useRef(''); const remoteAudio=useRef(null); const unifiedBotOutput=useRef(false);
 const append=(role,text)=>{if(text?.trim())setMessages(m=>[...m,{role,text}]);};
 useEffect(()=>{if(state!=='ready')return;const started=Date.now();const id=setInterval(()=>setSeconds(Math.floor((Date.now()-started)/1000)),1000);return()=>clearInterval(id);},[state]);
 useEffect(()=>()=>{const c=client.current;client.current=null;c?.disconnect().catch(()=>{});},[]);
 async function start(){
  if(client.current)return;setMessages([]);setPartial('');setError('');setSeconds(0);setMuted(false);setState('connecting');botBuffer.current='';unifiedBotOutput.current=false;remoteAudio.current=new MediaStream();
  let c;
  const current=()=>client.current===c;
  try{
   c=new PipecatClient({transport:new SmallWebRTCTransport({webrtcRequestParams:{endpoint:`${API}/api/voice/offer`}}),enableMic:true,enableCam:false,callbacks:{
    onBotReady:data=>{if(current()){const [major,minor]=String(data?.version||'0.0').split('.').map(Number);unifiedBotOutput.current=major>1||(major===1&&minor>=4);setState('ready');}},
    onDisconnected:()=>{if(current()){client.current=null;setState('ended');setSpeaking('');remoteAudio.current=null;if(audioRef.current)audioRef.current.srcObject=null;}},
    onUserTranscript:t=>{if(!current())return;if(t.final){append('Caller',t.text);setPartial('');}else setPartial(t.text);},
    onBotOutput:t=>{if(!current()||!unifiedBotOutput.current||!t.text)return;if(t.aggregated_by==='word')botBuffer.current+=t.text;else append('Assistant',t.text);},
    onBotLlmText:t=>{if(current()&&!unifiedBotOutput.current)botBuffer.current+=t.text||'';},
    onBotLlmStopped:()=>{if(current()&&!unifiedBotOutput.current){append('Assistant',botBuffer.current);botBuffer.current='';}},
    onBotStartedSpeaking:()=>{if(current())setSpeaking('Assistant');},
    onBotStoppedSpeaking:()=>{if(current()){if(unifiedBotOutput.current){append('Assistant',botBuffer.current);botBuffer.current='';}setSpeaking('');}},
    onUserStartedSpeaking:()=>{if(current())setSpeaking('Caller');},onUserStoppedSpeaking:()=>{if(current())setSpeaking('');},
    onTrackStarted:(track,participant)=>{if(!current()||track.kind!=='audio'||participant?.local)return;const stream=remoteAudio.current||new MediaStream();for(const previous of stream.getAudioTracks())if(previous!==track)stream.removeTrack(previous);if(!stream.getTracks().includes(track))stream.addTrack(track);remoteAudio.current=stream;if(audioRef.current){if(audioRef.current.srcObject!==stream)audioRef.current.srcObject=stream;audioRef.current.muted=false;audioRef.current.volume=1;audioRef.current.play().catch(()=>setError('Audio is connected but playback was blocked. Use the audio controls to start it.'));}},
    onTrackStopped:track=>{const stream=remoteAudio.current;if(!current()||track.kind!=='audio'||!stream)return;stream.removeTrack(track);if(!stream.getAudioTracks().length&&audioRef.current)audioRef.current.srcObject=null;},
    onError:e=>{if(current())setError(typeof e==='string'?e:e?.message||'Voice service reported an error.');}
   }});client.current=c;await c.connect();
  }catch(e){if(current()||!c){client.current=null;setError(e.message||'Unable to connect');setState('error');}try{await c?.disconnect();}catch{}}
 }
 async function end(){const c=client.current;client.current=null;setState('ended');setSpeaking('');setPartial('');append('Assistant',botBuffer.current);botBuffer.current='';try{await c?.disconnect();}catch(e){setError(e.message);}if(audioRef.current)audioRef.current.srcObject=null;remoteAudio.current=null;}
 async function toggleMute(){try{await client.current?.enableMic(muted);setMuted(!muted);}catch(e){setError(e.message);}}
 return {state,messages,partial,error,muted,seconds,speaking,start,end,toggleMute};
}
