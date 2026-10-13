import {Checkbox,DatePicker,Input,InputNumber,Radio,Select,Slider} from 'antd';
import dayjs from 'dayjs';
import type {Question,JSONValue} from './types';
export function FieldControl({question:q,value,onChange,disabled}:{question:Question;value?:JSONValue;onChange:(value:JSONValue)=>void;disabled:boolean}){
 const props={disabled,'aria-label':q.title,id:`field-${q.id}`};const options=q.options?.map(o=>({value:o.id,label:o.label}));
 switch(q.type){
 case 'text':return <Input {...props} value={typeof value==='string'?value:''} onChange={e=>onChange(e.target.value)} maxLength={q.max_length}/>;
 case 'textarea':return <Input.TextArea {...props} value={typeof value==='string'?value:''} onChange={e=>onChange(e.target.value)} rows={4} maxLength={q.max_length}/>;
 case 'number':return <InputNumber {...props} value={typeof value==='number'?value:null} onChange={v=>onChange(v)} style={{width:'100%'}}/>;
 case 'date':return <DatePicker {...props} value={typeof value==='string'?dayjs(value):null} onChange={v=>onChange(v?v.format('YYYY-MM-DD'):null)} style={{width:'100%'}}/>;
 case 'radio':return <Radio.Group {...props} value={value} options={options} onChange={e=>onChange(e.target.value)}/>;
 case 'checkbox':return <Checkbox.Group {...props} value={Array.isArray(value)?value as string[]:[]} options={options} onChange={onChange}/>;
 case 'select':return <Select {...props} allowClear value={typeof value==='string'?value:undefined} options={options} onChange={v=>onChange(v??null)} style={{width:'100%'}}/>;
 case 'slider':return <div><Slider {...props} min={q.min} max={q.max} step={q.step} value={typeof value==='number'?value:q.min} onChange={onChange}/><InputNumber {...props} value={typeof value==='number'?value:null} min={q.min} max={q.max} step={q.step} onChange={onChange} placeholder="尚未填写"/></div>;
 }
}
