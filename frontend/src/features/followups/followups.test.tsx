import {render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {App} from 'antd';
import {MemoryRouter,Routes,Route} from 'react-router-dom';
import {http,HttpResponse} from 'msw';
import {setupServer} from 'msw/node';
import {AnswerEntry} from './AnswerEntry';
import {VisitDetail} from './VisitDetail';
import type {FormDefinition} from '../../form-engine/types';
const definition:FormDefinition={protocol_version:1,title:'随访表单',questions:[{id:'q1',title:'健康情况',type:'text',required:true}]};
const binding={id:'b',form_version_id:'f',definition,form_paused:false,respondent:'patient' as const,required:true};
let requests=0,revoked=false;
const server=setupServer(http.get('*/api/auth/csrf/',()=>HttpResponse.json({csrf_token:'csrf'})),http.post('*/api/visits/v/answers/',()=>{requests++;return HttpResponse.json({code:'revision_conflict',message:'答案已被修改，请刷新后重试',fields:{}},{status:409})}),http.get('*/api/visits/v/',()=>revoked?HttpResponse.json({code:'object_unavailable',message:'对象不存在或当前不可访问',fields:{}},{status:404}):HttpResponse.json({id:'v',enrollment_id:'e',study_id:'s',study_name:'研究',patient_name:'模拟患者',stage_name:'基线期',status:'pending',is_current:true,writable:true,bindings:[binding],planned_on:'2026-10-13',window_start:'2026-10-13',window_end:'2026-10-16'})),http.get('*/api/visits/v/answers/',()=>HttpResponse.json({results:[]})));
beforeAll(()=>server.listen({onUnhandledRequest:'error'}));afterEach(()=>{requests=0;revoked=false;server.resetHandlers()});afterAll(()=>server.close());
function wrapper(children:React.ReactNode){return <QueryClientProvider client={new QueryClient()}><App>{children}</App></QueryClientProvider>}
test('患者表单明确代录，必填不足不发请求，冲突保留输入',async()=>{
 render(wrapper(<AnswerEntry visitId="v" binding={binding} writable answer={undefined} onSaved={()=>{}} onUnavailable={()=>{}}/>));
 expect(screen.getByText(/工作人员代录/)).toBeInTheDocument();await userEvent.click(screen.getByRole('button',{name:'提交答案'}));expect(requests).toBe(0);expect(screen.getByText('请填写此题')).toBeInTheDocument();await userEvent.type(screen.getByLabelText('健康情况'),'未保存的答案');await userEvent.click(screen.getByRole('button',{name:'保存草稿'}));expect(await screen.findByText('答案已被修改，请刷新后重试')).toBeInTheDocument();expect(screen.getByLabelText('健康情况')).toHaveValue('未保存的答案');
});
test('医生填写对象与暂停表单只读',()=>{render(wrapper(<AnswerEntry visitId="v" binding={{...binding,respondent:'doctor',form_paused:true}} writable answer={undefined} onSaved={()=>{}} onUnavailable={()=>{}}/>));expect(screen.getByText(/医生填写/)).toBeInTheDocument();expect(screen.getByLabelText('健康情况')).toBeDisabled();expect(screen.queryByRole('button',{name:'提交答案'})).not.toBeInTheDocument()});
test('缺少必需提交时不能完成访视，撤权后清理缓存',async()=>{
 const cache=new QueryClient({defaultOptions:{queries:{retry:false}}});render(<QueryClientProvider client={cache}><App><MemoryRouter initialEntries={['/visits/v']}><Routes><Route path="/visits/:id" element={<VisitDetail/>}/></Routes></MemoryRouter></App></QueryClientProvider>);
 expect(await screen.findByRole('button',{name:'完成当前访视'})).toBeDisabled();revoked=true;await cache.invalidateQueries({queryKey:['visit','v']});expect(await screen.findByText('对象不存在或当前不可访问')).toBeInTheDocument();expect(screen.queryByText('模拟患者')).not.toBeInTheDocument();expect(cache.getQueryData(['visit-answers','v'])).toBeUndefined();
});
test('只读答案刷新后展示最新版本',()=>{
 const old={id:'a',revision:1,visit_id:'v',binding_id:'b',form_version_id:'f',respondent:'patient' as const,is_proxy:true,recorded_by_id:'doctor',recorded_by_name:'医生',answers:{q1:'旧答案'},status:'submitted' as const,submitted_at:'2026-10-13',updated_at:'2026-10-13'};
 const {rerender}=render(wrapper(<AnswerEntry visitId="v" binding={binding} writable={false} answer={old} onSaved={()=>{}} onUnavailable={()=>{}}/>));
 rerender(wrapper(<AnswerEntry visitId="v" binding={binding} writable={false} answer={{...old,revision:2,answers:{q1:'新答案'}}} onSaved={()=>{}} onUnavailable={()=>{}}/>));
 expect(screen.getByLabelText('健康情况')).toHaveValue('新答案');
});
import {AuthProvider} from '../auth/AuthProvider';
import {EnrollmentDialog} from './EnrollmentDialog';
import {shanghaiToday,type Enrollment} from './api';
import type {Study} from '../studies/api';
test('筛选完成后单独确认入组，编号保留前导零',async()=>{
 const saved=vi.fn();server.use(http.get('*/api/auth/me/',()=>HttpResponse.json({user:{id:'u',phone:'+8613900000001',name:'测试',must_change_password:false},actor:{account_id:'a',role:'doctor',doctor_id:'d',must_change_password:false},workspaces:[],workspace_token:'token-a',next:'ready'})),http.post('*/api/enrollments/e/confirm/',async({request})=>{const body=await request.json() as {enrollment_code:string;enrolled_on:string};expect(body.enrollment_code).toBe('000001');expect(body.enrolled_on).toBe(shanghaiToday());return HttpResponse.json({id:'e',state:'following'})}));
 render(wrapper(<AuthProvider><EnrollmentDialog open study={{id:'s'} as Study} subject={{id:'e',state:'awaiting_enrollment'} as Enrollment} onCancel={()=>{}} onSaved={saved}/></AuthProvider>));
 await screen.findByLabelText('入组编号');await waitFor(()=>expect(screen.getByLabelText('入组日期')).toHaveValue(shanghaiToday()));await userEvent.type(screen.getByLabelText('入组编号'),'000001');await userEvent.click(screen.getByRole('button',{name:'确认入组'}));await waitFor(()=>expect(saved).toHaveBeenCalledOnce());
});

test('从关闭状态打开确认入组时填入上海当前日期',async()=>{
 const subject={id:'e',state:'awaiting_enrollment'} as Enrollment;
 const content=(open:boolean)=>wrapper(<AuthProvider><EnrollmentDialog open={open} study={{id:'s'} as Study} subject={subject} onCancel={()=>{}} onSaved={()=>{}}/></AuthProvider>);
 server.use(http.get('*/api/auth/me/',()=>HttpResponse.json({user:{id:'u',phone:'+8613900000001',name:'测试',must_change_password:false},actor:{account_id:'a',role:'doctor',doctor_id:'d',must_change_password:false},workspaces:[],workspace_token:'token-a',next:'ready'})));
 const {rerender}=render(content(false));rerender(content(true));
 await waitFor(()=>expect(screen.getByLabelText('入组日期')).toHaveValue(shanghaiToday()));
});
