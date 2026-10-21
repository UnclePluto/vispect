import {useState} from 'react';
import {Alert,Button,Form,Input,Typography} from 'antd';
import {errorMessage} from '../../api/client';
import {usePatientAuth} from './PatientAuthProvider';
export function PatientLoginPage({entryToken}:{entryToken:string}){
 const auth=usePatientAuth(),[busy,setBusy]=useState(false),[error,setError]=useState('');
 return <section className="patient-auth-card"><Typography.Title level={2}>患者登录</Typography.Title><Typography.Paragraph type="secondary">请使用医生开通的手机号和密码登录。</Typography.Paragraph>{error&&<Alert type="error" title={error}/>}<Form layout="vertical" onFinish={async(values:{phone:string;password:string})=>{setBusy(true);setError('');try{await auth.login(entryToken,values.phone,values.password)}catch(e){setError(errorMessage(e))}finally{setBusy(false)}}}><Form.Item label="手机号" name="phone" rules={[{required:true,message:'请输入手机号'}]}><Input autoComplete="username" inputMode="tel" maxLength={40}/></Form.Item><Form.Item label="密码" name="password" rules={[{required:true,message:'请输入密码'}]}><Input.Password autoComplete="current-password"/></Form.Item><Button type="primary" block htmlType="submit" loading={busy}>登录</Button></Form><Typography.Paragraph type="secondary" style={{marginTop:16}}>新账号默认密码为 888888，首次登录后须修改。</Typography.Paragraph></section>
}
