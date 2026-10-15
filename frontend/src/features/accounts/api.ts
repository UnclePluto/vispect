import {api} from '../../api/client';
import type {Page,Revision} from '../../api/types';
export type GlobalAccount=Revision&{phone:string;name:string;enabled:boolean;must_change_password:boolean};
export const findAccount=(phone:string)=>api<Page<GlobalAccount>>(`/api/platform/accounts/?phone=${encodeURIComponent(phone)}`);
export const setGlobalEnabled=(account:GlobalAccount,enabled:boolean)=>api<GlobalAccount>(`/api/platform/accounts/${account.id}/enabled/`,{method:'POST',body:{enabled,expected_revision:account.revision}});
export const resetGlobalPassword=(account:GlobalAccount,new_password:string)=>api<GlobalAccount>(`/api/platform/accounts/${account.id}/reset-password/`,{method:'POST',body:{new_password,expected_revision:account.revision}});
