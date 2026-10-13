import type {FormDefinition,Question,QuestionType} from '../../form-engine/types';
export const newId=()=>`q_${crypto.randomUUID().replaceAll('-','')}`;
export const labels:Record<QuestionType,string>={text:'单行文本',textarea:'长文本',number:'数字',date:'日期',radio:'单选',checkbox:'多选',select:'下拉',slider:'滑动条'};
export function newField(type:QuestionType):Question{return {id:newId(),type,title:labels[type],...(['radio','checkbox','select'].includes(type)?{options:[{id:newId(),label:'选项一'},{id:newId(),label:'选项二'}]}:{}),...(type==='slider'?{min:0,max:10,step:1}:{})}}
export function cloneField(definition:FormDefinition,fieldId:string):FormDefinition{
 const questions=structuredClone(definition.questions),index=questions.findIndex(q=>q.id===fieldId);if(index<0)return definition;
 const copy={...questions[index],id:newId(),title:`${questions[index].title}（副本）`};const optionIds=new Map<string,string>();
 if(copy.options)copy.options=copy.options.map(o=>{const id=newId();optionIds.set(o.id,id);return {...o,id}});
 if(copy.condition){const rules=copy.condition.rules.filter(r=>questions.slice(0,index).some(q=>q.id===r.question_id));if(rules.length)copy.condition={...copy.condition,rules};else delete copy.condition}
 if(copy.jumps){copy.jumps=Object.fromEntries(Object.entries(copy.jumps).filter(([option,target])=>optionIds.has(option)&&questions.slice(index+1).some(q=>q.id===target)).map(([option,target])=>[optionIds.get(option)!,target]));if(!Object.keys(copy.jumps).length)delete copy.jumps}
 questions.splice(index+1,0,copy);return {...definition,questions};
}
export function moveField(definition:FormDefinition,fieldId:string,position:number):FormDefinition{const questions=[...definition.questions],index=questions.findIndex(q=>q.id===fieldId);if(index<0)return definition;const [q]=questions.splice(index,1);questions.splice(Math.max(0,Math.min(position,questions.length)),0,q);return {...definition,questions}}
export function batchOptions(text:string,old:{id:string;label:string}[]=[]){const used=new Set<string>();return text.split('\n').map(s=>s.trim()).filter(Boolean).map(label=>{const existing=old.find(o=>o.label===label&&!used.has(o.id));const option=existing??{id:newId(),label};used.add(option.id);return option})}
