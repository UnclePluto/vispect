import cases from '../../../contracts/form-cases.json';
import {evaluateAnswers} from './engine';
import {validateDefinition} from './definition';
import type {FormDefinition,JSONValue} from './types';
test.each(cases)('$name',c=>{
 const definition=c.definition as FormDefinition;
 expect(evaluateAnswers(definition,c.answers as Record<string,JSONValue>,c.mode as 'draft'|'submit')).toEqual(c.expected);
 expect(Object.keys(validateDefinition(definition,true)).length>0).toBe('definition_invalid' in c&&c.definition_invalid===true);
});
test.each([Infinity,-Infinity,NaN])('拒绝非有限数字 %s',value=>{
 expect(evaluateAnswers({protocol_version:1,title:'测试',questions:[{id:'a',title:'数字',type:'number'}]},{a:value},'submit').errors).toEqual({a:['invalid_type']});
});
