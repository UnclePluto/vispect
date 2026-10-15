import {render,screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {http,HttpResponse} from 'msw';
import {setupServer} from 'msw/node';
import {AuthProvider} from '../auth/AuthProvider';
import {DoctorEditor} from './DoctorEditor';
const server=setupServer(http.get('*/api/auth/me/',()=>HttpResponse.json({user:{id:'u',phone:'13900000001',name:'用户',must_change_password:false},workspaces:[],workspace_token:'token-a',next:'ready',actor:{account_id:'a',tenant_id:'a',role:'tenant_admin',doctor_id:null,username:'admin',name:'管理员',must_change_password:false,tenant:{id:'a',slug:'a',name:'机构'}}})),http.get('*/api/auth/csrf/',()=>HttpResponse.json({csrf_token:'csrf'})),http.patch('*/api/doctors/doctor-1/',()=>HttpResponse.json({code:'revision_conflict',message:'记录已被其他人修改，请刷新后重试',fields:{}},{status:409})));
beforeAll(()=>server.listen({onUnhandledRequest:'error'}));afterEach(()=>server.resetHandlers());afterAll(()=>server.close());
test('保存冲突后保留医生未保存资料',async()=>{
    render(<QueryClientProvider client={new QueryClient()}><AuthProvider><DoctorEditor open doctor={{id:'doctor-1',revision:3,name:'原姓名',login_phone:'+8613900000001',phone:'',organization:'',department:'',title:'',enabled:true,created_at:'2026-10-13',deleted_at:null}} onCancel={()=>{}} onSaved={()=>{}}/></AuthProvider></QueryClientProvider>);
    const input=await screen.findByLabelText('姓名');await userEvent.clear(input);await userEvent.type(input,'编辑后姓名');await userEvent.click(screen.getByRole('button',{name:'保 存'}));
    expect(await screen.findByText('记录已被其他人修改，请刷新后重试')).toBeInTheDocument();expect(input).toHaveValue('编辑后姓名');
});
test('已注册手机号隐藏初始密码且清除旧输入',async()=>{
 server.use(http.post('*/api/members/phone-status/',async({request})=>{const {phone}=await request.json() as {phone:string};return HttpResponse.json({phone,registered:phone.endsWith('2')})}));
 render(<QueryClientProvider client={new QueryClient()}><AuthProvider><DoctorEditor open onCancel={()=>{}} onSaved={()=>{}}/></AuthProvider></QueryClientProvider>);
 const input=await screen.findByLabelText('登录手机号');await userEvent.type(input,'13910000001');await userEvent.type(await screen.findByLabelText('初始密码'),'Old-Strong-2026!');await userEvent.clear(input);await userEvent.type(input,'13910000002');expect(await screen.findByText('该手机号已注册，加入机构后保留原密码。')).toBeInTheDocument();expect(screen.queryByLabelText('初始密码')).not.toBeInTheDocument();
});
test('迟到手机号探测不能覆盖当前输入',async()=>{
 let release!:()=>void;const gate=new Promise<void>(r=>release=r);
 server.use(http.post('*/api/members/phone-status/',async({request})=>{const {phone}=await request.json() as {phone:string};if(phone.endsWith('1'))await gate;return HttpResponse.json({phone,registered:phone.endsWith('1')})}));
 render(<QueryClientProvider client={new QueryClient()}><AuthProvider><DoctorEditor open onCancel={()=>{}} onSaved={()=>{}}/></AuthProvider></QueryClientProvider>);
 const input=await screen.findByLabelText('登录手机号');await userEvent.type(input,'13910000001');await userEvent.clear(input);await userEvent.type(input,'13910000002');await screen.findByLabelText('初始密码');release();expect(screen.getByLabelText('登录手机号')).toHaveValue('13910000002');expect(screen.queryByText('该手机号已注册，加入机构后保留原密码。')).not.toBeInTheDocument();
});
