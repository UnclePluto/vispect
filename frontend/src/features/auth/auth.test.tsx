import {act,render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {http,HttpResponse} from 'msw';
import {setupServer} from 'msw/node';
import {AuthProvider,useAuth} from './AuthProvider';
import {getIdentity} from './api';
import {api} from '../../api/client';

const identity={account_id:'a',tenant_id:'tenant-a',role:'tenant_admin',doctor_id:null,username:'admin',name:'甲机构管理员',must_change_password:false,tenant:{id:'tenant-a',slug:'a',name:'甲机构'}};
function envelope(actor=identity){return {user:{id:'user',phone:'+8613900002001',name:actor.name,must_change_password:false},actor,workspaces:[{account_id:actor.account_id,tenant:actor.tenant,role:actor.role,name:actor.name}],workspace_token:actor.tenant_id,next:'ready'}}
const server=setupServer(http.get('*/api/auth/me/',()=>HttpResponse.json(envelope())),http.get('*/api/auth/csrf/',()=>HttpResponse.json({csrf_token:'test-csrf'})),http.post('*/api/auth/logout/',()=>HttpResponse.json({success:true})));
beforeAll(()=>server.listen({onUnhandledRequest:'error'}));afterEach(()=>server.resetHandlers());afterAll(()=>server.close());
function Probe(){const auth=useAuth();return <><span>{auth.actor?.name??'未登录'}</span><span>{auth.loading?'正在读取身份':'身份读取完成'}</span><button onClick={()=>auth.logout()}>退出</button><button onClick={()=>auth.login({phone:'13900002003',password:'test'})}>登录乙机构</button><button onClick={()=>api('/api/patients/').catch(()=>{})}>刷新患者</button></>}
test('账号接口支持取消信号',async()=>{expect((await getIdentity(new AbortController().signal)).actor?.name).toBe('甲机构管理员')});
test('test_logout_clears_private_cache',async()=>{
    const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
    client.setQueryData(['patients'],[{name:'旧账号患者'}]);
    render(<QueryClientProvider client={client}><AuthProvider><Probe/></AuthProvider></QueryClientProvider>);
    expect(await screen.findByText('甲机构管理员')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button',{name:'退出'}));
    await waitFor(()=>expect(screen.getByText('未登录')).toBeInTheDocument());
    expect(client.getQueryCache().getAll()).toHaveLength(0);
});
test('会话失效后移除身份与私人查询缓存',async()=>{
    server.use(http.get('*/api/patients/',()=>HttpResponse.json({code:'session_unavailable',message:'会话已失效',fields:{}},{status:401})));
    const client=new QueryClient();client.setQueryData(['patients'],[{name:'原有患者'}]);
    render(<QueryClientProvider client={client}><AuthProvider><Probe/></AuthProvider></QueryClientProvider>);
    expect(await screen.findByText('甲机构管理员')).toBeInTheDocument();await userEvent.click(screen.getByRole('button',{name:'刷新患者'}));
    await waitFor(()=>expect(screen.getByText('未登录')).toBeInTheDocument());expect(client.getQueryCache().getAll()).toHaveLength(0);
});
test('初始身份迟到不能覆盖新登录机构',async()=>{
    let release!:()=>void;const gate=new Promise<void>(resolve=>{release=resolve});
    server.use(http.get('*/api/auth/me/',async()=>{await gate;return HttpResponse.json(envelope())}),http.post('*/api/auth/login/',()=>HttpResponse.json(envelope({...identity,name:'乙机构管理员',tenant_id:'tenant-b',tenant:{id:'tenant-b',slug:'b',name:'乙机构'}}))));
    render(<QueryClientProvider client={new QueryClient()}><AuthProvider><Probe/></AuthProvider></QueryClientProvider>);
    await userEvent.click(screen.getByRole('button',{name:'登录乙机构'}));expect(await screen.findByText('乙机构管理员')).toBeInTheDocument();
    expect(screen.getByText('身份读取完成')).toBeInTheDocument();release();await screen.findByText('身份读取完成');await waitFor(()=>expect(screen.getByText('乙机构管理员')).toBeInTheDocument());
});
test('迟到的旧会话401不能清除新登录机构',async()=>{
 let release!:()=>void,started!:()=>void;const gate=new Promise<void>(r=>release=r),ready=new Promise<void>(r=>started=r);
 server.use(http.get('*/api/patients/',async()=>{started();await gate;return HttpResponse.json({code:'session_unavailable',message:'旧会话失效',fields:{}},{status:401})}),http.post('*/api/auth/login/',()=>HttpResponse.json(envelope({...identity,name:'乙机构管理员',tenant_id:'tenant-b'}))));
 render(<QueryClientProvider client={new QueryClient()}><AuthProvider><Probe/></AuthProvider></QueryClientProvider>);
 await screen.findByText('甲机构管理员');const stale=api('/api/patients/').catch(()=>{});await ready;await userEvent.click(screen.getByRole('button',{name:'登录乙机构'}));await screen.findByText('乙机构管理员');await act(async()=>{release();await stale});expect(screen.getByText('乙机构管理员')).toBeInTheDocument();
});
test('等待CSRF期间切换账号会取消旧创建请求',async()=>{
 let release!:()=>void,started!:()=>void,calls=0,csrfCalls=0;const gate=new Promise<void>(r=>release=r),ready=new Promise<void>(r=>started=r);
 server.use(http.get('*/api/auth/csrf/',async()=>{csrfCalls++;if(csrfCalls===1){started();await gate}return HttpResponse.json({csrf_token:'csrf'})}),http.post('*/api/doctors/',()=>{calls++;return HttpResponse.json({id:'wrong-tenant'})}),http.post('*/api/auth/login/',()=>HttpResponse.json(envelope({...identity,name:'乙机构管理员',tenant_id:'tenant-b'}))));
 render(<QueryClientProvider client={new QueryClient()}><AuthProvider><Probe/></AuthProvider></QueryClientProvider>);await screen.findByText('甲机构管理员');
 const stale=api('/api/doctors/',{method:'POST',body:{name:'旧机构医生'}}).catch(()=>{});await ready;await userEvent.click(screen.getByRole('button',{name:'登录乙机构'}));await screen.findByText('乙机构管理员');await act(async()=>{release();await stale});expect(calls).toBe(0);
});
import {download} from '../../api/client';
test('旧下载请求的401不清除新会话',async()=>{
 let release!:()=>void,started!:()=>void;const gate=new Promise<void>(r=>release=r),ready=new Promise<void>(r=>started=r);
 server.use(http.get('*/api/old-export/',async()=>{started();await gate;return HttpResponse.json({code:'session_unavailable',message:'旧会话',fields:{}},{status:401})}),http.post('*/api/auth/login/',()=>HttpResponse.json(envelope({...identity,name:'乙机构管理员',tenant_id:'tenant-b'}))));
 render(<QueryClientProvider client={new QueryClient()}><AuthProvider><Probe/></AuthProvider></QueryClientProvider>);await screen.findByText('甲机构管理员');const stale=download('/api/old-export/','answer.xlsx').catch(()=>{});await ready;await userEvent.click(screen.getByRole('button',{name:'登录乙机构'}));await screen.findByText('乙机构管理员');await act(async()=>{release();await stale});expect(screen.getByText('乙机构管理员')).toBeInTheDocument();
});

import {WorkspaceSwitcher} from './WorkspaceSwitcher';
import {LoginPage} from './LoginPage';
import {MemoryRouter} from 'react-router-dom';
import {App as AntApp} from 'antd';
function readyRender(child:React.ReactNode){return render(<QueryClientProvider client={new QueryClient()}><AntApp><MemoryRouter><AuthProvider>{child}</AuthProvider></MemoryRouter></AntApp></QueryClientProvider>)}
test('手机号登录没有机构标识和用户名',async()=>{
 server.use(http.get('*/api/auth/me/',()=>HttpResponse.json({code:'unauthenticated',message:'登录',fields:{}},{status:401})));
 readyRender(<LoginPage/>);expect(screen.getByLabelText('手机号')).toBeInTheDocument();expect(screen.queryByLabelText('租户标识')).not.toBeInTheDocument();expect(screen.queryByLabelText('用户名')).not.toBeInTheDocument();
});
test('选择机构更新独立角色且携带空间令牌',async()=>{
 const second={...identity,account_id:'b',role:'doctor',name:'乙机构医生',tenant_id:'tenant-b',tenant:{id:'tenant-b',slug:'b',name:'乙机构'}};
 const workspaces=[...envelope().workspaces,{account_id:'b',tenant:second.tenant,role:'doctor',name:second.name}];
 server.use(http.get('*/api/auth/me/',()=>HttpResponse.json({...envelope(),workspaces})),http.post('*/api/auth/switch-workspace/',async({request})=>{expect(await request.json()).toEqual({account_id:'b',workspace_token:'tenant-a'});return HttpResponse.json({...envelope(second),workspace_token:'token-b',workspaces})}));
 readyRender(<><Probe/><WorkspaceSwitcher/></>);await screen.findByText('甲机构管理员');await userEvent.click(screen.getByRole('combobox',{name:'当前机构'}));await userEvent.click(await screen.findByText(/乙机构.*医生.*b/));expect(await screen.findByText('乙机构医生')).toBeInTheDocument();
});
test('空间撤销保留统一身份',async()=>{
 let restored=false;server.use(http.get('*/api/auth/me/',()=>HttpResponse.json(restored?{...envelope(),actor:null,next:'choose_workspace'}:envelope())),http.get('*/api/patients/',()=>{restored=true;return HttpResponse.json({code:'workspace_unavailable',message:'机构已停用',fields:{}},{status:409})}));
 function State(){const a=useAuth();return <span>{a.user?.phone}:{a.next}</span>}
 readyRender(<><Probe/><State/></>);await screen.findByText('甲机构管理员');await userEvent.click(screen.getByText('刷新患者'));expect(await screen.findByText('+8613900002001:choose_workspace')).toBeInTheDocument();
});
import {Routes,Route} from 'react-router-dom';
test.each([['change_password','修改初始密码'],['choose_workspace','请选择机构']])('手机号登录按 %s 导航',async(next,destination)=>{
 server.use(http.get('*/api/auth/me/',()=>HttpResponse.json({code:'unauthenticated',message:'登录',fields:{}},{status:401})),http.post('*/api/auth/login/',async({request})=>{expect(await request.json()).toEqual({phone:'13900002001',password:'Password-2026!'});return HttpResponse.json({...envelope(),next})}));
 readyRender(<Routes><Route path="/" element={<LoginPage/>}/><Route path="/change-password" element={<span>修改初始密码</span>}/><Route path="/select-workspace" element={<span>请选择机构</span>}/></Routes>);
 await userEvent.type(screen.getByLabelText('手机号'),'13900002001');await userEvent.type(screen.getByLabelText('密码'),'Password-2026!');
 await userEvent.click(screen.getByRole('button',{name:/登\s*录/}));expect(await screen.findByText(destination)).toBeInTheDocument();
});
test('无广播时迟到的成功查询核验权威空间后丢弃',async()=>{
 let release!:()=>void,started!:()=>void,changed=false;const gate=new Promise<void>(r=>release=r),ready=new Promise<void>(r=>started=r);
 server.use(http.get('*/api/auth/me/',()=>HttpResponse.json(changed?{...envelope({...identity,name:'乙机构医生',tenant_id:'tenant-b'}),workspace_token:'token-b'}:envelope())),http.get('*/api/delayed-patients/',async()=>{started();await gate;return HttpResponse.json({name:'旧机构患者'})}));
 readyRender(<Probe/>);await screen.findByText('甲机构管理员');const pending=api('/api/delayed-patients/').then(()=>null,e=>e);await ready;let error:unknown;await act(async()=>{changed=true;release();error=await pending});expect((error as {code?:string})?.code).toBe('request_cancelled');expect(await screen.findByText('乙机构医生')).toBeInTheDocument();
});
test('无广播时迟到的成功下载不得落盘',async()=>{
 let release!:()=>void,started!:()=>void,changed=false;const gate=new Promise<void>(r=>release=r),ready=new Promise<void>(r=>started=r);
 server.use(http.get('*/api/auth/me/',()=>HttpResponse.json(changed?{...envelope({...identity,name:'乙机构医生',tenant_id:'tenant-b'}),workspace_token:'token-b'}:envelope())),http.get('*/api/delayed-export/',async()=>{started();await gate;return new HttpResponse('old spreadsheet',{headers:{'Content-Type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}})}));
 const original=URL.createObjectURL;URL.createObjectURL=vi.fn(()=> 'blob:test');const click=vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{});
 try{readyRender(<Probe/>);await screen.findByText('甲机构管理员');const pending=download('/api/delayed-export/','old.xlsx').then(()=>null,e=>e);await ready;let error:unknown;await act(async()=>{changed=true;release();error=await pending});expect((error as {code?:string})?.code).toBe('request_cancelled');expect(click).not.toHaveBeenCalled();await screen.findByText('乙机构医生');}finally{URL.createObjectURL=original;click.mockRestore()}
});
test('切换进行中阻止新的业务写入，失败后恢复操作',async()=>{
 let release!:()=>void,started!:()=>void,writes=0;const gate=new Promise<void>(r=>release=r),ready=new Promise<void>(r=>started=r);
 server.use(http.post('*/api/auth/switch-workspace/',async()=>{started();await gate;return HttpResponse.json({code:'object_unavailable',message:'机构不可用',fields:{}},{status:404})}),http.post('*/api/new-write/',()=>{writes++;return HttpResponse.json({saved:true})}));
 function Switch(){const auth=useAuth();return <><Probe/><span>{auth.switching?'正在切换':'可操作'}</span><button onClick={()=>void auth.switchWorkspace('b').catch(()=>{})}>发起切换</button></>}
 readyRender(<Switch/>);await screen.findByText('甲机构管理员');await userEvent.click(screen.getByText('发起切换'));await ready;
 try{const error=await api('/api/new-write/',{method:'POST',body:{}}).then(()=>null,e=>e);expect(error?.code).toBe('request_cancelled');expect(writes).toBe(0)}finally{release()}
 await screen.findByText('可操作');expect(await api('/api/new-write/',{method:'POST',body:{}})).toEqual({saved:true});expect(writes).toBe(1);
});
