import {Alert,App,Button,Space,Spin,Typography} from 'antd';
import {Outlet,useParams} from 'react-router-dom';
import {useQuery} from '@tanstack/react-query';
import {ApiError,errorMessage} from '../../api/client';
import {usePatientAuth} from './PatientAuthProvider';
import {PatientLoginPage} from './PatientLoginPage';
import {PatientPasswordPage} from './PatientPasswordPage';
import {resolveEntry} from './api';
import './patient-portal.css';
export function PatientPortalLayout(){
 const {token}=useParams(),auth=usePatientAuth(),{modal}=App.useApp();
 function logout(){if(auth.hasUnsavedChanges())modal.confirm({title:'有未保存的填写内容，是否退出？',okText:'放弃修改并退出',cancelText:'继续填写',onOk:()=>auth.logout()});else void auth.logout().catch(()=>{})}
 const entry=useQuery({queryKey:['patient-entry',token],queryFn:({signal})=>resolveEntry(token!,signal),enabled:!!token});
 const badEntry=entry.error instanceof ApiError&&entry.error.status===404;
 return <div className="patient-portal"><header className="patient-header"><Typography.Text strong>智观云 · 患者填写</Typography.Text>{auth.envelope&&<Space wrap><span>已登录：{auth.envelope.user.phone}</span><Button type="link" onClick={logout}>退出登录</Button></Space>}</header><main className="patient-main">{(auth.loading||entry.isLoading)&&<div className="patient-status"><Spin aria-label="正在加载"/></div>}{(auth.error||entry.error)&&<Alert type="error" title={badEntry?'填写链接已失效，请联系医生':auth.error||errorMessage(entry.error)} action={!badEntry&&<Button onClick={()=>{void auth.refresh();void entry.refetch()}}>重试</Button>}/>}<div hidden={auth.loading||entry.isLoading||!!auth.error||!!entry.error}>{auth.initialized&&entry.data&&(auth.envelope?auth.envelope.next==='change_password'?<PatientPasswordPage/>:<Outlet/>:<PatientLoginPage entryToken={token!}/>)}</div></main><footer className="patient-footer">智观云健康管理平台</footer></div>
}
