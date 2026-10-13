import {render,screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {MemoryRouter,Routes,Route} from 'react-router-dom';
import {App} from 'antd';
import {http,HttpResponse} from 'msw';
import {setupServer} from 'msw/node';
import {cloneField,moveField,batchOptions} from './designerState';
import {FormDesigner} from './FormDesigner';
import type {FormDefinition} from '../../form-engine/types';
const definition:FormDefinition={protocol_version:1,title:'原表单',questions:[{id:'a',title:'原问题',type:'text'},{id:'b',title:'第二题',type:'text'}]};
test('复制创建新ID，移动保持ID，批量选项保留稳定ID',()=>{
 const copy=cloneField(definition,'a');expect(copy.questions).toHaveLength(3);expect(new Set(copy.questions.map(q=>q.id)).size).toBe(3);expect(moveField(definition,'b',0).questions[0].id).toBe('b');
 const old=[{id:'stable',label:'保留'}];expect(batchOptions('保留\n新增',old)[0].id).toBe('stable');expect(batchOptions('保留\n新增',old)).toHaveLength(2);
});
const server=setupServer(http.get('*/api/forms/f/',()=>HttpResponse.json({id:'f',title:'原表单',revision:1,editable:true,paused:false,draft_definition:definition,latest_version:null})),http.get('*/api/auth/csrf/',()=>HttpResponse.json({csrf_token:'csrf'})),http.patch('*/api/forms/f/',()=>HttpResponse.json({code:'revision_conflict',message:'记录已被其他人修改',fields:{}},{status:409})));
beforeAll(()=>server.listen({onUnhandledRequest:'error'}));afterAll(()=>server.close());
test('编辑属性及必填，保存冲突保留未保存内容',async()=>{
 render(<QueryClientProvider client={new QueryClient()}><App><MemoryRouter initialEntries={['/forms/f']}><Routes><Route path="/forms/:id" element={<FormDesigner/>}/></Routes></MemoryRouter></App></QueryClientProvider>);
 const title=await screen.findByLabelText('题目标题');await userEvent.clear(title);await userEvent.type(title,'尚未保存的新问题');await userEvent.click(screen.getByRole('switch',{name:'必填'}));await userEvent.click(screen.getByRole('button',{name:'保存草稿'}));expect(await screen.findByText('记录已被其他人修改')).toBeInTheDocument();expect(title).toHaveValue('尚未保存的新问题');expect(screen.getByRole('switch',{name:'必填'})).toBeChecked();
});
test('复制保留有效显示条件及选项跳题，并使用新选项ID',()=>{
 const d:FormDefinition={protocol_version:1,title:'复制规则',questions:[{id:'first',title:'前置题',type:'text'},{id:'choice',title:'选择',type:'radio',options:[{id:'yes',label:'是'}],condition:{mode:'all',rules:[{question_id:'first',operator:'answered'}]},jumps:{yes:'last'}},{id:'last',title:'最后题',type:'text'}]};
 const cloned=cloneField(d,'choice').questions[2];expect(cloned.condition).toEqual(d.questions[1].condition);expect(cloned.options?.[0].id).not.toBe('yes');expect(cloned.jumps?.[cloned.options![0].id]).toBe('last');
});
