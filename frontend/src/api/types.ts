export type Actor={account_id:string;tenant_id:string|null;role:'platform_admin'|'tenant_admin'|'doctor';doctor_id:string|null;username:string;name:string;must_change_password:boolean;tenant:{id:string;slug:string;name:string}|null};
export type Page<T>={count:number;results:T[]};
export type Revision={id:string;revision:number};
export type ErrorResponse={code:string;message:string;fields:Record<string,string[]>};
