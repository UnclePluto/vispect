import {QueryClient} from '@tanstack/react-query';
import {ApiError} from '../api/client';
export const queryClient=new QueryClient({defaultOptions:{queries:{staleTime:15000,retry:(count,error)=>!(error instanceof ApiError&&[401,403,404].includes(error.status))&&count<1,refetchOnWindowFocus:true}}});
