import {Suspense} from 'react';
import zhCN from 'antd/locale/zh_CN';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';
dayjs.locale('zh-cn');
import {RouterProvider} from 'react-router-dom';
import {App as AntApp,ConfigProvider,Spin} from 'antd';
import {WorkspaceChangesProvider} from '../features/auth/WorkspaceChangesProvider';
import {router} from './router';
import './style.css';
export function App(){return <ConfigProvider locale={zhCN}><AntApp><WorkspaceChangesProvider><Suspense fallback={<div className="full-spin"><Spin size="large"/></div>}><RouterProvider router={router}/></Suspense></WorkspaceChangesProvider></AntApp></ConfigProvider>}
