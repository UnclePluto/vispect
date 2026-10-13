import {api} from '../../api/client';
import type {Visit} from '../followups/api';
export type Dashboard={patients:number;studies:number;today_tasks:number;overdue_tasks:number;tasks:Visit[]};
export const getDashboard=()=>api<Dashboard>('/api/dashboard/');
