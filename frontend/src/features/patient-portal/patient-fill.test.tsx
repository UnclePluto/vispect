import {render,screen,waitFor} from '@testing-library/react';
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
test('患者提交后后台修订，刷新显示最新只读答案',async()=>{
 render(<App/>);await userEvent.type(await screen.findByLabelText('健康情况'),'患者初次答案');await confirmSubmit();await screen.findByText('填写已提交');
 answers.set('p1',{id:'answer-p1',revision:2,status:'submitted',submitted_at:'2026-10-16T08:00:00Z',answers:{q1:'医生核对后的答案'}});
 await act(async()=>{focusManager.setFocused(false);focusManager.setFocused(true)});
 await waitFor(()=>expect(screen.getByLabelText('健康情况')).toHaveValue('医生核对后的答案'));
});
