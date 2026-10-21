import {render,screen,waitFor,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {http,HttpResponse} from 'msw';
import {setupServer} from 'msw/node';
import {App} from '../../app/App';
import {router} from '../../app/router';
import type {PatientAnswer,PatientTaskChoice} from './types';
const definition={protocol_version:1,title:'随访问卷',questions:[{id:'q1',type:'text',title:'健康情况',required:true}]};
let choices:PatientTaskChoice[],answers:Map<string,PatientAnswer>,failSubmit:boolean,failDraft:boolean,readOnly:boolean,keys:string[],posted:string[];
const envelope={user:{id:'login',phone:'+8613800000001',must_change_password:false},next:'ready',session_token:'fill-context'};
const server=setupServer(
 http.get('*/api/patient/auth/me/',()=>HttpResponse.json(envelope)),http.get('*/api/patient/csrf/',()=>HttpResponse.json({csrf_token:'csrf'})),http.post('*/api/patient/entry/resolve/',()=>HttpResponse.json({available:true})),
 http.post('*/api/patient/tasks/resolve/',()=>HttpResponse.json({count:choices.length,results:choices})),
 http.get('*/api/patient/entries/qr-fill/patients/:patient/',({params})=>{const patient=choices.find(c=>c.patient_id===params.patient)!;const answer=answers.get(patient.patient_id)??null;return HttpResponse.json({...patient,study_name:'研究甲',stage_name:'基线期',form_version_id:'v1',definition,answer,writable:!readOnly&&answer?.status!=='submitted',read_only_reason:readOnly?'该访视尚未开放':answer?.status==='submitted'?'答案已提交':null})}),
 http.post('*/api/patient/entries/qr-fill/patients/:patient/answers/',async({request,params})=>{const body=await request.json() as {action:'draft'|'submit';answers:Record<string,string>;expected_revision:number};const patient=String(params.patient);posted.push(patient);if(body.action==='submit'){keys.push(request.headers.get('Idempotency-Key')??'');if(failSubmit){failSubmit=false;return HttpResponse.json({code:'temporary_failure',message:'网络暂时不可用，请重试',fields:{}},{status:503})}}else if(failDraft)return HttpResponse.json({code:'temporary_failure',message:'草稿保存失败',fields:{}},{status:503});const answer:PatientAnswer={id:'answer-'+patient,answers:body.answers,revision:body.expected_revision+1,status:body.action==='submit'?'submitted':'draft',submitted_at:body.action==='submit'?'2026-10-16T08:00:00Z':null};answers.set(patient,answer);return HttpResponse.json(answer)})
);
beforeAll(()=>server.listen({onUnhandledRequest:'error'}));beforeEach(async()=>{choices=[{patient_id:'p1',patient_name:'同名患者',patient_code:'P001',task_state:'writable'}];answers=new Map();failSubmit=false;failDraft=false;readOnly=false;keys=[];posted=[];await router.navigate('/patient/fill/qr-fill')});afterEach(()=>server.resetHandlers());afterAll(()=>server.close());
async function confirmSubmit(){await userEvent.click(screen.getByRole('button',{name:'提交答案'}));await userEvent.click(await screen.findByRole('button',{name:'确认提交'}))}
test('同名患者按档案编号选择，提交归属明确选择的人',async()=>{
 choices.push({patient_id:'p2',patient_name:'同名患者',patient_code:'P002',task_state:'writable'});render(<App/>);
 await userEvent.click(await screen.findByRole('button',{name:/P002/}));await userEvent.type(await screen.findByLabelText('健康情况'),'第二位患者的答案');await confirmSubmit();
 expect(await screen.findByText('填写已提交')).toBeVisible();expect(posted).toEqual(['p2']);
});
test('网络失败保留输入和幂等键，重试成功后只读',async()=>{
 failSubmit=true;render(<App/>);await userEvent.type(await screen.findByLabelText('健康情况'),'需要保留的答案');await confirmSubmit();
 expect(await screen.findByText('网络暂时不可用，请重试')).toBeVisible();expect(screen.getByLabelText('健康情况')).toHaveValue('需要保留的答案');await confirmSubmit();
 expect(await screen.findByText('填写已提交')).toBeVisible();expect(keys).toHaveLength(2);expect(keys[0]).toBeTruthy();expect(keys[1]).toBe(keys[0]);expect(screen.getByLabelText('健康情况')).toBeDisabled();
});
test('已提交患者表单没有编辑或再次提交入口',async()=>{
 answers.set('p1',{id:'a',revision:1,status:'submitted',submitted_at:'2026-10-16T08:00:00Z',answers:{q1:'已交答案'}});render(<App/>);
 expect(await screen.findByLabelText('健康情况')).toHaveValue('已交答案');expect(screen.getByLabelText('健康情况')).toBeDisabled();expect(screen.queryByRole('button',{name:'提交答案'})).not.toBeInTheDocument();
});
test('保存失败后切换患者，不把未保存答案带给另一人',async()=>{
 choices.push({patient_id:'p2',patient_name:'同名患者',patient_code:'P002',task_state:'writable'});failDraft=true;render(<App/>);
 await userEvent.click(await screen.findByRole('button',{name:/P001/}));await userEvent.type(await screen.findByLabelText('健康情况'),'第一人的未保存答案');await userEvent.click(screen.getByRole('button',{name:'保存草稿'}));await screen.findByText('草稿保存失败');await userEvent.click(screen.getByRole('button',{name:'切换患者'}));await userEvent.click(await screen.findByRole('button',{name:'放弃修改并切换'}));await userEvent.click(await screen.findByRole('button',{name:/P002/}));
 await waitFor(()=>expect(screen.getByLabelText('健康情况')).toHaveValue(''));expect(screen.queryByDisplayValue('第一人的未保存答案')).not.toBeInTheDocument();
});
test('未开放访视显示原因且不能提交',async()=>{
 readOnly=true;render(<App/>);expect(await screen.findByText('该访视尚未开放')).toBeVisible();expect(screen.queryByRole('button',{name:'提交答案'})).not.toBeInTheDocument();
});

import {act} from '@testing-library/react';
import {focusManager} from '@tanstack/react-query';
test.each(['choices','task'])('后台%s查询暂时失败时保留未保存输入，恢复后仍可填写',async(kind)=>{
 render(<App/>);await userEvent.type(await screen.findByLabelText('健康情况'),'尚未保存的答案');
 const failure=()=>HttpResponse.json({code:'temporary_failure',message:'查询暂时失败',fields:{}},{status:503});
 server.use(kind==='choices'?http.post('*/api/patient/tasks/resolve/',failure):http.get('*/api/patient/entries/qr-fill/patients/:patient/',failure));
 await act(async()=>{focusManager.setFocused(false);focusManager.setFocused(true)});
 expect(await screen.findByText('查询暂时失败')).toBeVisible();expect(screen.getByLabelText('健康情况')).toHaveValue('尚未保存的答案');
 server.resetHandlers();await userEvent.click(screen.getByRole('button',{name:'重试查询'}));
 await waitFor(()=>expect(screen.queryByText('查询暂时失败')).not.toBeInTheDocument());expect(screen.getByLabelText('健康情况')).toHaveValue('尚未保存的答案');expect(screen.getByLabelText('健康情况')).toBeEnabled();
});
test.each(['choices','task'])('后台%s查询确认无权访问时清除受保护填写内容',async(kind)=>{
 render(<App/>);await userEvent.type(await screen.findByLabelText('健康情况'),'受保护的答案');
 const unavailable=()=>HttpResponse.json({code:'not_found',message:'填写任务已失效',fields:{}},{status:404});
 server.use(kind==='choices'?http.post('*/api/patient/tasks/resolve/',unavailable):http.get('*/api/patient/entries/qr-fill/patients/:patient/',unavailable));
 await act(async()=>{focusManager.setFocused(false);focusManager.setFocused(true)});
 await screen.findByText('填写任务已失效');expect(screen.queryByLabelText('健康情况')).not.toBeInTheDocument();
});
test('患者提交后后台修订，刷新显示最新只读答案',async()=>{
 render(<App/>);await userEvent.type(await screen.findByLabelText('健康情况'),'患者初次答案');await confirmSubmit();await screen.findByText('填写已提交');
 answers.set('p1',{id:'answer-p1',revision:2,status:'submitted',submitted_at:'2026-10-16T08:00:00Z',answers:{q1:'医生核对后的答案'}});
 await act(async()=>{focusManager.setFocused(false);focusManager.setFocused(true)});
 await waitFor(()=>expect(screen.getByLabelText('健康情况')).toHaveValue('医生核对后的答案'));
});
test.each(['submitted','draft'] as const)('未保存时其他终端更新为%s，明确区分服务器记录与本机内容并要求核对',async(status)=>{
 render(<App/>);await userEvent.type(await screen.findByLabelText('健康情况'),'本机未保存的答案');
 answers.set('p1',{id:'answer-p1',revision:1,status,submitted_at:status==='submitted'?'2026-10-16T08:00:00Z':null,answers:{q1:'其他终端保存的答案'}});
 await act(async()=>{focusManager.setFocused(false);focusManager.setFocused(true)});
 expect(await screen.findByText('服务器记录已变化，当前输入仍保留，请核对后重新加载。')).toBeVisible();
 const local=within(screen.getByRole('region',{name:'本机未保存内容'})),remote=within(screen.getByRole('region',{name:'服务器最新记录'}));
 expect(local.getByLabelText('健康情况')).toHaveValue('本机未保存的答案');expect(remote.getByLabelText('健康情况')).toHaveValue('其他终端保存的答案');expect(screen.queryByText('填写已提交')).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'提交答案'})).not.toBeInTheDocument();
 await userEvent.click(screen.getByRole('button',{name:'重新加载'}));await userEvent.click(await screen.findByRole('button',{name:'保留输入'}));expect(local.getByLabelText('健康情况')).toHaveValue('本机未保存的答案');
 await userEvent.click(screen.getByRole('button',{name:'重新加载'}));await userEvent.click(await screen.findByRole('button',{name:'放弃并重新加载'}));
 await waitFor(()=>expect(screen.queryByRole('region',{name:'本机未保存内容'})).not.toBeInTheDocument());expect(screen.getByLabelText('健康情况')).toHaveValue('其他终端保存的答案');if(status==='submitted')expect(await screen.findByText('填写已提交')).toBeVisible();
});
