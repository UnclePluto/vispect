import {useEffect,useState} from 'react';
import {Alert,App,Button,Empty,Spin} from 'antd';
import {useBlocker,useParams} from 'react-router-dom';
import {useQuery} from '@tanstack/react-query';
import {ApiError,errorMessage} from '../../api/client';
import {resolveTasks,getTask} from './api';
import {usePatientAuth} from './PatientAuthProvider';
import {PatientChoice} from './PatientChoice';
import {PatientTaskForm} from './PatientTaskForm';
function temporary(error:unknown){return !(error instanceof ApiError)||error.status>=500}
export function PatientFillPage(){
 const {token}=useParams(),{modal}=App.useApp(),auth=usePatientAuth(),[selected,setSelected]=useState<string|null>(null),[dirty,setDirty]=useState(false),[reload,setReload]=useState(0),[error,setError]=useState('');
 const choices=useQuery({queryKey:['patient-tasks',token],queryFn:({signal})=>resolveTasks(token!,signal)});
 useEffect(()=>{if(!selected&&choices.data?.results.length===1)setSelected(choices.data.results[0].patient_id)},[selected,choices.data]);
 const valid=!!selected&&!!choices.data?.results.some(c=>c.patient_id===selected),task=useQuery({queryKey:['patient-task',token,selected],queryFn:({signal})=>getTask(token!,selected!,signal),enabled:valid});
 const blocker=useBlocker(({currentLocation,nextLocation})=>dirty&&currentLocation.pathname!==nextLocation.pathname);
 useEffect(()=>{auth.setUnsavedChanges(dirty);const guard=(event:BeforeUnloadEvent)=>{if(dirty){event.preventDefault();event.returnValue=''}};window.addEventListener('beforeunload',guard);return()=>{auth.setUnsavedChanges(false);window.removeEventListener('beforeunload',guard)}},[dirty,auth.setUnsavedChanges]);
 useEffect(()=>{if(blocker.state==='blocked'){const dialog=modal.confirm({title:'有未保存的填写内容，是否离开？',okText:'放弃修改并离开',cancelText:'继续填写',onOk:()=>blocker.proceed(),onCancel:()=>blocker.reset()});return()=>dialog.destroy()}},[blocker,modal]);
 async function switchPatient(){if(dirty){const okay=await new Promise<boolean>(resolve=>modal.confirm({title:'有未保存内容，是否切换患者？',okText:'放弃修改并切换',cancelText:'继续填写',onOk:()=>resolve(true),onCancel:()=>resolve(false)}));if(!okay)return}setDirty(false);setSelected(null);setError('')}
 async function refresh(){const result=await task.refetch();if(result.error)throw result.error}
 async function reloadTask(){setError('');try{await refresh();setReload(n=>n+1);setDirty(false)}catch(e){setError(errorMessage(e))}}
 if(choices.isLoading)return <Spin/>;
 if(choices.error&&(!choices.data||!temporary(choices.error)))return <Alert type="error" title={errorMessage(choices.error)}/>;
 const items=choices.data?.results??[];
 if(!items.length)return <Empty description="暂无对应填写任务，请联系医生"/>;
 if(!selected)return <PatientChoice choices={items} onSelect={setSelected}/>;
 if(task.isLoading||!valid)return <Spin/>;
 if(!task.data||(task.error&&!temporary(task.error)))return <Alert type="error" title={errorMessage(task.error)}/>;
 const queryError=choices.error||task.error;
 return <>{items.length>1&&<Button onClick={()=>void switchPatient()} style={{marginBottom:16}}>切换患者</Button>}{queryError&&<Alert type="error" title={errorMessage(queryError)} description="暂时无法刷新，当前填写内容已保留。" action={<Button onClick={()=>{void choices.refetch();void task.refetch()}}>重试查询</Button>}/>} {error&&<Alert type="error" title={error}/>}<PatientTaskForm key={`${token}:${selected}:${task.data.form_version_id}:${reload}`} task={task.data} entryToken={token!} onSaved={refresh} onReload={reloadTask} onDirtyChange={setDirty}/></>
}
