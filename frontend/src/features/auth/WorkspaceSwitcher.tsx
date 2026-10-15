import {useState} from 'react';
import {App,Select} from 'antd';
import {useNavigate} from 'react-router-dom';
import {useAuth} from './AuthProvider';
import type {WorkspaceOption} from '../../api/types';
import {errorMessage} from '../../api/client';
const roleNames={platform_admin:'平台管理员',tenant_admin:'机构管理员',doctor:'医生'};
export function workspaceLabel(w:WorkspaceOption){return `${w.tenant?.name??'平台管理中心'} · ${roleNames[w.role]} · ${w.tenant?.slug??'platform'} (${w.account_id.slice(0,8)})`}
export function WorkspaceSwitcher(){const auth=useAuth(),navigate=useNavigate(),{message}=App.useApp(),[busy,setBusy]=useState(false);return <Select aria-label="当前机构" style={{minWidth:260,maxWidth:'70%'}} value={auth.actor?.account_id} loading={busy} disabled={busy||auth.switching} placeholder="请选择机构" options={auth.workspaces.map(w=>({value:w.account_id,label:workspaceLabel(w)}))} onChange={async id=>{setBusy(true);try{if(await auth.switchWorkspace(id))navigate('/',{replace:true})}catch(e){void message.error(errorMessage(e))}finally{setBusy(false)}}}/>}
