import {Button,Card,Space,Typography} from 'antd';
import type {PatientTaskChoice} from './types';
export function PatientChoice({choices,onSelect}:{choices:PatientTaskChoice[];onSelect:(patient:string)=>void}){return <Card><Typography.Title level={2}>选择填写患者</Typography.Title><Typography.Paragraph type="secondary">请核对姓名和档案编号，再开始填写。</Typography.Paragraph><Space orientation="vertical" style={{width:'100%'}}>{choices.map(choice=><Button block size="large" key={choice.patient_id} onClick={()=>onSelect(choice.patient_id)}>{choice.patient_name} · {choice.patient_code}</Button>)}</Space></Card>}
