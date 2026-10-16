import {useEffect,useRef,useState} from 'react';
import {Alert,App,Button,Descriptions,Space,Tag} from 'antd';
import {DynamicForm} from '../../form-engine/DynamicForm';
import {ApiError} from '../../api/client';
import type {JSONValue} from '../../form-engine/types';
import type {PatientTaskPayload,PatientAnswer} from './types';
import {writeTask} from './api';
export function PatientTaskForm({task,entryToken,onSaved,onDirtyChange,onReload}:{task:PatientTaskPayload;entryToken:string;onSaved:()=>Promise<unknown>;onDirtyChange:(dirty:boolean)=>void;onReload:()=>Promise<void>}){
 const {modal}=App.useApp(),[revision,setRevision]=useState(task.answer?.revision??0),[confirmed,setConfirmed]=useState<PatientAnswer|null>(null),[conflict,setConflict]=useState(false),[dirty,setDirty]=useState(false),key=useRef(crypto.randomUUID()),mounted=useRef(true),cancelConfirm=useRef<()=>void>(()=>{});
 const answer=confirmed&&confirmed.revision>=(task.answer?.revision??0)?confirmed:task.answer,submitted=answer?.status==='submitted';
 const remoteChanged=dirty&&(task.answer?.revision??0)>revision,needsReview=conflict||remoteChanged;
 useEffect(()=>{if(!dirty&&task.answer&&task.answer.revision>revision)setRevision(task.answer.revision)},[dirty,task.answer,revision]);
 useEffect(()=>{onDirtyChange(dirty);return()=>onDirtyChange(false)},[dirty,onDirtyChange]);
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;cancelConfirm.current()}},[]);
 async function beforeSubmit(){return await new Promise<boolean>(resolve=>{const dialog=modal.confirm({title:'确认提交本次填写？',content:'提交后将无法自行修改，如需修正请联系医生。',okText:'确认提交',cancelText:'继续核对',onOk:()=>resolve(mounted.current),onCancel:()=>resolve(false)});cancelConfirm.current=()=>{dialog.destroy();resolve(false)}})}
 async function save(values:Record<string,JSONValue>,action:'draft'|'submit'){
  try{const result=await writeTask(entryToken,task.patient_id,values,action,revision,action==='submit'?key.current:undefined);if(!mounted.current)return;setRevision(result.revision);setConfirmed(result);setConflict(false);void onSaved().catch(()=>{})}catch(e){if(e instanceof ApiError&&e.status===409){setConflict(true);void onSaved().catch(()=>{})}throw e}
 }
 async function reload(){if(dirty){const okay=await new Promise<boolean>(resolve=>modal.confirm({title:'重新加载将放弃当前未保存内容',okText:'放弃并重新加载',cancelText:'保留输入',onOk:()=>resolve(true),onCancel:()=>resolve(false)}));if(!okay)return}await onReload()}
 return <section className="patient-task-form">
  <Descriptions size="small" column={1} items={[{key:'patient',label:'当前患者',children:`${task.patient_name} · ${task.patient_code}`},{key:'study',label:'研究',children:task.study_name},{key:'visit',label:'访视',children:task.stage_name}]}/>
  <Space wrap style={{margin:'16px 0'}}><Tag color={needsReview?'orange':submitted?'green':answer?'blue':'default'}>{needsReview?'需要核对':submitted?'已提交':answer?'已保存草稿':'尚未填写'}</Tag></Space>
  {submitted&&!needsReview&&<Alert type="success" title="填写已提交" description={answer?.submitted_at?`提交时间：${new Date(answer.submitted_at).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'})}，如需修改请联系医生。`:'如需修改请联系医生。'}/>}
  {!task.writable&&!submitted&&<Alert type="info" title={task.read_only_reason??'当前表单只读'}/>}
  {needsReview&&<Alert type="warning" title="服务器记录已变化，当前输入仍保留，请核对后重新加载。" action={<Button onClick={()=>void reload()}>重新加载</Button>}/>}
  <section aria-label={needsReview?'本机未保存内容':'本机填写内容'}>
   {needsReview&&<h3>本机未保存内容（尚未提交）</h3>}
   <DynamicForm definition={task.definition} initialAnswers={answer?.answers??{}} mode="entry" readOnly={needsReview||!task.writable||submitted} preserveDirtyOnReadOnly onDirtyChange={setDirty} beforeSubmit={beforeSubmit} onSaveDraft={values=>save(values,'draft')} onSubmit={values=>save(values,'submit')}/>
  </section>
  {remoteChanged&&task.answer&&<section aria-label="服务器最新记录">
   <h3>{task.answer.status==='submitted'?'服务器已提交的答案':'服务器最新草稿'}</h3>
   {task.answer.submitted_at&&<p>服务器提交时间：{new Date(task.answer.submitted_at).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'})}</p>}
   <DynamicForm definition={task.definition} initialAnswers={task.answer.answers} mode="entry" readOnly/>
  </section>}
 </section>
}
