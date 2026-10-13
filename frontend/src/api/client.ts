import type {ErrorResponse} from './types';
export class ApiError extends Error{readonly code:string;readonly fields:Record<string,string[]>;readonly status:number;constructor(data:ErrorResponse,status:number){super(data.message);this.code=data.code;this.fields=data.fields;this.status=status}}
let authGeneration=0;
export function advanceAuthGeneration(){authGeneration++}
function cancelled(){return new ApiError({code:'request_cancelled',message:'账号已切换，该请求已取消',fields:{}},409)}
type Options={method?:string;body?:unknown;idempotencyKey?:string;signal?:AbortSignal};
export async function api<T>(path:string,{method='GET',body,idempotencyKey,signal}:Options={}):Promise<T>{
    const requestGeneration=authGeneration;
    const headers:Record<string,string>={'Accept':'application/json'};
    if(!['GET','HEAD','OPTIONS'].includes(method)){
        const csrf=await fetch(new URL('/api/auth/csrf/',window.location.origin),{credentials:'include',signal});
        const token=await csrf.json();headers['X-CSRFToken']=token.csrf_token;
    }
    if(body!==undefined)headers['Content-Type']='application/json';
    if(idempotencyKey)headers['Idempotency-Key']=idempotencyKey;
    if(requestGeneration!==authGeneration)throw cancelled();
    const response=await fetch(new URL(path,window.location.origin),{method,body:body===undefined?undefined:JSON.stringify(body),headers,credentials:'include',signal});
    const data=await response.json().catch(()=>({code:'request_failed',message:'请求失败，请稍后重试',fields:{}}));
    if(requestGeneration!==authGeneration)throw cancelled();
    if(!response.ok){if(response.status===401)window.dispatchEvent(new window.CustomEvent('vispect:session-expired'));throw new ApiError(data,response.status)}
    return data as T;
}
export function errorMessage(error:unknown){return error instanceof Error?error.message:'操作失败，请稍后重试'}
export async function download(path:string,filename:string){
 const requestGeneration=authGeneration;
 const response=await fetch(new URL(path,window.location.origin),{credentials:'include',headers:{Accept:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/json'}});
 if(requestGeneration!==authGeneration)throw cancelled();
 if(!response.ok){if(response.status===401)window.dispatchEvent(new window.CustomEvent('vispect:session-expired'));throw new ApiError(await response.json(),response.status)}
 const blob=await response.blob();if(requestGeneration!==authGeneration)throw cancelled();
 const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export function objectUnavailable(error:unknown){return error instanceof ApiError&&[403,404].includes(error.status)}
