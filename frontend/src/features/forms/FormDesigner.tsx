import {PatientEntryDialog} from '../patient-access/PatientEntryDialog';
import {useWorkspaceDirty} from '../auth/WorkspaceChangesProvider';
import {useEffect,useRef,useState} from 'react';
import {Alert,Button,Card,Input,Space,Spin,Tag,Typography} from 'antd';
import {useParams} from 'react-router-dom';
import {useQuery,useQueryClient} from '@tanstack/react-query';
import {errorMessage} from '../../api/client';
import {validateDefinition} from '../../form-engine/definition';
import type {FormDefinition,Question} from '../../form-engine/types';
import {getForm,saveDraft,publishForm,type FormRecord} from './api';
import {FieldPalette} from './FieldPalette';
import {QuestionList} from './QuestionList';
import {FieldProperties} from './FieldProperties';
import {FormPreview} from './FormPreview';
import {cloneField,moveField,newField} from './designerState';
export function FormDesigner(){
 const {id}=useParams(),cache=useQueryClient();const q=useQuery({queryKey:['form',id],queryFn:()=>getForm(id!)});const [record,setRecord]=useState<FormRecord>(),[definition,setDefinition]=useState<FormDefinition>(),[selected,setSelected]=useState(''),[error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false),[entryOpen,setEntryOpen]=useState(false),[preview,setPreview]=useState(false),[dirty,setDirty]=useState(false);const loaded=useRef('');
 useWorkspaceDirty(`form:${id}`,dirty);
 useEffect(()=>{if(q.data&&loaded.current!==id){loaded.current=id!;setRecord(q.data);const d=q.data.draft_definition??q.data.latest_version?.definition;setDefinition(d);setSelected(d?.questions[0]?.id??'');setDirty(false)}},[q.data,id]);
 useEffect(()=>{const guard=(e:BeforeUnloadEvent)=>{if(dirty){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',guard);return()=>window.removeEventListener('beforeunload',guard)},[dirty]);
 if(q.isLoading||!record||!definition)return q.error?<Alert type="error" title={errorMessage(q.error)}/>:<Spin/>;
 if(q.isError)return <Alert type="error" title={errorMessage(q.error)}/>;
 const current=definition.questions.find(x=>x.id===selected),invalid=Object.keys(validateDefinition(definition)).length>0;
 function update(next:FormDefinition){setDefinition(next);setDirty(true);setNotice('');setError('')}
 function structural(next:FormDefinition){if(Object.keys(validateDefinition(next)).length){setError('调整会使条件引用或跳题目标无效，请先修改关联规则');return}update(next)}
 async function save(publish=false){if(!record||!definition)return;setBusy(true);setError('');setNotice('');try{const saved=await saveDraft(record,definition);setRecord(saved);setDirty(false);if(publish){await publishForm(saved,crypto.randomUUID());const fresh=await getForm(saved.id);setRecord(fresh);setNotice('发布成功，已有研究继续使用原版本')}else setNotice('草稿已保存');await cache.invalidateQueries({queryKey:['forms']})}catch(e){setError(errorMessage(e))}finally{setBusy(false)}}
 const replace=(question:Question)=>update({...definition,questions:definition.questions.map(x=>x.id===question.id?question:x)});
 return <><div className="page-heading"><div><Typography.Title level={3}>表单设计</Typography.Title><Space><Tag>{record.latest_version?`最新发布 v${record.latest_version.number}`:'未发布'}</Tag>{record.paused&&<Tag color="orange">所有版本已暂停填写</Tag>}{dirty&&<Tag color="gold">有未保存修改</Tag>}</Space></div><Space wrap><Button disabled={!record.latest_version} onClick={()=>setEntryOpen(true)}>填写链接</Button><Button disabled={invalid} onClick={()=>setPreview(true)}>预览</Button>{record.editable&&<><Button loading={busy} disabled={invalid} onClick={()=>save()}>保存草稿</Button><Button type="primary" loading={busy} disabled={invalid||Object.keys(validateDefinition(definition,true)).length>0} onClick={()=>save(true)}>保存并发布</Button></>}</Space></div>{error&&<Alert type="error" title={error} style={{marginBottom:16}}/>}{notice&&<Alert type="success" title={notice} style={{marginBottom:16}}/>}{invalid&&<Alert type="warning" title="当前定义存在无效配置，请检查题目范围、选项、条件和跳题" style={{marginBottom:16}}/>}<Card style={{marginBottom:16}}><Space orientation="vertical" style={{width:'100%'}}><Input aria-label="表单名称" value={definition.title} disabled={!record.editable||busy} placeholder="表单名称" maxLength={500} onChange={e=>update({...definition,title:e.target.value})}/><Input.TextArea aria-label="表单说明" value={definition.description} disabled={!record.editable||busy} placeholder="表单说明" rows={2} onChange={e=>update({...definition,description:e.target.value})}/></Space></Card><div className="designer-grid"><FieldPalette disabled={!record.editable||busy} onAdd={type=>{const field=newField(type);update({...definition,questions:[...definition.questions,field]});setSelected(field.id)}}/><QuestionList questions={definition.questions} selected={selected} onSelect={setSelected} readOnly={!record.editable||busy} onMove={(field,pos)=>structural(moveField(definition,field,pos))} onCopy={field=>update(cloneField(definition,field))} onDelete={field=>structural({...definition,questions:definition.questions.filter(x=>x.id!==field)})}/>{current?<FieldProperties question={current} questions={definition.questions} onChange={replace} readOnly={!record.editable||busy}/>:<Card size="small">请选择题目编辑属性</Card>}</div><PatientEntryDialog formId={id} open={entryOpen} onClose={()=>setEntryOpen(false)}/><FormPreview definition={definition} open={preview} onClose={()=>setPreview(false)}/></>
}
