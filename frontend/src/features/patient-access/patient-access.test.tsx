import {render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {App} from 'antd';
import {http,HttpResponse} from 'msw';
import {setupServer} from 'msw/node';
import {AuthProvider} from '../auth/AuthProvider';
import {PatientEditor} from '../patients/PatientEditor';
let saved:Record<string,unknown>|undefined;
const server=setupServer(
 http.get('*/api/auth/me/',()=>HttpResponse.json({user:{id:'u',phone:'+8613900000001',name:'医生',must_change_password:false},actor:{account_id:'a',role:'doctor',doctor_id:'d',must_change_password:false},workspaces:[],workspace_token:'patient-access-test',next:'ready'})),
 http.get('*/api/auth/csrf/',()=>HttpResponse.json({csrf_token:'csrf'})),
 http.post('*/api/patients/',async({request})=>{saved=await request.json() as Record<string,unknown>;return HttpResponse.json({id:'patient',...saved})})
);
beforeAll(()=>server.listen({onUnhandledRequest:'error'}));afterEach(()=>{server.resetHandlers();saved=undefined});afterAll(()=>server.close());
test('创建患者可开通默认密码账号，界面无需填写密码',async()=>{
 render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><App><AuthProvider><PatientEditor open onCancel={()=>{}} onSaved={()=>{}}/></AuthProvider></App></QueryClientProvider>);
 await userEvent.type(await screen.findByLabelText('档案编号'),'000031');await userEvent.type(screen.getByLabelText('姓名'),'测试患者');
 await userEvent.click(screen.getByRole('checkbox',{name:'开通患者填写账号'}));
 await userEvent.type(screen.getByLabelText('登录手机号'),'13800000001');
 expect(screen.queryByLabelText('初始密码')).not.toBeInTheDocument();
 await userEvent.click(screen.getByRole('button',{name:'保 存'}));
 await waitFor(()=>expect(saved?.enable_patient_portal).toBe(true));
 expect(saved?.login_phone).toBe('13800000001');
});

import {MemoryRouter} from 'react-router-dom';
import {FormsPage} from '../forms/FormsPage';
test('从表单选择研究访视后生成固定版本的共用二维码',async()=>{
 const entry={id:'entry-1',binding_id:'binding-1',token:'shared-entry-token',enabled:true,revision:1,url_path:'/patient/fill/shared-entry-token',created_at:'2026-10-16'};
 server.use(
  http.get('*/api/forms/',()=>HttpResponse.json({count:1,results:[{id:'form-1',title:'患者问卷',paused:false,editable:false,revision:1,latest_version:{id:'v1',number:1}}]})),
  http.get('*/api/forms/form-1/patient-entry-options/',()=>HttpResponse.json({count:1,results:[{binding_id:'binding-1',study_id:'study-1',study_name:'研究甲',stage_name:'基线期',form_title:'患者问卷',version_number:1,entry:null,create_block_reason:null}]})),
  http.get('*/api/patient-form-bindings/binding-1/entry/',()=>HttpResponse.json({entry:null})),
  http.post('*/api/patient-form-bindings/binding-1/entry/',()=>HttpResponse.json(entry))
 );
 render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><App><AuthProvider><MemoryRouter><FormsPage/></MemoryRouter></AuthProvider></App></QueryClientProvider>);
 await userEvent.click(await screen.findByRole('button',{name:'填写链接'}));
 await waitFor(()=>expect(screen.getByText(/研究甲.*基线期.*v1/)).toBeVisible());
 await userEvent.click(screen.getByRole('button',{name:'生成填写链接'}));
 expect(await screen.findByDisplayValue(/\/patient\/fill\/shared-entry-token/)).toBeVisible();
 expect(screen.getByRole('button',{name:'下载二维码'})).toBeEnabled();
});

import {PatientEntryDialog} from './PatientEntryDialog';
import {useAuth} from '../auth/AuthProvider';
import {useState} from 'react';
test('重新生成使用已有入口修订号并显示新链接',async()=>{
 const old={id:'old-entry',binding_id:'b',token:'old-token',enabled:true,revision:3,url_path:'/patient/fill/old-token',created_at:'2026-10-16'};
 let revision:number|undefined;
 server.use(http.get('*/api/patient-form-bindings/b/entry/',()=>HttpResponse.json({entry:old})),http.post('*/api/patient-form-entries/old-entry/regenerate/',async({request})=>{revision=(await request.json() as {expected_revision:number}).expected_revision;return HttpResponse.json({...old,id:'new-entry',token:'new-token',revision:1,url_path:'/patient/fill/new-token'})}));
 render(<QueryClientProvider client={new QueryClient()}><App><AuthProvider><PatientEntryDialog bindingId="b" open onClose={()=>{}}/></AuthProvider></App></QueryClientProvider>);
 await screen.findByDisplayValue(/old-token/);await userEvent.click(screen.getByRole('button',{name:'重新生成'}));await userEvent.click(await screen.findByRole('button',{name:'确认重新生成'}));
 expect(await screen.findByDisplayValue(/new-token/)).toBeVisible();expect(revision).toBe(3);
});
test('切换机构关闭已有二维码弹窗',async()=>{
 const envelope=(id:string,token:string)=>({user:{id:'u',phone:'+8613900000001',name:'医生',must_change_password:false},actor:{account_id:id,role:'doctor',doctor_id:'d',must_change_password:false},workspaces:[],workspace_token:token,next:'ready'});
 let active=envelope('a','switch-a');
 server.use(http.get('*/api/auth/me/',()=>HttpResponse.json(active)),http.post('*/api/auth/switch-workspace/',()=>{active=envelope('b','switch-b');return HttpResponse.json(active)}),http.get('*/api/patient-form-bindings/b/entry/',()=>HttpResponse.json({entry:{id:'entry',binding_id:'b',token:'sensitive-old-entry',enabled:true,revision:1,url_path:'/patient/fill/sensitive-old-entry',created_at:'2026-10-16'}})));
 function Harness(){const auth=useAuth(),[open,setOpen]=useState(true);return <><button onClick={()=>void auth.switchWorkspace('b')}>切换测试机构</button>{auth.actor&&<PatientEntryDialog bindingId="b" open={open} onClose={()=>setOpen(false)}/>}</>}
 render(<QueryClientProvider client={new QueryClient()}><App><AuthProvider><Harness/></AuthProvider></App></QueryClientProvider>);
 await screen.findByDisplayValue(/sensitive-old-entry/);await userEvent.click(screen.getByRole('button',{name:'切换测试机构'}));
 await waitFor(()=>expect(screen.queryByDisplayValue(/sensitive-old-entry/)).not.toBeInTheDocument());
});
