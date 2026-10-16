import {render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {App,ConfigProvider} from 'antd';
import zhCN from 'antd/locale/zh_CN';
import {http,HttpResponse} from 'msw';
import {setupServer} from 'msw/node';
import {AnswerEntry} from './AnswerEntry';
import type {FormDefinition} from '../../form-engine/types';
const definition:FormDefinition={protocol_version:1,title:'生活情况',questions:[{id:'living',type:'radio',title:'生活状态',required:true,options:[{id:'dependent',label:'需要协助'},{id:'independent',label:'独立生活'}]}]};
const binding={id:'b',form_version_id:'v1',definition,form_paused:false,respondent:'patient' as const,required:true};
const answer={id:'a',revision:3,visit_id:'visit',binding_id:'b',form_version_id:'v1',respondent:'patient' as const,is_proxy:false,recorded_by_id:'doctor',recorded_by_name:'李医生',recorded_by_kind:'staff' as const,recorded_by_patient_id:null,submission_source:'patient' as const,submitted_by_id:null,submitted_by_patient_id:'patient-login',submitted_by_name:'患者账号（尾号 0001）',answers:{living:'dependent'},status:'submitted' as const,submitted_at:'2026-10-16T08:00:00Z',updated_at:'2026-10-16T09:00:00Z',can_revise:true,revise_block_reason:null};
let revised:Record<string,unknown>|undefined;
const server=setupServer(http.get('*/api/auth/csrf/',()=>HttpResponse.json({csrf_token:'csrf'})),http.post('*/api/answers/a/revise/',async({request})=>{revised=await request.json() as Record<string,unknown>;return HttpResponse.json({...answer,revision:4,answers:revised.answers})}),http.get('*/api/answers/a/revisions/',()=>HttpResponse.json({count:1,results:[{id:'history',answer_id:'a',previous_revision:2,previous_answers:{living:'dependent'},new_answers:{living:'independent'},definition,previous_recorded_by_name:'患者账号（尾号 0001）',actor_name:'李医生',reason:'医生核对',created_at:'2026-10-16T09:00:00Z'}]})));
beforeAll(()=>server.listen({onUnhandledRequest:'error'}));afterEach(()=>{server.resetHandlers();revised=undefined});afterAll(()=>server.close());
function content(){return <QueryClientProvider client={new QueryClient()}><ConfigProvider locale={zhCN}><App><AnswerEntry visitId="visit" binding={binding} answer={answer} writable={false} onSaved={()=>{}} onUnavailable={()=>{}}/></App></ConfigProvider></QueryClientProvider>}
test('完成访视的患者答案按服务端权限修订，必须填写原因',async()=>{
 render(content());await userEvent.click(screen.getByRole('button',{name:'修订答案'}));await userEvent.click(screen.getByLabelText('独立生活'));await userEvent.click(screen.getByRole('button',{name:'提交答案'}));
 expect(await screen.findByText('请填写修订原因')).toBeVisible();await userEvent.type(screen.getByLabelText('修订原因'),'医生核对');await userEvent.click(screen.getByRole('button',{name:'提交答案'}));
 await waitFor(()=>expect(revised?.expected_revision).toBe(3));expect(revised?.reason).toBe('医生核对');expect(revised?.answers).toEqual({living:'independent'});
});
test('原始患者提交人与最近医生修改人分别显示',()=>{render(content());expect(screen.getByText('患者自填')).toBeVisible();expect(screen.getByText('患者账号（尾号 0001）')).toBeVisible();expect(screen.getByText('李医生')).toBeVisible()});
test('修订历史使用题目与选项文案展示修改前后值',async()=>{
 render(content());await userEvent.click(screen.getByRole('button',{name:'修订历史'}));await screen.findByText('医生核对');await userEvent.click(screen.getByRole('button',{name:/展开行|Expand row/}));
 expect(await screen.findByText('修改前')).toBeVisible();expect(screen.getAllByText('生活状态').length).toBeGreaterThan(0);expect(screen.getAllByText('需要协助').length).toBeGreaterThan(0);expect(screen.getAllByText('独立生活').length).toBeGreaterThan(0);
});
