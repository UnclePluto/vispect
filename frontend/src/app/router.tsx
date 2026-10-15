import {lazy} from 'react';
const GlobalAccountsPage=lazy(()=>import('../features/accounts/GlobalAccountsPage').then(module=>({default:module.GlobalAccountsPage})));
const AuditPage=lazy(()=>import('../features/governance/AuditPage').then(module=>({default:module.AuditPage})));
const RecycleBinPage=lazy(()=>import('../features/governance/RecycleBinPage').then(module=>({default:module.RecycleBinPage})));
const DashboardPage=lazy(()=>import('../features/dashboard/DashboardPage').then(module=>({default:module.DashboardPage})));
const VisitCalendar=lazy(()=>import('../features/followups/VisitCalendar').then(module=>({default:module.VisitCalendar})));
const VisitDetail=lazy(()=>import('../features/followups/VisitDetail').then(module=>({default:module.VisitDetail})));
const EnrollmentDetail=lazy(()=>import('../features/followups/EnrollmentDetail').then(module=>({default:module.EnrollmentDetail})));
const StudiesPage=lazy(()=>import('../features/studies/StudiesPage').then(module=>({default:module.StudiesPage})));
const StudyDetail=lazy(()=>import('../features/studies/StudyDetail').then(module=>({default:module.StudyDetail})));
const FormDesigner=lazy(()=>import('../features/forms/FormDesigner').then(module=>({default:module.FormDesigner})));
const FormsPage=lazy(()=>import('../features/forms/FormsPage').then(module=>({default:module.FormsPage})));
const PatientsPage=lazy(()=>import('../features/patients/PatientsPage').then(module=>({default:module.PatientsPage})));
import {createBrowserRouter,Navigate,Outlet} from 'react-router-dom';
import {Spin,Result} from 'antd';
import {useAuth,authDestination} from '../features/auth/AuthProvider';
import {WorkspaceSelectPage} from '../features/auth/WorkspaceSelectPage';
const LoginPage=lazy(()=>import('../features/auth/LoginPage').then(module=>({default:module.LoginPage})));
const ChangePasswordPage=lazy(()=>import('../features/auth/ChangePasswordPage').then(module=>({default:module.ChangePasswordPage})));
import {AdminLayout} from './AdminLayout';
const DoctorsPage=lazy(()=>import('../features/doctors/DoctorsPage').then(module=>({default:module.DoctorsPage})));
const TenantsPage=lazy(()=>import('../features/tenants/TenantsPage').then(module=>({default:module.TenantsPage})));
function AuthGate(){const {user,actor,next,loading}=useAuth();if(loading)return <div className="full-spin"><Spin size="large"/></div>;if(!user)return <Navigate to="/login" replace/>;if(next!=='ready'||!actor)return <Navigate to={authDestination(next)} replace/>;return <Outlet/>}
function RoleGate({platform}:{platform:boolean}){const {actor}=useAuth();return (actor?.role==='platform_admin')===platform?<Outlet/>:<Result status="403" title="当前身份没有此页面权限"/>}
function TenantAdminGate(){const {actor}=useAuth();return actor?.role==='tenant_admin'?<Outlet/>:<Result status="403" title="此页面仅机构管理员可访问"/>}
function Home(){const {actor}=useAuth();return <Navigate to={actor?.role==='platform_admin'?'/tenants':'/dashboard'} replace/>}
function PasswordGate(){const {user,loading}=useAuth();if(loading)return <Spin/>;return user?<ChangePasswordPage/>:<Navigate to="/login" replace/>}
export const router=createBrowserRouter([{path:'/select-workspace',element:<WorkspaceSelectPage/>},{path:'/login',element:<LoginPage/>},{path:'/change-password',element:<PasswordGate/>},{element:<AuthGate/>,children:[{element:<AdminLayout/>,children:[{path:'/',element:<Home/>},{element:<RoleGate platform/>,children:[{path:'/accounts',element:<GlobalAccountsPage/>},{path:'/platform-audit',element:<AuditPage/>},{path:'/tenants',element:<TenantsPage/>}]},{element:<RoleGate platform={false}/>,children:[{element:<TenantAdminGate/>,children:[{path:'/audit',element:<AuditPage/>},{path:'/recycle',element:<RecycleBinPage/>}]},{path:'/dashboard',element:<DashboardPage/>},{path:'/calendar',element:<VisitCalendar/>},{path:'/visits/:id',element:<VisitDetail/>},{path:'/enrollments/:id',element:<EnrollmentDetail/>},{path:'/studies',element:<StudiesPage/>},{path:'/studies/:id',element:<StudyDetail/>},{path:'/forms/:id',element:<FormDesigner/>},{path:'/forms',element:<FormsPage/>},{path:'/patients',element:<PatientsPage/>},{path:'/doctors',element:<DoctorsPage/>}]}]}]},{path:'*',element:<Result status="404" title="页面不存在"/>}]);
