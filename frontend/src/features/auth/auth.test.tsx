import {act,render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {http,HttpResponse} from 'msw';
import {setupServer} from 'msw/node';
import {AuthProvider,useAuth} from './AuthProvider';
import {getIdentity} from './api';
import {api} from '../../api/client';

const identity={account_id:'a',tenant_id:'tenant-a',role:'tenant_admin',doctor_id:null,username:'admin',name:'甲机构管理员',must_change_password:false,tenant:{id:'tenant-a',slug:'a',name:'甲机构'}};
const server=setupServer(http.get('*/api/auth/me/',()=>HttpResponse.json(identity)),http.get('*/api/auth/csrf/',()=>HttpResponse.json({csrf_token:'test-csrf'})),http.post('*/api/auth/logout/',()=>HttpResponse.json({success:true})));
beforeAll(()=>server.listen({onUnhandledRequest:'error'}));afterEach(()=>server.resetHandlers());afterAll(()=>server.close());
function Probe(){const auth=useAuth();return <><span>{auth.actor?.name??'未登录'}</span><span>{auth.loading?'正在读取身份':'身份读取完成'}</span><button onClick={()=>auth.logout()}>退出</button><button onClick={()=>auth.login('tenant',{tenant:'b',username:'admin',password:'test'})}>登录乙机构</button><button onClick={()=>api('/api/patients/').catch(()=>{})}>刷新患者</button></>}
test('账号接口支持取消信号',async()=>{expect((await getIdentity(new AbortController().signal)).name).toBe('甲机构管理员')});
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
    server.use(http.get('*/api/auth/me/',async()=>{await gate;return HttpResponse.json(identity)}),http.post('*/api/auth/tenant-login/',()=>HttpResponse.json({...identity,name:'乙机构管理员',tenant_id:'tenant-b',tenant:{id:'tenant-b',slug:'b',name:'乙机构'}})));
    render(<QueryClientProvider client={new QueryClient()}><AuthProvider><Probe/></AuthProvider></QueryClientProvider>);
    await userEvent.click(screen.getByRole('button',{name:'登录乙机构'}));expect(await screen.findByText('乙机构管理员')).toBeInTheDocument();
    expect(screen.getByText('身份读取完成')).toBeInTheDocument();release();await screen.findByText('身份读取完成');await waitFor(()=>expect(screen.getByText('乙机构管理员')).toBeInTheDocument());
});
test('迟到的旧会话401不能清除新登录机构',async()=>{
 let release!:()=>void,started!:()=>void;const gate=new Promise<void>(r=>release=r),ready=new Promise<void>(r=>started=r);
 server.use(http.get('*/api/patients/',async()=>{started();await gate;return HttpResponse.json({code:'session_unavailable',message:'旧会话失效',fields:{}},{status:401})}),http.post('*/api/auth/tenant-login/',()=>HttpResponse.json({...identity,name:'乙机构管理员',tenant_id:'tenant-b'})));
 render(<QueryClientProvider client={new QueryClient()}><AuthProvider><Probe/></AuthProvider></QueryClientProvider>);
 await screen.findByText('甲机构管理员');const stale=api('/api/patients/').catch(()=>{});await ready;await userEvent.click(screen.getByRole('button',{name:'登录乙机构'}));await screen.findByText('乙机构管理员');await act(async()=>{release();await stale});expect(screen.getByText('乙机构管理员')).toBeInTheDocument();
});
test('等待CSRF期间切换账号会取消旧创建请求',async()=>{
 let release!:()=>void,started!:()=>void,calls=0,csrfCalls=0;const gate=new Promise<void>(r=>release=r),ready=new Promise<void>(r=>started=r);
 server.use(http.get('*/api/auth/csrf/',async()=>{csrfCalls++;if(csrfCalls===1){started();await gate}return HttpResponse.json({csrf_token:'csrf'})}),http.post('*/api/doctors/',()=>{calls++;return HttpResponse.json({id:'wrong-tenant'})}),http.post('*/api/auth/tenant-login/',()=>HttpResponse.json({...identity,name:'乙机构管理员',tenant_id:'tenant-b'})));
 render(<QueryClientProvider client={new QueryClient()}><AuthProvider><Probe/></AuthProvider></QueryClientProvider>);await screen.findByText('甲机构管理员');
 const stale=api('/api/doctors/',{method:'POST',body:{name:'旧机构医生'}}).catch(()=>{});await ready;await userEvent.click(screen.getByRole('button',{name:'登录乙机构'}));await screen.findByText('乙机构管理员');await act(async()=>{release();await stale});expect(calls).toBe(0);
});
import {download} from '../../api/client';
test('旧下载请求的401不清除新会话',async()=>{
 let release!:()=>void,started!:()=>void;const gate=new Promise<void>(r=>release=r),ready=new Promise<void>(r=>started=r);
 server.use(http.get('*/api/old-export/',async()=>{started();await gate;return HttpResponse.json({code:'session_unavailable',message:'旧会话',fields:{}},{status:401})}),http.post('*/api/auth/tenant-login/',()=>HttpResponse.json({...identity,name:'乙机构管理员',tenant_id:'tenant-b'})));
 render(<QueryClientProvider client={new QueryClient()}><AuthProvider><Probe/></AuthProvider></QueryClientProvider>);await screen.findByText('甲机构管理员');const stale=download('/api/old-export/','answer.xlsx').catch(()=>{});await ready;await userEvent.click(screen.getByRole('button',{name:'登录乙机构'}));await screen.findByText('乙机构管理员');await act(async()=>{release();await stale});expect(screen.getByText('乙机构管理员')).toBeInTheDocument();
});
