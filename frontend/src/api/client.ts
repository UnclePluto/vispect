import type {ErrorResponse} from './types';
export class ApiError extends Error{readonly code:string;readonly fields:Record<string,string[]>;readonly status:number;constructor(data:ErrorResponse,status:number){super(data.message);this.code=data.code;this.fields=data.fields;this.status=status}}
type Options={method?:string;body?:unknown;idempotencyKey?:string;signal?:AbortSignal};
export async function api<T>(path:string,{method='GET',body,idempotencyKey,signal}:Options={}):Promise<T>{
    const headers:Record<string,string>={'Accept':'application/json'};
    if(!['GET','HEAD','OPTIONS'].includes(method)){
        const csrf=await fetch(new URL('/api/auth/csrf/',window.location.origin),{credentials:'include',signal});
        const token=await csrf.json();headers['X-CSRFToken']=token.csrf_token;
    }
    if(body!==undefined)headers['Content-Type']='application/json';
    if(idempotencyKey)headers['Idempotency-Key']=idempotencyKey;
    const response=await fetch(new URL(path,window.location.origin),{method,body:body===undefined?undefined:JSON.stringify(body),headers,credentials:'include',signal});
    const data=await response.json().catch(()=>({code:'request_failed',message:'请求失败，请稍后重试',fields:{}}));
    if(!response.ok){if(response.status===401)window.dispatchEvent(new window.CustomEvent('vispect:session-expired'));throw new ApiError(data,response.status)}
    return data as T;
}
export function errorMessage(error:unknown){return error instanceof Error?error.message:'操作失败，请稍后重试'}
