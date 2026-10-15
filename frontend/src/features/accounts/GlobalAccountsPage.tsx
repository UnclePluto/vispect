import {useState} from 'react';
import {Alert,App,Button,Card,Form,Input,Modal,Popconfirm,Result,Space,Table,Tag,Typography} from 'antd';
import {useQuery,useQueryClient} from '@tanstack/react-query';
import {useActor} from '../auth/AuthProvider';
import {useWorkspaceDirty} from '../auth/WorkspaceChangesProvider';
import {errorMessage} from '../../api/client';
import {findAccount,setGlobalEnabled,resetGlobalPassword,type GlobalAccount} from './api';
import {normalizePhone} from './phone';
export function GlobalAccountsPage(){
 const actor=useActor(),{message}=App.useApp(),cache=useQueryClient(),[phone,setPhone]=useState<string|null>(null),[validation,setValidation]=useState(''),[reset,setReset]=useState<GlobalAccount|null>(null),[busy,setBusy]=useState(false),[form]=Form.useForm(),password=Form.useWatch('password',form);
 useWorkspaceDirty(`global-password:${reset?.id}`,!!reset&&!!password);
 const q=useQuery({queryKey:['global-accounts',phone],queryFn:()=>findAccount(phone!),enabled:actor?.role==='platform_admin'&&!!phone});
 if(actor?.role!=='platform_admin')return <Result status="403" title="此页面仅平台管理员可访问"/>;
 async function action(run:()=>Promise<GlobalAccount>){try{await run();await cache.invalidateQueries({queryKey:['global-accounts']});void message.success('账号已更新')}catch(e){void message.error(errorMessage(e))}}
 async function save(){try{const values=await form.validateFields();setBusy(true);await resetGlobalPassword(reset!,values.password);setReset(null);form.resetFields();await cache.invalidateQueries({queryKey:['global-accounts']});void message.success('密码已重置，用户需重新登录并修改密码')}catch(e){if(e instanceof Error)void message.error(errorMessage(e))}finally{setBusy(false)}}
 return <><Typography.Title level={3}>全局账号管理</Typography.Title><Typography.Paragraph type="secondary">统一手机号和密码。全局停用影响其所有机构，机构成员状态由各机构独立管理。</Typography.Paragraph><Card><Input.Search placeholder="输入完整手机号查询" style={{width:320,marginBottom:16}} onSearch={raw=>{const canonical=normalizePhone(raw);setValidation(canonical?'':'请输入有效的完整手机号');setPhone(canonical)}}/>{validation&&<Alert type="error" title={validation}/>} {q.error&&<Alert type="error" title={errorMessage(q.error)}/>}<Table rowKey="id" loading={q.isFetching} dataSource={q.data?.results??[]} pagination={false} columns={[{title:'手机号',dataIndex:'phone'},{title:'姓名',dataIndex:'name'},{title:'全局状态',render:(_,a:GlobalAccount)=><Tag color={a.enabled?'green':'default'}>{a.enabled?'启用':'停用'}</Tag>},{title:'密码状态',render:(_,a:GlobalAccount)=>a.must_change_password?'需修改初始密码':'正常'},{title:'操作',render:(_,a:GlobalAccount)=><Space><Popconfirm title={a.enabled?'全局停用该账号？所有机构会话将失效。':'启用全局账号？'} onConfirm={()=>action(()=>setGlobalEnabled(a,!a.enabled))}><Button>{a.enabled?'全局停用':'全局启用'}</Button></Popconfirm><Button onClick={()=>{form.resetFields();setReset(a)}}>重置密码</Button></Space>}]}/></Card><Modal title="重置全局密码" open={!!reset} onCancel={()=>{setReset(null);form.resetFields()}} onOk={save} okText="重置密码" cancelText="取消" confirmLoading={busy}><Form form={form} layout="vertical"><Alert type="warning" title="将撤销全部现有登录，用户下次登录必须修改密码。"/><Form.Item label="新密码" name="password" rules={[{required:true},{min:12,message:'至少 12 位'}]}><Input.Password autoComplete="new-password"/></Form.Item></Form></Modal></>
}
