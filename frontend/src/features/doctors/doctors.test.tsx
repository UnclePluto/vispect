import {render,screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {http,HttpResponse} from 'msw';
import {setupServer} from 'msw/node';
import {AuthProvider} from '../auth/AuthProvider';
import {DoctorEditor} from './DoctorEditor';
const server=setupServer(http.get('*/api/auth/me/',()=>HttpResponse.json({account_id:'a',tenant_id:'a',role:'tenant_admin',doctor_id:null,username:'admin',name:'管理员',must_change_password:false,tenant:{id:'a',slug:'a',name:'机构'}})),http.get('*/api/auth/csrf/',()=>HttpResponse.json({csrf_token:'csrf'})),http.patch('*/api/doctors/doctor-1/',()=>HttpResponse.json({code:'revision_conflict',message:'记录已被其他人修改，请刷新后重试',fields:{}},{status:409})));
beforeAll(()=>server.listen({onUnhandledRequest:'error'}));afterAll(()=>server.close());
test('保存冲突后保留医生未保存资料',async()=>{
    render(<QueryClientProvider client={new QueryClient()}><AuthProvider><DoctorEditor open doctor={{id:'doctor-1',revision:3,name:'原姓名',username:'doctor',phone:'',organization:'',department:'',title:'',enabled:true,created_at:'2026-10-13',deleted_at:null}} onCancel={()=>{}} onSaved={()=>{}}/></AuthProvider></QueryClientProvider>);
    const input=await screen.findByLabelText('姓名');await userEvent.clear(input);await userEvent.type(input,'编辑后姓名');await userEvent.click(screen.getByRole('button',{name:'保 存'}));
    expect(await screen.findByText('记录已被其他人修改，请刷新后重试')).toBeInTheDocument();expect(input).toHaveValue('编辑后姓名');
});
