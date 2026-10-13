import {validateDefinition,validText} from './definition';
import type {FormDefinition,Question,JSONValue,EvaluationResult} from './types';
const missing=(value:JSONValue|undefined)=>value===undefined||value===null||value===''||(Array.isArray(value)&&value.length===0);
function conditionMatches(condition:Question['condition'],answers:Record<string,JSONValue>):boolean{
 if(!condition)return true;
 const values=condition.rules.map(r=>{
  if(!Object.hasOwn(answers,r.question_id))return false;
  const value=answers[r.question_id],target=r.value;
  switch(r.operator){case 'answered':return true;case 'eq':return value===target;case 'neq':return value!==target;case 'contains':return Array.isArray(value)&&value.includes(target!);case 'gt':return (value as number)>(target as number);case 'gte':return (value as number)>=(target as number);case 'lt':return (value as number)<(target as number);case 'lte':return (value as number)<=(target as number);}
 });
 return condition.mode==='all'?values.every(Boolean):values.some(Boolean);
}
// Decimal arithmetic from JSON's decimal representation, avoiding binary rounding.
function decimal(value:number):[bigint,number]{const [base,exponent='0']=String(value).toLowerCase().split('e');const places=(base.split('.')[1]??'').length;return [BigInt(base.replace('.','')),places-Number(exponent)];}
function precision(value:number){let [coefficient,scale]=decimal(value);while(coefficient!==0n&&coefficient%10n===0n){coefficient/=10n;scale--}return coefficient===0n?0:Math.max(0,scale)}
function onStep(value:number,min:number,step:number){const values=[decimal(value),decimal(min),decimal(step)],scale=Math.max(0,...values.map(v=>v[1]));const [a,b,c]=values.map(([n,s])=>n*10n**BigInt(scale-s));return (a-b)%c===0n;}
function answerError(q:Question,value:JSONValue):string|undefined{
 if(q.type==='text'||q.type==='textarea'){if(typeof value!=='string'||!validText(value))return 'invalid_type';if(Array.from(value).length<(q.min_length??0)||Array.from(value).length>(q.max_length??100000))return 'length'}
 else if(q.type==='number'||q.type==='slider'){if(typeof value!=='number'||!Number.isFinite(value))return 'invalid_type';if(value<(q.min??-1e12)||value>(q.max??1e12))return 'out_of_range';if(q.precision!==undefined&&precision(value)>q.precision)return 'precision';if(q.type==='slider'&&!onStep(value,q.min!,q.step!))return 'step'}
 else if(q.type==='date'){if(typeof value!=='string')return 'invalid_type';if(!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value))return 'invalid_date';const [year,month,day]=value.split('-').map(Number);const days=[31,year%4===0&&(year%100!==0||year%400===0)?29:28,31,30,31,30,31,31,30,31,30,31];if(year<1||month<1||month>12||day<1||day>days[month-1])return 'invalid_date'}
 else if(q.type==='radio'||q.type==='select'){if(typeof value!=='string')return 'invalid_type';if(!q.options?.some(o=>o.id===value))return 'invalid_option'}
 else if(q.type==='checkbox'){if(!Array.isArray(value)||value.some(v=>typeof v!=='string'))return 'invalid_type';if(new Set(value).size!==value.length||value.some(v=>!q.options?.some(o=>o.id===v)))return 'invalid_option';if(value.length<(q.min_selections??0)||value.length>(q.max_selections??q.options!.length))return 'selection_count'}
}
export function evaluateAnswers(definition:FormDefinition,answers:Record<string,JSONValue>,mode:'draft'|'submit'):EvaluationResult{
 const errors=validateDefinition(definition);if(Object.keys(errors).length)return {visible_ids:[],answers:{},errors};
 if(!['draft','submit'].includes(mode)||answers===null||Array.isArray(answers)||typeof answers!=='object')return {visible_ids:[],answers:{},errors:{_answers:['invalid_type']}};
 const ids=definition.questions.map(q=>q.id),result:EvaluationResult={visible_ids:[],answers:Object.create(null),errors:Object.create(null)};
 for(const key of Object.keys(answers))if(!ids.includes(key))result.errors[key]=['unknown_question'];
 let skipUntil=0;
 definition.questions.forEach((q,i)=>{
  if(i<skipUntil||!conditionMatches(q.condition,result.answers))return;
  result.visible_ids.push(q.id);const value=Object.hasOwn(answers,q.id)?answers[q.id]:undefined;
  if(missing(value)){if(mode==='submit'&&q.required)result.errors[q.id]=['required'];return}
  const error=answerError(q,value!);if(error){result.errors[q.id]=[error];return}
  result.answers[q.id]=value!;
  if((q.type==='radio'||q.type==='select')&&q.jumps&&Object.hasOwn(q.jumps,String(value)))skipUntil=ids.indexOf(q.jumps[String(value)]);
 });return result;
}
