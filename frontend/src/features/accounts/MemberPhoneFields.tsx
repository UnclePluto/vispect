import {useEffect,useState} from 'react';
import {Alert,Form,Input,Spin,type FormInstance} from 'antd';
import {api,errorMessage} from '../../api/client';
import {normalizePhone} from './phone';
export function MemberPhoneFields({form,phoneName,passwordName,label='登录手机号'}:{form:FormInstance;phoneName:string;passwordName:string;label?:string}){
 const raw=Form.useWatch(phoneName,form),phone=normalizePhone(raw),[status,setStatus]=useState<{phone:string;registered:boolean}|null>(null),[error,setError]=useState('');
 useEffect(()=>{
   form.setFieldValue(passwordName,undefined);setStatus(null);setError('');if(!phone)return;
   const controller=new AbortController();let active=true;
   api<{phone:string;registered:boolean}>('/api/members/phone-status/',{method:'POST',body:{phone},signal:controller.signal}).then(result=>{if(active)setStatus(result)}).catch(e=>{if(active&&!controller.signal.aborted)setError(errorMessage(e))});
   return()=>{active=false;controller.abort()};
 },[phone,form,passwordName]);
 const current=status?.phone===phone?status:null;
 return <><Form.Item label={label} name={phoneName} rules={[{required:true,message:'请输入登录手机号'},{validator:(_,value)=>normalizePhone(value)?Promise.resolve():Promise.reject(new Error('请输入有效的中国大陆手机号'))}]}><Input inputMode="tel" autoComplete="off"/></Form.Item>{phone&&!current&&!error&&<Spin size="small"/>}{error&&<Alert type="error" title={error}/>} {current?.registered?<Alert type="info" title="该手机号已注册，加入机构后保留原密码。" style={{marginBottom:16}}/>:current&&<Form.Item label="初始密码" name={passwordName} rules={[{required:true,message:'请设置初始密码'},{min:12,message:'至少 12 位'}]} extra="仅新用户需要设置，首次登录必须修改"><Input.Password autoComplete="new-password"/></Form.Item>}</>
}
