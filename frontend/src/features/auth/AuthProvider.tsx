import {App} from 'antd';
import {useWorkspaceChanges} from './WorkspaceChangesProvider';
import {advanceAuthGeneration,setWorkspaceToken,beginWorkspaceTransition} from '../../api/client';
import {createContext,useContext,useEffect,useRef,useState,type ReactNode} from 'react';
import {useQueryClient} from '@tanstack/react-query';
import type {AuthEnvelope} from '../../api/types';
import * as authApi from './api';
type Auth={user:AuthEnvelope['user']|null;actor:AuthEnvelope['actor'];next:AuthEnvelope['next']|null;workspaces:AuthEnvelope['workspaces'];workspaceToken:string|null;loading:boolean;switching:boolean;login:(values:authApi.LoginValues)=>Promise<void>;switchWorkspace:(accountId:string)=>Promise<boolean>;logout:()=>Promise<void>;refreshIdentity:()=>Promise<void>;refreshActor:()=>Promise<void>};
const Context=createContext<Auth|null>(null);
export function AuthProvider({children}:{children:ReactNode}){
 const changes=useWorkspaceChanges(),{message}=App.useApp();
 const cache=useQueryClient(),[state,setState]=useState<AuthEnvelope|null>(null),[loading,setLoading]=useState(true),[switching,setSwitching]=useState(false);
 const generation=useRef(0),channel=useRef<BroadcastChannel|null>(null),stateRef=useRef(state),switchInFlight=useRef(false);stateRef.current=state;
 function apply(next:AuthEnvelope|null){
   if(stateRef.current?.workspace_token&&stateRef.current.workspace_token!==next?.workspace_token){generation.current++;advanceAuthGeneration();cache.clear();changes.clear()}
   stateRef.current=next;setWorkspaceToken(next?.workspace_token??null);setState(next);
 }
 async function invalidate(clear=true){generation.current++;advanceAuthGeneration();await cache.cancelQueries();if(clear)cache.clear()}
 async function refreshIdentity(){const current=generation.current;const next=await authApi.getIdentity();if(current===generation.current){apply(next);setLoading(false)}}
 useEffect(()=>{const controller=new AbortController(),current=generation.current;authApi.getIdentity(controller.signal).then(next=>{if(!controller.signal.aborted&&current===generation.current)apply(next)}).catch(()=>{}).finally(()=>{if(!controller.signal.aborted&&current===generation.current)setLoading(false)});return()=>controller.abort()},[]);
 useEffect(()=>{
   const expired=()=>{void invalidate();apply(null);setLoading(false)};
   const stale=(external=false)=>{
     if(external){changes.clear();void message?.warning('机构已在其他页面切换，未保存内容未提交')}
     const end=beginWorkspaceTransition();
     void (async()=>{await invalidate();setLoading(true);try{await refreshIdentity()}catch{apply(null)}finally{setLoading(false);end()}})();
   };
   const staleEvent=(event:Event)=>stale(!!(event as CustomEvent).detail?.external);
   window.addEventListener('vispect:session-expired',expired);window.addEventListener('vispect:workspace-stale',staleEvent);
   if(window.BroadcastChannel){channel.current=new window.BroadcastChannel('vispect.workspace');channel.current.onmessage=event=>{if(event.data?.type==='workspace_changed')stale(true)}}
   return()=>{window.removeEventListener('vispect:session-expired',expired);window.removeEventListener('vispect:workspace-stale',staleEvent);channel.current?.close();channel.current=null};
 },[cache]);
 const value:Auth={user:state?.user??null,actor:state?.actor??null,next:state?.next??null,workspaces:state?.workspaces??[],workspaceToken:state?.workspace_token??null,loading,switching,
 login:async values=>{const end=beginWorkspaceTransition();try{await invalidate();const next=await authApi.login(values);apply(next);setLoading(false)}finally{end()}},
 switchWorkspace:async accountId=>{
   const token=stateRef.current?.workspace_token;if(!token||switchInFlight.current)return false;
   switchInFlight.current=true;let end:(()=>void)|undefined;
   try{
     if(!await changes.confirmChange())return false;
     end=beginWorkspaceTransition();setSwitching(true);await invalidate(false);
     try{const next=await authApi.switchWorkspace(accountId,token);apply(next);changes.clear();channel.current?.postMessage({type:'workspace_changed'});return true}
     catch(error){try{await refreshIdentity()}catch{apply(null)}throw error}
   }finally{end?.();setSwitching(false);switchInFlight.current=false}
 },
 logout:async()=>{const end=beginWorkspaceTransition();try{await invalidate();await authApi.logout()}finally{apply(null);setLoading(false);end();channel.current?.postMessage({type:'workspace_changed'})}},refreshIdentity,refreshActor:refreshIdentity};
 return <Context.Provider value={value}>{children}</Context.Provider>
}
export function useAuth(){const context=useContext(Context);if(!context)throw new Error('缺少账号上下文');return context}
export function useActor(){return useAuth().actor}
export function authDestination(next:Auth['next']){return next==='change_password'?'/change-password':next==='choose_workspace'||next==='no_workspace'?'/select-workspace':'/'}
