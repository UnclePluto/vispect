import {Button,Card,Space} from 'antd';
import {PlusOutlined} from '@ant-design/icons';
import {labels} from './designerState';
import type {QuestionType} from '../../form-engine/types';
export function FieldPalette({onAdd,disabled}:{onAdd:(type:QuestionType)=>void;disabled:boolean}){return <Card title="添加题目" size="small"><Space orientation="vertical" style={{width:'100%'}}>{(Object.keys(labels) as QuestionType[]).map(type=><Button block key={type} icon={<PlusOutlined/>} disabled={disabled} onClick={()=>onAdd(type)}>{labels[type]}</Button>)}</Space></Card>}
