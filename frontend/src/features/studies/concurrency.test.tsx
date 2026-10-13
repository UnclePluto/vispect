import {render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {App} from 'antd';
import {MemoryRouter,Routes,Route} from 'react-router-dom';
import {http,HttpResponse} from 'msw';
import {setupServer} from 'msw/node';
import {ProtocolEditor} from './ProtocolEditor';
import {StudyDetail} from './StudyDetail';
import type {Study} from './api';
vi.mock('../auth/AuthProvider',()=>({useActor:()=>({role:'tenant_admin'})}));
const original={id:'s',revision:1,name:'研究',code:'001',state:'draft',editable:true,protocol_frozen:false,owner_id:'d1',members:[{id:'d1',name:'医生甲'}],stages:[{name:'基线期',kind:'baseline',offset_days:0,window_before:0,window_after:3,bindings:[]}]} as Study;
const conflict={code:'revision_conflict',message:'内容已被修改，请刷新后重试',fields:{}};
const server=setupServer(http.get('*/api/auth/csrf/',()=>HttpResponse.json({csrf_token:'csrf'})),http.get('*/api/forms/version-options/',()=>HttpResponse.json({results:[],count:0})),http.get('*/api/studies/s/',()=>HttpResponse.json(original)),http.get('*/api/studies/s/subjects/',()=>HttpResponse.json({results:[],count:0})),http.get('*/api/doctors/options/',()=>HttpResponse.json({results:[{id:'d1',name:'医生甲'},{id:'d2',name:'医生乙'},{id:'d3',name:'医生丙'}]})));
beforeAll(()=>server.listen({onUnhandledRequest:'error'}));afterEach(()=>server.resetHandlers());afterAll(()=>server.close());
function wrapper(cache:QueryClient,children:React.ReactNode){return <QueryClientProvider client={cache}><App>{children}</App></QueryClientProvider>}
test('编辑流程期间收到新版本仍以编辑起点修订号保存',async()=>{
 let body:any;server.use(http.post('*/api/studies/s/protocol/',async({request})=>{body=await request.json();return HttpResponse.json(conflict,{status:409})}));
 const cache=new QueryClient();const content=(study:Study)=>wrapper(cache,<ProtocolEditor study={study} onSaved={()=>{}}/>);const {rerender}=render(content(original));
 await userEvent.type(screen.getByLabelText('阶段名称1'),'甲修改');rerender(content({...original,revision:2,stages:[{...original.stages![0],name:'乙已保存'}]}));await userEvent.click(screen.getByRole('button',{name:'保存访视流程'}));
 expect(await screen.findByText(conflict.message)).toBeInTheDocument();expect(body.expected_revision).toBe(1);expect(screen.getByLabelText('阶段名称1')).toHaveValue('基线期甲修改');
});
test('编辑成员期间查询刷新不会推进编辑起点修订号',async()=>{
 let body:any;server.use(http.post('*/api/studies/s/members/',async({request})=>{body=await request.json();return HttpResponse.json(conflict,{status:409})}));
 const cache=new QueryClient({defaultOptions:{queries:{retry:false}}});render(wrapper(cache,<MemoryRouter initialEntries={['/studies/s']}><Routes><Route path="/studies/:id" element={<StudyDetail/>}/></Routes></MemoryRouter>));
 await userEvent.click(await screen.findByRole('tab',{name:'研究成员'}));await userEvent.click(screen.getByRole('combobox'));await userEvent.click(screen.getByText('医生乙',{selector:'.ant-select-item-option-content'}));
 cache.setQueryData(['study','s'],{...original,revision:2,members:[...original.members!,{id:'d3',name:'医生丙'}]});await userEvent.click(screen.getByRole('button',{name:'保存成员'}));await waitFor(()=>expect(body).toBeDefined());expect(body.expected_revision).toBe(1);expect(body.doctor_ids).toEqual(['d1','d2']);expect(await screen.findByText(conflict.message)).toBeInTheDocument();
});
