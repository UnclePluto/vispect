import Ajv from 'ajv';
import schema from '../../../contracts/form-definition.schema.json';
import type {FormDefinition} from './types';
const validate=new Ajv({strict:false,strictNumbers:true}).compile(schema);
export function validateDefinition(definition:FormDefinition,publish=false):Record<string,string[]>{
 const invalid={_definition:['invalid_definition']};
 if(!validate(definition))return invalid;
 const questions=definition.questions,ids=questions.map(q=>q.id);
 if(new Set(ids).size!==ids.length)return invalid;
 if(publish&&(!definition.title.trim()||!questions.length))return invalid;
 for(const [i,q] of questions.entries()){
  const kind=q.type,options=q.options??[],optionIds=options.map(o=>o.id);
  if(publish&&!q.title.trim())return invalid;
  if(new Set(optionIds).size!==optionIds.length)return invalid;
  if(['radio','checkbox','select'].includes(kind)&&!options.length)return invalid;
  if(!['radio','checkbox','select'].includes(kind)&&q.options!==undefined)return invalid;
  for(const [lo,hi] of [[q.min,q.max],[q.min_length,q.max_length],[q.min_selections,q.max_selections]])if(lo!==undefined&&hi!==undefined&&lo>hi)return invalid;
  if(kind==='slider'&&(q.min===undefined||q.max===undefined||q.step===undefined||q.min>=q.max))return invalid;
  if([q.min,q.max,q.precision].some(v=>v!==undefined)&&!['number','slider'].includes(kind))return invalid;
  if(q.step!==undefined&&kind!=='slider')return invalid;
  if([q.min_length,q.max_length].some(v=>v!==undefined)&&!['text','textarea'].includes(kind))return invalid;
  if([q.min_selections,q.max_selections].some(v=>v!==undefined)&&kind!=='checkbox')return invalid;
  if((q.min_selections??0)>options.length)return invalid;
  for(const rule of q.condition?.rules??[]){
   const index=ids.indexOf(rule.question_id),op=rule.operator,value=rule.value;
   if(index<0||index>=i)return invalid;
   const source=questions[index],sourceType=source.type;
   if(op!=='answered'&&value===undefined)return invalid;
   if(['gt','gte','lt','lte'].includes(op)&&(!['number','slider'].includes(sourceType)||typeof value!=='number'))return invalid;
   if(op==='contains'&&(sourceType!=='checkbox'||!source.options?.some(o=>o.id===value)))return invalid;
   if(['eq','neq'].includes(op)){
    if(sourceType==='checkbox')return invalid;
    if(['number','slider'].includes(sourceType)&&typeof value!=='number')return invalid;
    if(!['number','slider'].includes(sourceType)&&typeof value!=='string')return invalid;
    if(['radio','select'].includes(sourceType)&&!source.options?.some(o=>o.id===value))return invalid;
   }
  }
  if(q.jumps){if(!['radio','select'].includes(kind))return invalid;for(const [option,target] of Object.entries(q.jumps))if(!optionIds.includes(option)||!ids.slice(i+1).includes(target))return invalid;}
 }
 return {};
}
