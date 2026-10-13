import {api} from '../../api/client';
import type {Page,Revision} from '../../api/types';
import type {FormDefinition} from '../../form-engine/types';
export type FormVersion={id:string;form_id:string;number:number;definition:FormDefinition;created_at:string};
export type FormRecord=Revision&{title:string;description:string;paused:boolean;editable:boolean;owner_id:string;draft_definition?:FormDefinition;latest_version:FormVersion|null;updated_at:string;deleted_at:string|null};
export const getForms=(page=1,search='')=>api<Page<FormRecord>>(`/api/forms/?page=${page}&search=${encodeURIComponent(search)}`);
export const getForm=(id:string)=>api<FormRecord>(`/api/forms/${id}/`);
export const createForm=(definition:FormDefinition)=>api<FormRecord>('/api/forms/',{method:'POST',body:{definition}});
export const saveDraft=(form:FormRecord,definition:FormDefinition)=>api<FormRecord>(`/api/forms/${form.id}/`,{method:'PATCH',body:{definition,expected_revision:form.revision}});
export const publishForm=(form:FormRecord,key:string)=>api<FormVersion>(`/api/forms/${form.id}/publish/`,{method:'POST',idempotencyKey:key,body:{expected_revision:form.revision}});
export const setFormPaused=(form:FormRecord,paused:boolean)=>api<FormRecord>(`/api/forms/${form.id}/${paused?'pause':'resume'}/`,{method:'POST',body:{expected_revision:form.revision}});
export const deleteForm=(form:FormRecord)=>api<FormRecord>(`/api/forms/${form.id}/`,{method:'DELETE',body:{expected_revision:form.revision}});
export const getVersions=(id:string)=>api<Page<FormVersion>>(`/api/forms/${id}/versions/`);
export type VersionOption={id:string;form_id:string;title:string;number:number;paused:boolean};
export async function getVersionOptions(){const results:VersionOption[]=[];let page=1;while(true){const data=await api<Page<VersionOption>>(`/api/forms/version-options/?page=${page}&page_size=100`);results.push(...data.results);if(results.length>=data.count||!data.results.length)return results;page++}}
export type FormReferences={studies:{id:string;name:string;state:string}[];pending_visits:number};
export const getFormReferences=(id:string)=>api<FormReferences>(`/api/forms/${id}/references/`);
