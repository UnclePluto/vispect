import {ApiError} from '../../api/client';
let generation=0;
let sessionToken:string|null=null;
export function setPatientSessionToken(token:string|null){if(token!==sessionToken){generation++;sessionToken=token}}
export function invalidatePatientRequests(){generation++}
function stale(){return new ApiError({code:'patient_request_cancelled',message:'患者账号已变化，请重新加载',fields:{}},409)}
type Options={method?:string;body?:unknown;idempotencyKey?:string;signal?:AbortSignal};
function authEvent(status:number,code:string){if(status===401)window.dispatchEvent(new Event('vispect:patient-session-expired'));else if(code==='patient_session_changed')window.dispatchEvent(new Event('vispect:patient-session-changed'))}
export async function patientApi<T>(path:string,{method='GET',body,idempotencyKey,signal}:Options={}):Promise<T>{
 const current=generation,token=sessionToken,authentication=path.startsWith('/api/patient/auth/')||path==='/api/patient/csrf/'||path==='/api/patient/entry/resolve/';
 const headers:Record<string,string>={Accept:'application/json'};
 if(!['GET','HEAD','OPTIONS'].includes(method)){
  const csrf=await fetch(new URL('/api/patient/csrf/',window.location.origin),{credentials:'include',cache:'no-store',signal});
  if(!csrf.ok)throw new ApiError({code:'csrf_failed',message:'请求校验失效，请刷新后重试',fields:{}},403);
  headers['X-CSRFToken']=(await csrf.json()).csrf_token;
 }
 if(token)headers['X-Patient-Session-Token']=token;
 if(body!==undefined)headers['Content-Type']='application/json';
 if(idempotencyKey)headers['Idempotency-Key']=idempotencyKey;
 if(current!==generation)throw stale();
 const response=await fetch(new URL(path,window.location.origin),{method,body:body===undefined?undefined:JSON.stringify(body),headers,credentials:'include',cache:'no-store',signal});
 const data=await response.json().catch(()=>({code:'request_failed',message:'请求失败，请稍后重试',fields:{}}));
 if(current!==generation)throw stale();
 if(!authentication&&token){
  const check=await fetch(new URL('/api/patient/auth/me/',window.location.origin),{credentials:'include',cache:'no-store',signal,headers:{Accept:'application/json'}}),identity=await check.json();
  if(current!==generation)throw stale();
  if(!check.ok){authEvent(check.status,identity.code);throw new ApiError(identity,check.status)}
  if(identity.session_token!==token){authEvent(409,'patient_session_changed');throw stale()}
 }
 if(!response.ok){if(!authentication)authEvent(response.status,data.code);throw new ApiError(data,response.status)}
 return data as T;
}
