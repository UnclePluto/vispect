import {createContext,useContext,useEffect,useRef,useState,type ReactNode} from 'react';
import {useQueryClient} from '@tanstack/react-query';
import type {Actor} from '../../api/types';
import * as authApi from './api';
type Auth={actor:Actor|null;loading:boolean;login:(kind:'tenant'|'platform',values:authApi.LoginValues)=>Promise<void>;logout:()=>Promise<void>;refreshActor:()=>Promise<void>};
const Context=createContext<Auth|null>(null);
export function AuthProvider({children}:{children:ReactNode}){
    const cache=useQueryClient();const [actor,setActor]=useState<Actor|null>(null);const [loading,setLoading]=useState(true);
    const identityGeneration=useRef(0);
    useEffect(()=>{const controller=new AbortController(),generation=identityGeneration.current;authApi.getIdentity(controller.signal).then(next=>{if(!controller.signal.aborted&&generation===identityGeneration.current)setActor(next)}).catch(()=>{}).finally(()=>{if(!controller.signal.aborted)setLoading(false)});return()=>controller.abort()},[]);
    useEffect(()=>{const expired=()=>{identityGeneration.current++;setActor(null);void cache.cancelQueries().finally(()=>cache.clear())};window.addEventListener('vispect:session-expired',expired);return()=>window.removeEventListener('vispect:session-expired',expired)},[cache]);
    const value:Auth={actor,loading,login:async(kind,values)=>{identityGeneration.current++;await cache.cancelQueries();cache.clear();const next=await authApi.login(kind,values);setActor(next)},logout:async()=>{identityGeneration.current++;try{await authApi.logout()}finally{await cache.cancelQueries();cache.clear();setActor(null)}},refreshActor:async()=>{const generation=identityGeneration.current,next=await authApi.getIdentity();if(generation===identityGeneration.current)setActor(next)}};
    return <Context.Provider value={value}>{children}</Context.Provider>
}
export function useAuth(){const context=useContext(Context);if(!context)throw new Error('缺少账号上下文');return context}
export function useActor(){return useAuth().actor}
