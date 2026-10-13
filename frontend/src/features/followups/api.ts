import {api,download} from '../../api/client';
import type {Page,Revision} from '../../api/types';
import type {FormDefinition,JSONValue} from '../../form-engine/types';
export type Enrollment=Revision&{study_id:string;study_name:string;patient_id:string;patient_name:string;patient_code:string;doctor_id:string;doctor_name:string;observation_code:string;enrollment_code:string|null;added_on:string;enrolled_on:string|null;state:'screening'|'awaiting_enrollment'|'following'|'completed'|'stopped';current_visit_id:string|null;stop_type:string;stop_reason:string;visits?:Visit[]};
export type VisitBinding={id:string;form_version_id:string;definition:FormDefinition;form_paused:boolean;respondent:'doctor'|'patient';required:boolean};
export type Visit=Revision&{enrollment_id:string;study_id:string;study_name:string;patient_id:string;patient_name:string;patient_code:string;doctor_id:string;doctor_name:string;stage_id:string;stage_name:string;stage_kind:string;position:number;planned_on:string;window_start:string;window_end:string;status:'pending'|'completed'|'stopped';is_current:boolean;is_today:boolean;overdue:boolean;writable:boolean;study_state:string;enrollment_state:string;bindings?:VisitBinding[];color?:string};
export type Answer=Revision&{visit_id:string;binding_id:string;form_version_id:string;respondent:'doctor'|'patient';is_proxy:boolean;recorded_by_id:string;recorded_by_name:string;answers:Record<string,JSONValue>;status:'draft'|'submitted';submitted_at:string|null;updated_at:string;patient_name?:string;patient_code?:string;stage_name?:string;form_title?:string;version_number?:number};
export type History={id:string;previous_answers:Record<string,JSONValue>;previous_revision:number;actor_name:string;previous_recorded_by_name:string;reason:string;created_at:string};
export const enrollmentLabels={screening:'筛选中',awaiting_enrollment:'待入组',following:'随访中',completed:'已完成',stopped:'已停止'};
export const getSubjects=(study:string,page=1,search='')=>api<Page<Enrollment>>(`/api/studies/${study}/subjects/?${new URLSearchParams({page:String(page),search})}`);
export const getEnrollment=(id:string)=>api<Enrollment>(`/api/enrollments/${id}/`);
export const addSubject=(study:string,body:{patient_id:string;doctor_id:string;observation_code:string},key:string)=>api<Enrollment>(`/api/studies/${study}/subjects/`,{method:'POST',body,idempotencyKey:key});
export const confirmEnrollment=(id:string,body:{enrollment_code:string;enrolled_on:string},key:string)=>api<Enrollment>(`/api/enrollments/${id}/confirm/`,{method:'POST',body,idempotencyKey:key});
export const transferFollowup=(e:Enrollment,doctor_id:string)=>api<Enrollment>(`/api/enrollments/${e.id}/transfer/`,{method:'POST',body:{doctor_id,expected_revision:e.revision}});
export const stopFollowup=(id:string,stop_type:string,reason:string,key:string)=>api<Enrollment>(`/api/enrollments/${id}/stop/`,{method:'POST',body:{stop_type,reason},idempotencyKey:key});
export const getVisit=(id:string)=>api<Visit>(`/api/visits/${id}/`);
export const getVisitAnswers=(id:string)=>api<{results:Answer[]}>(`/api/visits/${id}/answers/`);
export const saveDraftAnswer=(visit:string,binding:string,answers:Record<string,JSONValue>,expected_revision:number)=>api<Answer>(`/api/visits/${visit}/answers/`,{method:'POST',body:{binding_id:binding,answers,expected_revision,action:'draft'}});
export const submitAnswer=(visit:string,binding:string,answers:Record<string,JSONValue>,key:string)=>api<Answer>(`/api/visits/${visit}/answers/`,{method:'POST',body:{binding_id:binding,answers,action:'submit'},idempotencyKey:key});
export const reviseAnswer=(answer:string,answers:Record<string,JSONValue>,reason:string,expected_revision:number)=>api<Answer>(`/api/answers/${answer}/revise/`,{method:'POST',body:{answers,reason,expected_revision}});
export const completeVisit=(visit:string,key:string)=>api<Visit>(`/api/visits/${visit}/complete/`,{method:'POST',body:{},idempotencyKey:key});
export const getHistory=(answer:string,page=1)=>api<Page<History>>(`/api/answers/${answer}/revisions/?page=${page}`);
export const getStudyAnswers=(study:string,page=1)=>api<Page<Answer>>(`/api/studies/${study}/answers/?page=${page}`);
export const downloadAnswer=(id:string)=>download(`/api/answers/${id}/export/`,'answer.xlsx');
export const downloadStudy=(id:string)=>download(`/api/studies/${id}/export/`,'study-answers.xlsx');
export async function allPages<T>(load:(page:number)=>Promise<Page<T>>){const results:T[]=[];let page=1;while(true){const data=await load(page);results.push(...data.results);if(results.length>=data.count||!data.results.length)return results;page++}}
export const getCalendar=(from:string,to:string,study='',doctor='')=>allPages<Visit>(page=>api<Page<Visit>>(`/api/calendar/?${new URLSearchParams({from,to,page:String(page),page_size:'100',...(study?{study_id:study}:{}),...(doctor?{doctor_id:doctor}:{})})}`));
export function shanghaiToday(){const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());const part=(type:string)=>parts.find(p=>p.type===type)!.value;return `${part('year')}-${part('month')}-${part('day')}`}
