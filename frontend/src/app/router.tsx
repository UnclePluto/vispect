import {StudiesPage} from '../features/studies/StudiesPage';
import {StudyDetail} from '../features/studies/StudyDetail';
import {FormDesigner} from '../features/forms/FormDesigner';
import {FormsPage} from '../features/forms/FormsPage';
import {PatientsPage} from '../features/patients/PatientsPage';
import {createBrowserRouter,Navigate,Outlet} from 'react-router-dom';
import {Spin,Result} from 'antd';
import {useAuth} from '../features/auth/AuthProvider';
import {LoginPage} from '../features/auth/LoginPage';
import {ChangePasswordPage} from '../features/auth/ChangePasswordPage';
import {AdminLayout} from './AdminLayout';
import {DoctorsPage} from '../features/doctors/DoctorsPage';
import {TenantsPage} from '../features/tenants/TenantsPage';
function AuthGate(){const {actor,loading}=useAuth();if(loading)return <div className="full-spin"><Spin size="large"/></div>;if(!actor)return <Navigate to="/login" replace/>;if(actor.must_change_password)return <Navigate to="/change-password" replace/>;return <Outlet/>}
function RoleGate({platform}:{platform:boolean}){const {actor}=useAuth();return (actor?.role==='platform_admin')===platform?<Outlet/>:<Result status="403" title="当前身份没有此页面权限"/>}
function Home(){const {actor}=useAuth();return <Navigate to={actor?.role==='platform_admin'?'/tenants':'/doctors'} replace/>}
function PasswordGate(){const {actor,loading}=useAuth();if(loading)return <Spin/>;return actor?<ChangePasswordPage/>:<Navigate to="/login" replace/>}
export const router=createBrowserRouter([{path:'/login',element:<LoginPage/>},{path:'/change-password',element:<PasswordGate/>},{element:<AuthGate/>,children:[{element:<AdminLayout/>,children:[{path:'/',element:<Home/>},{element:<RoleGate platform/>,children:[{path:'/tenants',element:<TenantsPage/>}]},{element:<RoleGate platform={false}/>,children:[{path:'/studies',element:<StudiesPage/>},{path:'/studies/:id',element:<StudyDetail/>},{path:'/forms/:id',element:<FormDesigner/>},{path:'/forms',element:<FormsPage/>},{path:'/patients',element:<PatientsPage/>},{path:'/doctors',element:<DoctorsPage/>}]}]}]},{path:'*',element:<Result status="404" title="页面不存在"/>}]);
