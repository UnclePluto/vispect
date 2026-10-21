import type {Answer,History} from './api';
import type {Question,JSONValue} from '../../form-engine/types';
export function answerSource(answer:Answer){const source=answer.submission_source??(answer.respondent==='doctor'?'doctor':answer.is_proxy?'proxy':'patient');return {patient:'患者自填',proxy:'工作人员代录',doctor:'医生填写'}[source]}
export function displayHistoryValue(question:Question|undefined,value:JSONValue|undefined):string{
 if(value===undefined||value===null||value==='')return '未填写';
 if(question?.type==='radio'||question?.type==='select')return question.options?.find(option=>option.id===value)?.label??String(value);
 if(Array.isArray(value))return value.map(item=>question?.options?.find(option=>option.id===item)?.label??String(item)).join('、')||'未填写';
 return typeof value==='object'?JSON.stringify(value):String(value);
}
export function historyChanges(history:History){const questions=history.definition?.questions??[],ids=[...new Set([...questions.map(q=>q.id),...Object.keys(history.previous_answers),...Object.keys(history.new_answers??{})])];return ids.filter(id=>JSON.stringify(history.previous_answers[id])!==JSON.stringify(history.new_answers?.[id])).map(id=>{const q=questions.find(question=>question.id===id);return {id,title:q?.title??id,before:displayHistoryValue(q,history.previous_answers[id]),after:displayHistoryValue(q,history.new_answers?.[id])}})}
