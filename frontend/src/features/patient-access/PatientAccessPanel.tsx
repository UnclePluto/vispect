import {useState} from 'react';
import {Alert,Button,Card,Form,Input,Modal,Space,Tag,Typography} from 'antd';
import type {Patient} from '../patients/api';
import {useWorkspaceDirty} from '../auth/WorkspaceChangesProvider';
import {errorMessage} from '../../api/client';
import {openPatientAccess} from './api';
export function PatientAccessPanel({patient,onSaved}:{patient:Patient;onSaved:()=>void|Promise<unknown>}){
 const [open,setOpen]=useState(false),[phone,setPhone]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');
 useWorkspaceDirty(`patient-access:${patient.id}`,open&&!!phone);
 const access=patient.portal_access;
 async function save(){setBusy(true);setError('');try{await openPatientAccess(patient,phone);await onSaved();setOpen(false);setPhone('')}catch(e){setError(errorMessage(e))}finally{setBusy(false)}}
 return <Card size="small" title="患者填写账号" style={{marginTop:20}}>{access?<Space wrap><Typography.Text>{access.login_phone}</Typography.Text><Tag color={access.enabled?'green':'default'}>{access.enabled?'已开通':'不可用'}</Tag>{access.must_change_password&&<Tag>首次登录需改密</Tag>}</Space>:<><Typography.Paragraph type="secondary">开通后可扫码登录并填写已入组研究的患者表单。</Typography.Paragraph><Button onClick={()=>{setPhone(patient.phone);setError('');setOpen(true)}}>开通填写账号</Button></>}<Modal title="开通患者填写账号" open={open} onCancel={()=>setOpen(false)} onOk={save} confirmLoading={busy} okText="开通" cancelText="取消" destroyOnHidden><Form layout="vertical">{error&&<Alert type="error" title={error}/>}<Form.Item label="登录手机号" required><Input aria-label="登录手机号" value={phone} onChange={e=>setPhone(e.target.value)} autoComplete="tel" maxLength={40}/></Form.Item><Alert type="info" title="新账号默认密码为 888888，首次登录必须修改；已有账号保留原密码。"/></Form></Modal></Card>
}
