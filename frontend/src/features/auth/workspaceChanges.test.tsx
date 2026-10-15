import {act,render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {useState} from 'react';
import {App as AntApp} from 'antd';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {http,HttpResponse} from 'msw';
import {setupServer} from 'msw/node';
import {AuthProvider,useAuth} from './AuthProvider';
import {WorkspaceChangesProvider,useWorkspaceDirty,useWorkspaceChanges} from './WorkspaceChangesProvider';
import {DynamicForm} from '../../form-engine/DynamicForm';
let calls=0;
const actor={account_id:'a',tenant_id:'a',role:'tenant_admin',doctor_id:null,username:'admin',name:'甲管理员',must_change_password:false,tenant:{id:'a',slug:'a',name:'甲机构'}};
const envelope={user:{id:'u',phone:'+8613900000001',name:'用户',must_change_password:false},actor,workspaces:[],workspace_token:'token-a',next:'ready'};
const server=setupServer(http.get('*/api/auth/me/',()=>HttpResponse.json(envelope)),http.get('*/api/auth/csrf/',()=>HttpResponse.json({csrf_token:'csrf'})),http.post('*/api/auth/switch-workspace/',()=>{calls++;return HttpResponse.json({...envelope,workspace_token:'token-b',actor:{...actor,name:'乙医生'}})}));
beforeAll(()=>server.listen({onUnhandledRequest:'error'}));afterEach(()=>{server.resetHandlers();calls=0});afterAll(()=>server.close());
function Editor(){const [text,setText]=useState('');useWorkspaceDirty('editor',!!text);return <input aria-label="草稿" value={text} onChange={e=>setText(e.target.value)}/>}
function Probe(){const auth=useAuth();return <><span>{auth.actor?.name}</span><Editor key={auth.workspaceToken}/><button onClick={()=>void auth.switchWorkspace('b')}>切换机构</button></>}
function wrap(children:React.ReactNode){return <QueryClientProvider client={new QueryClient()}><AntApp><WorkspaceChangesProvider><AuthProvider>{children}</AuthProvider></WorkspaceChangesProvider></AntApp></QueryClientProvider>}
test('未保存时取消切换保留输入，确认后只调用一次并清理',async()=>{
 render(wrap(<Probe/>));await screen.findByText('甲管理员');await userEvent.type(screen.getByLabelText('草稿'),'未保存内容');await userEvent.click(screen.getByText('切换机构'));
 expect(await screen.findByRole('dialog',{name:'有未保存的修改，是否切换机构？'})).toBeInTheDocument();await userEvent.click(screen.getByRole('button',{name:/取\s*消/}));await waitFor(()=>expect(screen.queryByRole('dialog')).not.toBeInTheDocument());expect(calls).toBe(0);expect(screen.getByLabelText('草稿')).toHaveValue('未保存内容');
 await userEvent.click(screen.getByText('切换机构'));await userEvent.click(await screen.findByRole('button',{name:'放弃修改并切换'}));expect(await screen.findByText('乙医生')).toBeInTheDocument();expect(calls).toBe(1);expect(screen.getByLabelText('草稿')).toHaveValue('');
});
test('答案保存成功清除登记，保存失败保留登记',async()=>{
 let fail=true;function Answer(){const [dirty,setDirty]=useState(false);const changes=useWorkspaceChanges();useWorkspaceDirty('answer',dirty);return <><DynamicForm definition={{protocol_version:1,title:'表单',questions:[{id:'q',type:'text',title:'答案'}]}} initialAnswers={{}} mode="entry" readOnly={false} onDirtyChange={setDirty} onSaveDraft={async()=>{if(fail)throw Error('保存冲突')}}/><button onClick={()=>void changes.confirmChange()}>检查修改</button></>}
 render(wrap(<Answer/>));await userEvent.type(screen.getByLabelText('答案'),'草稿');await userEvent.click(screen.getByText('保存草稿'));await screen.findByText('保存冲突');await userEvent.click(screen.getByText('检查修改'));await screen.findByRole('dialog',{name:'有未保存的修改，是否切换机构？'});await userEvent.click(screen.getByRole('button',{name:/取\s*消/}));await waitFor(()=>expect(screen.queryByRole('dialog')).not.toBeInTheDocument());fail=false;await userEvent.click(screen.getByText('保存草稿'));await screen.findByText('草稿已保存');await userEvent.click(screen.getByText('检查修改'));expect(screen.queryByRole('dialog',{name:'有未保存的修改，是否切换机构？'})).not.toBeInTheDocument();
});
test('其他标签页切换会清理旧编辑内容，不出现阻止切换的确认',async()=>{
 let listener:((event:{data:{type:string}})=>void)|null=null;
 class Channel {set onmessage(fn:typeof listener){listener=fn}close(){}postMessage(){}}
 const previous=window.BroadcastChannel;window.BroadcastChannel=Channel as unknown as typeof BroadcastChannel;
 try{render(wrap(<Probe/>));await screen.findByText('甲管理员');await userEvent.type(screen.getByLabelText('草稿'),'旧机构修改');server.use(http.get('*/api/auth/me/',()=>HttpResponse.json({...envelope,workspace_token:'token-b',actor:{...actor,name:'乙医生'}})));await act(async()=>listener?.({data:{type:'workspace_changed'}}));await screen.findByText('乙医生');expect(screen.getByLabelText('草稿')).toHaveValue('');expect(await screen.findByText('机构已在其他页面切换，未保存内容未提交')).toBeInTheDocument();expect(screen.queryByRole('dialog',{name:'有未保存的修改，是否切换机构？'})).not.toBeInTheDocument();}finally{window.BroadcastChannel=previous}
});
