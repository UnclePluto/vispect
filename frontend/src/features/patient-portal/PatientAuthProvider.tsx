import {createContext,Fragment,useCallback,useContext,useEffect,useRef,useState,type ReactNode} from 'react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {ApiError,errorMessage} from '../../api/client';
import {setPatientSessionToken,invalidatePatientRequests} from './client';
import type {PatientAuthEnvelope} from './types';
import {getPatientIdentity,patientLogin,changePatientPassword,patientLogout} from './api';
type Auth={envelope:PatientAuthEnvelope|null;loading:boolean;initialized:boolean;error:string;refresh:()=>Promise<void>;login:(token:string,phone:string,password:string)=>Promise<void>;changePassword:(oldPassword:string,newPassword:string)=>Promise<void>;logout:()=>Promise<void>;hasUnsavedChanges:()=>boolean;setUnsavedChanges:(dirty:boolean)=>void};
const Context=createContext<Auth|null>(null);
export function PatientAuthProvider({children}:{children:ReactNode}){
 const [cache]=useState(()=>new QueryClient({defaultOptions:{queries:{retry:false,refetchOnWindowFocus:'always'}}}));
 const [envelope,setEnvelope]=useState<PatientAuthEnvelope|null>(null),[loading,setLoading]=useState(true),[initialized,setInitialized]=useState(false),[error,setError]=useState('');
 const unsaved=useRef(false),state=useRef(envelope),epoch=useRef(0),refreshSequence=useRef(0),mounted=useRef(true),channel=useRef<BroadcastChannel|null>(null);
 const apply=useCallback((next:PatientAuthEnvelope|null)=>{
  if(state.current?.session_token!==next?.session_token){epoch.current++;setPatientSessionToken(next?.session_token??null);void cache.cancelQueries();cache.clear()}
  state.current=next;setEnvelope(next);
 },[cache]);
 const refresh=useCallback(async()=>{const sequence=++refreshSequence.current,current=epoch.current;setLoading(true);setError('');try{const next=await getPatientIdentity();if(mounted.current&&current===epoch.current)apply(next)}catch(e){if(mounted.current&&current===epoch.current){if(e instanceof ApiError&&e.status===401)apply(null);else setError(errorMessage(e))}}finally{if(mounted.current&&sequence===refreshSequence.current){setInitialized(true);setLoading(false)}}},[apply]);
 useEffect(()=>{mounted.current=true;void refresh();const expired=()=>{refreshSequence.current++;apply(null);setLoading(false)},changed=()=>{void refresh()};window.addEventListener('vispect:patient-session-expired',expired);window.addEventListener('vispect:patient-session-changed',changed);window.addEventListener('pageshow',changed);window.addEventListener('focus',changed);if(window.BroadcastChannel){channel.current=new BroadcastChannel('vispect.patient-session');channel.current.onmessage=changed}return()=>{mounted.current=false;epoch.current++;invalidatePatientRequests();setPatientSessionToken(null);window.removeEventListener('vispect:patient-session-expired',expired);window.removeEventListener('vispect:patient-session-changed',changed);window.removeEventListener('pageshow',changed);window.removeEventListener('focus',changed);channel.current?.close();channel.current=null;cache.clear()}},[refresh,apply,cache]);
 const setUnsavedChanges=useCallback((dirty:boolean)=>{unsaved.current=dirty},[]);
 const value:Auth={hasUnsavedChanges:()=>unsaved.current,setUnsavedChanges,envelope,loading,initialized,error,refresh,login:async(token,phone,password)=>{refreshSequence.current++;setLoading(false);epoch.current++;invalidatePatientRequests();const next=await patientLogin(token,phone,password);setError('');apply(next);channel.current?.postMessage({type:'changed'})},changePassword:async(oldPassword,newPassword)=>{refreshSequence.current++;setLoading(false);const next=await changePatientPassword(oldPassword,newPassword);apply(next);channel.current?.postMessage({type:'changed'})},logout:async()=>{refreshSequence.current++;setLoading(false);try{await patientLogout()}finally{apply(null);channel.current?.postMessage({type:'changed'})}}};
 return <QueryClientProvider client={cache}><Context.Provider value={value}><Fragment key={envelope?.session_token??'anonymous'}>{children}</Fragment></Context.Provider></QueryClientProvider>
}
export function usePatientAuth(){const auth=useContext(Context);if(!auth)throw new Error('缺少患者认证上下文');return auth}
