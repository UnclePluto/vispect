import {act,render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {http,HttpResponse} from 'msw';
import {setupServer} from 'msw/node';
import {App} from '../../app/App';
import {router} from '../../app/router';
let staffCalls=0;
let auth:null|{user:{id:string;phone:string;must_change_password:boolean};next:string;session_token:string}=null;
const server=setupServer(
 http.get('*/api/auth/me/',()=>{staffCalls++;return HttpResponse.json({code:'unauthenticated',message:'未登录',fields:{}},{status:401})}),
 http.get('*/api/patient/csrf/',()=>HttpResponse.json({csrf_token:'csrf'})),
 http.post('*/api/patient/entry/resolve/',()=>HttpResponse.json({available:true})),
 http.get('*/api/patient/auth/me/',()=>auth?HttpResponse.json(auth):HttpResponse.json({code:'patient_session_unavailable',message:'请登录',fields:{}},{status:401})),
 http.post('*/api/patient/auth/login/',()=>{auth={user:{id:'p',phone:'+8613800000001',must_change_password:true},next:'change_password',session_token:'patient-one'};return HttpResponse.json(auth)}),
 http.post('*/api/patient/auth/change-password/',()=>{auth={user:{id:'p',phone:'+8613800000001',must_change_password:false},next:'ready',session_token:'patient-two'};return HttpResponse.json(auth)}),
 http.post('*/api/patient/auth/logout/',()=>{auth=null;return HttpResponse.json({ok:true})}),
 http.post('*/api/patient/tasks/resolve/',()=>HttpResponse.json({count:0,results:[]}))
);
beforeAll(()=>server.listen({onUnhandledRequest:'error'}));beforeEach(async()=>{staffCalls=0;auth=null;await router.navigate('/patient/fill/test-qr-token')});afterEach(()=>server.resetHandlers());afterAll(()=>server.close());
test('患者首次登录改密后留在原扫码目标，且不加载工作人员认证',async()=>{
 render(<App/>);
 await userEvent.type(await screen.findByLabelText('手机号'),'13800000001');await userEvent.type(screen.getByLabelText('密码'),'888888');await userEvent.click(screen.getByRole('button',{name:'登 录'}));
 expect(await screen.findByRole('heading',{name:'修改初始密码'})).toBeVisible();
 await userEvent.type(screen.getByLabelText('原密码'),'888888');await userEvent.type(screen.getByLabelText('新密码'),'Patient-Strong-Password!');await userEvent.type(screen.getByLabelText('确认新密码'),'Patient-Strong-Password!');await userEvent.click(screen.getByRole('button',{name:'修改密码并继续'}));
 await screen.findByText(/已登录/);
 expect(window.location.pathname).toBe('/patient/fill/test-qr-token');expect(staffCalls).toBe(0);
});
test('患者退出后浏览器后退不会恢复旧患者内容',async()=>{
 auth={user:{id:'p',phone:'+8613800000001',must_change_password:false},next:'ready',session_token:'patient-two'};
 render(<App/>);await screen.findByText(/已登录/);await userEvent.click(screen.getByRole('button',{name:'退出登录'}));
 expect(await screen.findByLabelText('手机号')).toBeVisible();
 await act(async()=>{window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))});
 await waitFor(()=>expect(screen.queryByText(/已登录/)).not.toBeInTheDocument());
});

import {patientApi,setPatientSessionToken} from './client';
test('退出失败明确提示且保留当前登录，重试确认撤销后才完成退出',async()=>{
 auth={user:{id:'p',phone:'+8613800000001',must_change_password:false},next:'ready',session_token:'patient-two'};
 let fail=true;
 server.use(http.post('*/api/patient/auth/logout/',()=>{if(fail)return HttpResponse.json({code:'temporary_failure',message:'退出服务暂时失败',fields:{}},{status:503});auth=null;return HttpResponse.json({ok:true})}));
 render(<App/>);await screen.findByText(/已登录/);await userEvent.click(screen.getByRole('button',{name:'退出登录'}));
 expect(await screen.findByText('退出未成功，请重试')).toBeVisible();expect(screen.getByText(/已登录/)).toBeVisible();expect(screen.queryByLabelText('手机号')).not.toBeInTheDocument();
 await act(async()=>{window.dispatchEvent(new Event('focus'));window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))});
 await waitFor(()=>expect(screen.getByText(/已登录/)).toBeVisible());expect(screen.queryByLabelText('手机号')).not.toBeInTheDocument();
 fail=false;await userEvent.click(screen.getByRole('button',{name:'退出登录'}));expect(await screen.findByLabelText('手机号')).toBeVisible();
});
test('患者请求不发送工作人员令牌，也不触发工作人员退出',async()=>{
 auth={user:{id:'p',phone:'+8613800000001',must_change_password:false},next:'ready',session_token:'header-token'};setPatientSessionToken('header-token');
 let staffExpired=0,workspaceHeader:string|null='not-observed',patientHeader:string|null=null;
 const expired=()=>{staffExpired++};window.addEventListener('vispect:session-expired',expired);
 server.use(http.get('*/api/patient/header-check/',({request})=>{workspaceHeader=request.headers.get('X-Workspace-Token');patientHeader=request.headers.get('X-Patient-Session-Token');return HttpResponse.json({code:'unauthenticated',message:'需要重新登录',fields:{}},{status:401})}));
 try{await expect(patientApi('/api/patient/header-check/')).rejects.toMatchObject({status:401});expect(workspaceHeader).toBeNull();expect(patientHeader).toBe('header-token');expect(staffExpired).toBe(0)}finally{window.removeEventListener('vispect:session-expired',expired);setPatientSessionToken(null)}
});
test('新患者会话建立后丢弃旧请求的迟到响应',async()=>{
 let start!:()=>void,finish!:()=>void;
 const started=new Promise<void>(r=>{start=r}),pending=new Promise<void>(r=>{finish=r});
 server.use(http.get('*/api/patient/slow/',async()=>{start();await pending;return HttpResponse.json({patient_name:'旧患者'})}));
 setPatientSessionToken('old-context');const result=patientApi('/api/patient/slow/');await started;setPatientSessionToken('new-context');finish();
 await expect(result).rejects.toMatchObject({code:'patient_request_cancelled'});setPatientSessionToken(null);
});
