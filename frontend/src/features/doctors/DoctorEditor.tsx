import {MemberPhoneFields} from '../accounts/MemberPhoneFields';
import {useWorkspaceDirty} from '../auth/WorkspaceChangesProvider';
import {useEffect,useState} from 'react';
import {Alert,Form,Input,Modal,Switch} from 'antd';
import {useActor} from '../auth/AuthProvider';
import {ApiError,errorMessage} from '../../api/client';
import {createDoctor,updateDoctor,type Doctor,type DoctorValues} from './api';
export function DoctorEditor({open,doctor,onCancel,onSaved}:{open:boolean;doctor?:Doctor|null;onCancel:()=>void;onSaved:()=>void}){
const [workspaceDirty,setWorkspaceDirty]=useState(false);useWorkspaceDirty(`doctor:${doctor?.id??'new'}`,open&&workspaceDirty);    const actor=useActor(),[form]=Form.useForm<DoctorValues>(),[busy,setBusy]=useState(false),[error,setError]=useState('');
    useEffect(()=>{if(open){setWorkspaceDirty(false);form.resetFields();form.setFieldsValue(doctor?{...doctor}:{enabled:true});setError('')}},[open,doctor,form]);
    async function save(){try{const values=await form.validateFields();setBusy(true);setError('');if(doctor)await updateDoctor(doctor,values);else await createDoctor(values);setWorkspaceDirty(false);onSaved()}catch(e){if(e instanceof ApiError){setError(e.message);form.setFields(Object.entries(e.fields).filter(([name])=>name in form.getFieldsValue()).map(([name,errors])=>({name:name as keyof DoctorValues,errors})))}else if(e instanceof Error)setError(errorMessage(e))}finally{setBusy(false)}}
    return <Modal title={doctor?'编辑医生':'新增医生'} open={open} onCancel={onCancel} onOk={save} okText="保存" cancelText="取消" confirmLoading={busy} destroyOnHidden><Form onValuesChange={()=>setWorkspaceDirty(true)} form={form} layout="vertical" preserve={false}>{error&&<Alert type="error" title={error} showIcon style={{marginBottom:16}}/>}<Form.Item label="姓名" name="name" rules={[{required:true,message:'请输入姓名'}]}><Input maxLength={200}/></Form.Item>{!doctor&&actor?.role==='tenant_admin'&&<MemberPhoneFields form={form} phoneName="login_phone" passwordName="initial_password"/>}{doctor&&<Form.Item label="登录手机号"><Input value={doctor.login_phone} disabled/></Form.Item>}<Form.Item label="联系方式" name="phone"><Input maxLength={40}/></Form.Item><Form.Item label="所属单位" name="organization"><Input maxLength={200}/></Form.Item><Form.Item label="科室" name="department"><Input maxLength={100}/></Form.Item><Form.Item label="职称" name="title"><Input maxLength={100}/></Form.Item>{actor?.role==='tenant_admin'&&<Form.Item label="本机构成员启用" name="enabled" valuePropName="checked"><Switch/></Form.Item>}</Form></Modal>
}
