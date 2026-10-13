import {useEffect,useRef,useState} from 'react';
import {Alert,Button,Card,Descriptions,Popconfirm,Space,Spin,Tabs,Tag,Typography} from 'antd';
import {useQuery,useQueryClient} from '@tanstack/react-query';
import {useNavigate,useParams} from 'react-router-dom';
import {errorMessage,objectUnavailable} from '../../api/client';
import {getVisit,getVisitAnswers,completeVisit} from './api';
import {AnswerEntry} from './AnswerEntry';
export function VisitDetail(){
 const {id}=useParams(),navigate=useNavigate(),cache=useQueryClient(),[error,setError]=useState(''),[unavailable,setUnavailable]=useState(false),[busy,setBusy]=useState(false);const key=useRef(crypto.randomUUID());const visit=useQuery({queryKey:['visit',id],queryFn:()=>getVisit(id!)}),answers=useQuery({queryKey:['visit-answers',id],queryFn:()=>getVisitAnswers(id!),enabled:!!visit.data&&!visit.isError});
 function revoke(){setUnavailable(true);cache.removeQueries({queryKey:['visit',id],exact:true});cache.removeQueries({queryKey:['visit-answers',id],exact:true});cache.removeQueries({queryKey:['answer-history']})}
 useEffect(()=>{if(objectUnavailable(visit.error)||objectUnavailable(answers.error))revoke()},[visit.error,answers.error]);
 async function refresh(){await Promise.all(['visit','visit-answers','subjects','enrollment','calendar','dashboard','study-answers'].map(name=>cache.invalidateQueries({queryKey:[name]})))}
 async function complete(){setBusy(true);setError('');try{await completeVisit(id!,key.current);key.current=crypto.randomUUID();await refresh()}catch(e){if(objectUnavailable(e))revoke();else setError(errorMessage(e))}finally{setBusy(false)}}
 if(unavailable)return <Alert type="error" title="对象不存在或当前不可访问"/>;
 if(visit.isLoading||answers.isLoading)return <Spin/>;if(visit.error||answers.error||!visit.data)return <Alert type="error" title={errorMessage(visit.error??answers.error)}/>;
 const v=visit.data,records=answers.data?.results??[],missing=v.bindings?.filter(b=>b.required&&!records.some(a=>a.binding_id===b.id&&a.status==='submitted'))??[];
 return <><div className="page-heading"><div><Typography.Title level={3}>{v.stage_name}</Typography.Title><Typography.Text type="secondary">{v.study_name} · {v.patient_name}</Typography.Text></div><Space><Button onClick={()=>navigate(`/enrollments/${v.enrollment_id}`)}>返回受试者</Button><Popconfirm title="完成当前访视？" description="完成后答案只读，并开启下一阶段。" onConfirm={complete}><Button type="primary" loading={busy} disabled={!v.writable||missing.length>0}>完成当前访视</Button></Popconfirm></Space></div>{error&&<Alert type="error" title={error}/>} {missing.length>0&&v.writable&&<Alert type="warning" title={`还有 ${missing.length} 份必需表单未提交`} style={{marginBottom:16}}/>}{v.overdue&&<Alert type="warning" title="当前访视已超过时间窗口，仍允许获授权人员补录" style={{marginBottom:16}}/>}<Card style={{marginBottom:16}}><Descriptions column={3} items={[{key:'patient',label:'患者',children:v.patient_name},{key:'planned',label:'计划日期',children:v.planned_on},{key:'window',label:'允许窗口',children:`${v.window_start} 至 ${v.window_end}`},{key:'doctor',label:'随访医生',children:v.doctor_name},{key:'status',label:'状态',children:<Tag>{v.status==='completed'?'已完成':v.status==='stopped'?'已停止':v.is_current?'当前待完成':'待开启'}</Tag>}]} /></Card><Tabs destroyOnHidden={false} items={v.bindings?.map(b=>({key:b.id,label:`${b.definition.title}${b.required?' *':''} · ${b.respondent==='patient'?'患者':'医生'}`,children:<AnswerEntry key={b.id} visitId={v.id} binding={b} answer={records.find(a=>a.binding_id===b.id)} writable={v.writable} onSaved={refresh} onUnavailable={revoke}/>}))}/></>
}
