import {useEffect,useState,useCallback,useRef} from 'react';
import {get} from '../../services/api';
export function useSchedule(){
 const [data,setData]=useState({doctors:[],slots:[],appointments:[],health:null});
 const [error,setError]=useState(''); const [loading,setLoading]=useState(true);
 const active=useRef(null);
 const refresh=useCallback(async()=>{
   active.current?.abort(); const controller=new AbortController(); active.current=controller;
   try { const [doctors,slots,appointments,health]=await Promise.all(['doctors','slots','appointments','health'].map(p=>get(p,controller.signal)));
     if(!controller.signal.aborted){setData({doctors,slots,appointments,health});setError('');}
   } catch(e){if(!controller.signal.aborted)setError(e.message);}
   finally{if(!controller.signal.aborted)setLoading(false);}
 },[]);
 useEffect(()=>{refresh();const timer=setInterval(refresh,2500);return()=>{clearInterval(timer);active.current?.abort();};},[refresh]);
 return {...data,error,loading,refresh};
}
