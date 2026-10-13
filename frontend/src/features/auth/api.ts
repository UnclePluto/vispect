import {api} from '../../api/client';
import type {Actor} from '../../api/types';
export type LoginValues={tenant?:string;username:string;password:string};
export const getIdentity=(signal?:AbortSignal)=>api<Actor>('/api/auth/me/',{signal});
export const login=(kind:'tenant'|'platform',body:LoginValues)=>api<Actor>(`/api/auth/${kind}-login/`,{method:'POST',body});
export const logout=()=>api<{success:boolean}>('/api/auth/logout/',{method:'POST'});
export const changePassword=(body:{old_password:string;new_password:string})=>api<Actor>('/api/auth/change-password/',{method:'POST',body});
