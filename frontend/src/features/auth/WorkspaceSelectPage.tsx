import {Alert,Button,Card,Space,Typography,Spin} from 'antd';
import {Navigate} from 'react-router-dom';
import {useAuth} from './AuthProvider';
import {WorkspaceSwitcher} from './WorkspaceSwitcher';
export function WorkspaceSelectPage(){const auth=useAuth();if(auth.loading)return <Spin/>;if(!auth.user)return <Navigate to="/login" replace/>;if(auth.next==='change_password')return <Navigate to="/change-password" replace/>;if(auth.actor)return <Navigate to="/" replace/>;return <div className="login-page"><Card className="login-card"><Typography.Title level={3}>选择机构</Typography.Title><Space orientation="vertical" size="large" style={{width:'100%'}}>{auth.workspaces.length?<WorkspaceSwitcher/>:<Alert type="info" title="暂无可用机构，请联系机构管理员。"/>}<Button onClick={()=>auth.refreshIdentity()}>刷新机构</Button><Button onClick={()=>auth.logout()}>退出登录</Button></Space></Card></div>}
