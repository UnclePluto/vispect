import {api} from '../../api/client';
import type {Page} from '../../api/types';
import type {Patient} from '../patients/api';
export type PatientAccessPayload={id:string;patient_id:string;login_phone:string;must_change_password:boolean;enabled:boolean;revision:number};
export type PatientEntryPayload={id:string;binding_id:string;token:string;enabled:boolean;revision:number;url_path:string;created_at:string};
export type EntryOption={binding_id:string;study_id:string;study_name:string;stage_name:string;form_title:string;version_number:number;entry:PatientEntryPayload|null;create_block_reason:string|null};
export const openPatientAccess=(patient:Patient,login_phone:string)=>api<PatientAccessPayload>(`/api/patients/${patient.id}/portal-access/`,{method:'POST',body:{phone:login_phone,expected_revision:patient.revision}});
export async function getEntryOptions(formId:string){const results:EntryOption[]=[];let page=1;while(true){const data=await api<Page<EntryOption>>(`/api/forms/${formId}/patient-entry-options/?page=${page}&page_size=100`);results.push(...data.results);if(results.length>=data.count||!data.results.length)return results;page++}}
export const getBindingEntry=(id:string)=>api<PatientEntryPayload|null>(`/api/patient-form-bindings/${id}/entry/`);
export const createBindingEntry=(id:string)=>api<PatientEntryPayload>(`/api/patient-form-bindings/${id}/entry/`,{method:'POST',body:{}});
export const changeEntry=(entry:PatientEntryPayload,action:'disable'|'regenerate')=>api<PatientEntryPayload>(`/api/patient-form-entries/${entry.id}/${action}/`,{method:'POST',body:{expected_revision:entry.revision}});
