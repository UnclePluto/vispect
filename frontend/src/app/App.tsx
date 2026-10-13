import zhCN from 'antd/locale/zh_CN';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';
dayjs.locale('zh-cn');
import {QueryClientProvider} from '@tanstack/react-query';
import {RouterProvider} from 'react-router-dom';
import {App as AntApp,ConfigProvider} from 'antd';
import {AuthProvider} from '../features/auth/AuthProvider';
import {queryClient} from './queryClient';
import {router} from './router';
import './style.css';
export function App(){return <QueryClientProvider client={queryClient}><ConfigProvider locale={zhCN}><AntApp><AuthProvider><RouterProvider router={router}/></AuthProvider></AntApp></ConfigProvider></QueryClientProvider>}
