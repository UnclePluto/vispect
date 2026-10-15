import {render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {App as AntApp} from 'antd';
import {http,HttpResponse} from 'msw';
import {setupServer} from 'msw/node';
import {GlobalAccountsPage} from './GlobalAccountsPage';
let role='platform_admin',queries=0;
vi.mock('../auth/AuthProvider',()=>({useActor:()=>({role})}));
const server=setupServer(http.get('*/api/platform/accounts/',()=>{queries++;return HttpResponse.json({count:1,results:[{id:'u',phone:'+8613910000001',name:'用户',enabled:true,must_change_password:false,revision:1}]})}));
beforeAll(()=>server.listen({onUnhandledRequest:'error'}));afterEach(()=>{server.resetHandlers();role='platform_admin';queries=0});afterAll(()=>server.close());
function mount(){return render(<QueryClientProvider client={new QueryClient()}><AntApp><GlobalAccountsPage/></AntApp></QueryClientProvider>)}
test('全局账号首次不查询，合法手机号后精确搜索',async()=>{mount();expect(queries).toBe(0);await userEvent.type(screen.getByPlaceholderText('输入完整手机号查询'),'13910000001{Enter}');expect(await screen.findByText('+8613910000001')).toBeInTheDocument();expect(queries).toBe(1)});
test('全局账号管理仅平台可见',async()=>{role='tenant_admin';mount();expect(screen.getByText('此页面仅平台管理员可访问')).toBeInTheDocument();expect(queries).toBe(0)});
