import {render,screen,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {DynamicForm} from './DynamicForm';
import type {FormDefinition} from './types';
const definition:FormDefinition={protocol_version:1,title:'共用规则',questions:[{id:'a',title:'选择',type:'radio',options:[{id:'yes',label:'是'},{id:'no',label:'否'}]},{id:'b',title:'后续必填',type:'text',required:true,condition:{mode:'all',rules:[{question_id:'a',operator:'eq',value:'yes'}]}}]};
test('设计预览与实际填写使用相同可见题目，预览不保存答案',async()=>{
 const submit=vi.fn();const {container}=render(<><section aria-label="预览"><DynamicForm definition={definition} initialAnswers={{a:'no',b:'旧答案'}} mode="preview" readOnly={false} onSubmit={submit}/></section><section aria-label="填写"><DynamicForm definition={definition} initialAnswers={{a:'no',b:'旧答案'}} mode="entry" readOnly={false}/></section></>);
 const ids=(label:string)=>[...within(screen.getByRole('region',{name:label})).getAllByTestId('question')].map(e=>e.getAttribute('data-question-id'));
 expect(ids('预览')).toEqual(ids('填写'));expect(container.querySelector('[data-question-id="b"]')).toBeNull();await userEvent.click(within(screen.getByRole('region',{name:'预览'})).getByRole('button',{name:'验证预览'}));expect(submit).not.toHaveBeenCalled();
});
test('八种题型渲染且提交校验必填',async()=>{
 const types=['text','textarea','number','date','radio','checkbox','select','slider'] as const;
 const d:FormDefinition={protocol_version:1,title:'所有题型',questions:types.map(type=>({id:type,title:type,type,required:true,...(['radio','checkbox','select'].includes(type)?{options:[{id:'o',label:'选项'}]}:{}),...(type==='slider'?{min:0,max:10,step:1}:{})}))};
 const submit=vi.fn();render(<DynamicForm definition={d} initialAnswers={{}} mode="entry" readOnly={false} onSubmit={submit}/>);
 expect(screen.getAllByTestId('question')).toHaveLength(8);await userEvent.click(screen.getByRole('button',{name:'提交答案'}));expect(submit).not.toHaveBeenCalled();expect(screen.getAllByText('请填写此题')).toHaveLength(8);
});
