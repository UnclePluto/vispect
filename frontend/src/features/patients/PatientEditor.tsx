import {useEffect,useState} from 'react';
import {Alert,Form,Input,Modal,Select} from 'antd';
import {useQuery} from '@tanstack/react-query';
import {useActor} from '../auth/AuthProvider';
import {errorMessage} from '../../api/client';
import {getDoctorOptions} from '../doctors/api';
import {createPatient,updatePatient,type Patient,type PatientValues} from './api';
export function PatientEditor({open,patient,onCancel,onSaved}:{open:boolean;patient?:Patient|null;onCancel:()=>void;onSaved:()=>void}){
 const actor=useActor(),[form]=Form.useForm<PatientValues>(),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const doctors=useQuery({queryKey:['doctor-options'],queryFn:getDoctorOptions,enabled:open&&!patient&&actor?.role==='tenant_admin'});
 useEffect(()=>{if(open){form.resetFields();form.setFieldsValue(patient?{code:patient.code,name:patient.name,gender:patient.gender,birth_date:patient.birth_date,phone:patient.phone,notes:patient.notes,status:patient.status}:{gender:'unknown',status:'active'});setError('')}},[open,patient,form]);
 async function save(){try{const values=await form.validateFields();setBusy(true);setError('');values.birth_date=values.birth_date||null;if(patient)await updatePatient(patient,values);else await createPatient(values);onSaved()}catch(e){if(e instanceof Error)setError(errorMessage(e))}finally{setBusy(false)}}
 return <Modal title={patient?'编辑患者':'新增患者'} open={open} onCancel={onCancel} onOk={save} okText="保存" cancelText="取消" confirmLoading={busy} destroyOnHidden><Form form={form} layout="vertical" preserve={false}>{error&&<Alert type="error" title={error}/>}<Form.Item label="档案编号" name="code" rules={[{required:true,message:'请输入档案编号'}]}><Input maxLength={100}/></Form.Item><Form.Item label="姓名" name="name" rules={[{required:true,message:'请输入姓名'}]}><Input maxLength={200}/></Form.Item><Form.Item label="性别" name="gender"><Select options={[{value:'unknown',label:'未知'},{value:'male',label:'男'},{value:'female',label:'女'},{value:'other',label:'其他'}]}/></Form.Item><Form.Item label="出生日期" name="birth_date"><Input type="date"/></Form.Item><Form.Item label="联系方式" name="phone"><Input maxLength={40}/></Form.Item><Form.Item label="管理状态" name="status" extra="管理状态不会自动停止研究随访"><Select options={[{value:'active',label:'在管'},{value:'inactive',label:'非在管'}]}/></Form.Item>{!patient&&actor?.role==='tenant_admin'&&<Form.Item label="负责医生" name="doctor_ids" rules={[{required:true,message:'请选择负责医生'}]}><Select mode="multiple" loading={doctors.isLoading} options={doctors.data?.results.map(d=>({value:d.id,label:d.name}))}/></Form.Item>}<Form.Item label="备注" name="notes"><Input.TextArea rows={3} maxLength={10000}/></Form.Item></Form></Modal>
}
