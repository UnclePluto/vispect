import {useState} from 'react';
import {Button,Card,Form,Input,Typography,Alert} from 'antd';
import {Navigate} from 'react-router-dom';
import {useAuth,authDestination} from './AuthProvider';
import type {LoginValues} from './api';
import {errorMessage} from '../../api/client';
export function LoginPage(){
 const auth=useAuth(),[busy,setBusy]=useState(false),[error,setError]=useState('');
 if(auth.user)return <Navigate to={authDestination(auth.next)} replace/>;
 async function submit(values:LoginValues){setBusy(true);setError('');try{await auth.login(values)}catch(e){setError(errorMessage(e))}finally{setBusy(false)}}
 return <div className="login-page"><Card className="login-card"><Typography.Title level={2}>智观云健康管理平台</Typography.Title><Typography.Paragraph type="secondary">机构独立空间 · 健康档案与研究随访</Typography.Paragraph><Form layout="vertical" onFinish={submit} style={{marginTop:24}}><Form.Item name="phone" label="手机号" rules={[{required:true,message:'请输入手机号'},{pattern:/^(?:(?:\+86|0086)?[\s-]*)?1[3-9](?:[\s-]*\d){9}$/,message:'请输入有效的中国大陆手机号'}]}><Input autoComplete="username" inputMode="tel"/></Form.Item><Form.Item name="password" label="密码" rules={[{required:true,message:'请输入密码'}]}><Input.Password autoComplete="current-password"/></Form.Item>{error&&<Alert type="error" showIcon title={error} style={{marginBottom:16}}/>}<Button type="primary" htmlType="submit" block loading={busy}>登录</Button></Form></Card></div>
}
