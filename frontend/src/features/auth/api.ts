import {api} from '../../api/client';
import type {AuthEnvelope} from '../../api/types';
export type LoginValues={phone:string;password:string};
export const getIdentity=(signal?:AbortSignal)=>api<AuthEnvelope>('/api/auth/me/',{signal});
export const login=(body:LoginValues)=>api<AuthEnvelope>('/api/auth/login/',{method:'POST',body});
export const switchWorkspace=(account_id:string,workspace_token:string)=>api<AuthEnvelope>('/api/auth/switch-workspace/',{method:'POST',body:{account_id,workspace_token}});
export const logout=()=>api<{success:boolean}>('/api/auth/logout/',{method:'POST'});
export const changePassword=(body:{old_password:string;new_password:string})=>api<AuthEnvelope>('/api/auth/change-password/',{method:'POST',body});
