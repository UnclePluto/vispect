import {createContext,useCallback,useContext,useEffect,useId,useMemo,useRef,type ReactNode} from 'react';
import {App} from 'antd';
type Changes={register:(key:string,dirty:boolean)=>void;confirmChange:()=>Promise<boolean>;clear:()=>void};
const fallback:Changes={register:()=>{},confirmChange:async()=>true,clear:()=>{}};
const Context=createContext<Changes>(fallback);
export function WorkspaceChangesProvider({children}:{children:ReactNode}){
 const {modal}=App.useApp(),entries=useRef(new Set<string>()),pending=useRef<Promise<boolean>|null>(null);
 const register=useCallback((key:string,dirty:boolean)=>{if(dirty)entries.current.add(key);else entries.current.delete(key)},[]);
 const clear=useCallback(()=>entries.current.clear(),[]);
 const confirmChange=useCallback(()=>{
  if(!entries.current.size)return Promise.resolve(true);
  if(pending.current)return pending.current;
  pending.current=new Promise<boolean>(resolve=>{modal.confirm({title:'有未保存的修改，是否切换机构？',content:'切换后将关闭当前编辑内容，未保存的修改不会提交。',okText:'放弃修改并切换',cancelText:'取消',onOk:()=>{pending.current=null;resolve(true)},onCancel:()=>{pending.current=null;resolve(false)}})});
  return pending.current;
 },[modal]);
 const value=useMemo(()=>({register,clear,confirmChange}),[register,clear,confirmChange]);
 return <Context.Provider value={value}>{children}</Context.Provider>
}
export function useWorkspaceChanges(){return useContext(Context)}
export function useWorkspaceDirty(key:string,dirty:boolean){const {register}=useContext(Context),id=useId(),entry=key+':'+id;useEffect(()=>{register(entry,dirty);return()=>register(entry,false)},[register,entry,dirty])}
