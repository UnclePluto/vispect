import type {FormDefinition,JSONValue} from '../../form-engine/types';
export type PatientAuthEnvelope={user:{id:string;phone:string;must_change_password:boolean};next:'change_password'|'ready';session_token:string};
export type PatientTaskChoice={patient_id:string;patient_name:string;patient_code:string;task_state:string};
export type PatientAnswer={id:string;revision:number;answers:Record<string,JSONValue>;status:'draft'|'submitted';submitted_at:string|null;submission_source?:string|null};
export type PatientTaskPayload={patient_id:string;patient_name:string;patient_code:string;study_name:string;stage_name:string;form_version_id:string;definition:FormDefinition;answer:PatientAnswer|null;task_state:string;writable:boolean;read_only_reason:string|null};
