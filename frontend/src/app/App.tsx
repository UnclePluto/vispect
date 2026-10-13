import {QueryClientProvider} from '@tanstack/react-query';
import {RouterProvider} from 'react-router-dom';
import {App as AntApp} from 'antd';
import {AuthProvider} from '../features/auth/AuthProvider';
import {queryClient} from './queryClient';
import {router} from './router';
import './style.css';
export function App(){return <QueryClientProvider client={queryClient}><AntApp><AuthProvider><RouterProvider router={router}/></AuthProvider></AntApp></QueryClientProvider>}
