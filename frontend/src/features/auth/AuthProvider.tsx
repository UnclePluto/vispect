import {advanceAuthGeneration,setWorkspaceToken} from '../../api/client';
import {createContext,useContext,useEffect,useRef,useState,type ReactNode} from 'react';
import {useQueryClient} from '@tanstack/react-query';
import type {AuthEnvelope} from '../../api/types';
import * as authApi from './api';
type Auth={user:AuthEnvelope['user']|null;actor:AuthEnvelope['actor'];next:AuthEnvelope['next']|null;workspaces:AuthEnvelope['workspaces'];workspaceToken:string|null;loading:boolean;login:(values:authApi.LoginValues)=>Promise<void>;switchWorkspace:(accountId:string)=>Promise<boolean>;logout:()=>Promise<void>;refreshIdentity:()=>Promise<void>;refreshActor:()=>Promise<void>};
const Context=createContext<Auth|null>(null);
export function AuthProvider({children}:{children:ReactNode}){
 const cache=useQueryClient(),[state,setState]=useState<AuthEnvelope|null>(null),[loading,setLoading]=useState(true);
 const generation=useRef(0),channel=useRef<BroadcastChannel|null>(null),stateRef=useRef(state);stateRef.current=state;
 function apply(next:AuthEnvelope|null){setWorkspaceToken(next?.workspace_token??null);setState(next)}
 async function invalidate(){generation.current++;advanceAuthGeneration();await cache.cancelQueries();cache.clear()}
 async function refreshIdentity(){const current=generation.current;const next=await authApi.getIdentity();if(current===generation.current){apply(next);setLoading(false)}}
 useEffect(()=>{const controller=new AbortController(),current=generation.current;authApi.getIdentity(controller.signal).then(next=>{if(!controller.signal.aborted&&current===generation.current)apply(next)}).catch(()=>{}).finally(()=>{if(!controller.signal.aborted&&current===generation.current)setLoading(false)});return()=>controller.abort()},[]);
 useEffect(()=>{
   const expired=()=>{void invalidate();apply(null);setLoading(false)};
   const stale=()=>{void (async()=>{await invalidate();setLoading(true);try{await refreshIdentity()}catch{apply(null)}finally{setLoading(false)}})()};
   window.addEventListener('vispect:session-expired',expired);window.addEventListener('vispect:workspace-stale',stale);
   if(window.BroadcastChannel){channel.current=new window.BroadcastChannel('vispect.workspace');channel.current.onmessage=event=>{if(event.data?.type==='workspace_changed')stale()}}
   return()=>{window.removeEventListener('vispect:session-expired',expired);window.removeEventListener('vispect:workspace-stale',stale);channel.current?.close();channel.current=null};
 },[cache]);
 const value:Auth={user:state?.user??null,actor:state?.actor??null,next:state?.next??null,workspaces:state?.workspaces??[],workspaceToken:state?.workspace_token??null,loading,
 login:async values=>{await invalidate();const next=await authApi.login(values);apply(next);setLoading(false)},
 switchWorkspace:async accountId=>{
   const token=stateRef.current?.workspace_token;if(!token)return false;
   await invalidate();setLoading(true);
   try{const next=await authApi.switchWorkspace(accountId,token);apply(next);channel.current?.postMessage({type:'workspace_changed'});return true}
   catch(error){try{await refreshIdentity()}catch{apply(null)}throw error}finally{setLoading(false)}
 },
 logout:async()=>{await invalidate();try{await authApi.logout()}finally{apply(null);setLoading(false);channel.current?.postMessage({type:'workspace_changed'})}},refreshIdentity,refreshActor:refreshIdentity};
 return <Context.Provider value={value}>{children}</Context.Provider>
}
export function useAuth(){const context=useContext(Context);if(!context)throw new Error('缺少账号上下文');return context}
export function useActor(){return useAuth().actor}
export function authDestination(next:Auth['next']){return next==='change_password'?'/change-password':next==='choose_workspace'||next==='no_workspace'?'/select-workspace':'/'}
