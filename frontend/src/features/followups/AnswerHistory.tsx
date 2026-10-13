import {useState} from 'react';
import {Alert,Descriptions,Drawer,Table} from 'antd';
import {useQuery} from '@tanstack/react-query';
import {errorMessage} from '../../api/client';
import {getHistory} from './api';
export function AnswerHistory({id,onClose}:{id:string|null;onClose:()=>void}){const [page,setPage]=useState(1);const q=useQuery({queryKey:['answer-history',id,page],queryFn:()=>getHistory(id!,page),enabled:!!id});return <Drawer title="答案修订历史" open={!!id} onClose={onClose} size="large">{q.error?<Alert type="error" title={errorMessage(q.error)}/>:<Table rowKey="id" loading={q.isLoading} dataSource={q.data?.results} pagination={{current:page,total:q.data?.count,pageSize:20,onChange:setPage,showSizeChanger:false}} columns={[{title:'原修订号',dataIndex:'previous_revision'},{title:'修订人',dataIndex:'actor_name'},{title:'原因',dataIndex:'reason'},{title:'时间',dataIndex:'created_at'}]} expandable={{expandedRowRender:r=><Descriptions column={1} bordered items={Object.entries(r.previous_answers).map(([key,value])=>({key,label:key,children:typeof value==='string'?value:JSON.stringify(value)}))}/>}}/>}</Drawer>}
