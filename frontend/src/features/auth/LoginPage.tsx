import {useState} from 'react';
import {Button,Card,Form,Input,Radio,Typography,Alert} from 'antd';
import {Navigate,useNavigate} from 'react-router-dom';
import {useAuth} from './AuthProvider';
import type {LoginValues} from './api';
import {errorMessage} from '../../api/client';
export function LoginPage(){
    const auth=useAuth(),navigate=useNavigate();const [kind,setKind]=useState<'tenant'|'platform'>('tenant'),[busy,setBusy]=useState(false),[error,setError]=useState('');
    if(auth.actor)return <Navigate to="/" replace/>;
    async function submit(values:LoginValues){setBusy(true);setError('');try{await auth.login(kind,values);navigate('/',{replace:true})}catch(e){setError(errorMessage(e))}finally{setBusy(false)}}
    return <div className="login-page"><Card className="login-card"><Typography.Title level={2}>Vispect 健康管理</Typography.Title><Typography.Paragraph type="secondary">机构独立空间 · 健康档案与研究随访</Typography.Paragraph><Radio.Group value={kind} onChange={e=>setKind(e.target.value)} options={[{label:'租户登录',value:'tenant'},{label:'平台管理',value:'platform'}]} optionType="button" buttonStyle="solid"/><Form layout="vertical" onFinish={submit} style={{marginTop:24}}>{kind==='tenant'&&<Form.Item name="tenant" label="租户标识" rules={[{required:true,message:'请输入租户标识'}]}><Input autoComplete="organization" placeholder="例如 clinic-a"/></Form.Item>}<Form.Item name="username" label="用户名" rules={[{required:true,message:'请输入用户名'}]}><Input autoComplete="username"/></Form.Item><Form.Item name="password" label="密码" rules={[{required:true,message:'请输入密码'}]}><Input.Password autoComplete="current-password"/></Form.Item>{error&&<Alert type="error" showIcon title={error} style={{marginBottom:16}}/>}<Button type="primary" htmlType="submit" block loading={busy}>登录</Button></Form></Card></div>
}
