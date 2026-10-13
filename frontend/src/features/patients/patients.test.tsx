import {render,screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {http,HttpResponse} from 'msw';
import {setupServer} from 'msw/node';
import {AuthProvider} from '../auth/AuthProvider';
import {PatientEditor} from './PatientEditor';
const server=setupServer(http.get('*/api/auth/me/',()=>HttpResponse.json({role:'doctor',doctor_id:'d',must_change_password:false})),http.get('*/api/auth/csrf/',()=>HttpResponse.json({csrf_token:'csrf'})),http.post('*/api/patients/',async({request})=>{const data=await request.json() as {code:string};expect(data.code).toBe('000001');return HttpResponse.json({code:'quota_exceeded',message:'患者额度已满',fields:{}},{status:409})}));
beforeAll(()=>server.listen({onUnhandledRequest:'error'}));afterAll(()=>server.close());
test('档案编号保留前导零，保存失败保留输入',async()=>{
 render(<QueryClientProvider client={new QueryClient()}><AuthProvider><PatientEditor open onCancel={()=>{}} onSaved={()=>{}}/></AuthProvider></QueryClientProvider>);
 await userEvent.type(await screen.findByLabelText('档案编号'),'000001');await userEvent.type(screen.getByLabelText('姓名'),'测试患者');await userEvent.click(screen.getByRole('button',{name:'保 存'}));
 expect(await screen.findByText('患者额度已满')).toBeInTheDocument();expect(screen.getByLabelText('档案编号')).toHaveValue('000001');
});
