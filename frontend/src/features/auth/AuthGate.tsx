import {Navigate,Outlet} from 'react-router-dom';
import {Spin} from 'antd';
import {authDestination,useAuth} from './AuthProvider';
export function AuthGate(){const {user,actor,next,loading}=useAuth();if(loading)return <div className="full-spin"><Spin size="large"/></div>;if(!user)return <Navigate to="/login" replace/>;if(next!=='ready'||!actor)return <Navigate to={authDestination(next)} replace/>;return <Outlet/>}
