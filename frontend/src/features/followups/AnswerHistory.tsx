import {useEffect,useState} from 'react';
import {Alert,Collapse,Descriptions,Drawer,Table} from 'antd';
import {useQuery} from '@tanstack/react-query';
import {errorMessage} from '../../api/client';
import {getHistory,type History} from './api';
import {displayHistoryValue,historyChanges} from './answerOrigins';
function Snapshot({row,after}:{row:History;after:boolean}){const answers=after?row.new_answers??{}:row.previous_answers;return <Descriptions column={1} bordered items={Object.entries(answers).map(([id,value])=>{const question=row.definition?.questions.find(q=>q.id===id);return {key:id,label:question?.title??id,children:displayHistoryValue(question,value)}})}/>}
export function AnswerHistory({id,onClose}:{id:string|null;onClose:()=>void}){
 const [page,setPage]=useState(1);useEffect(()=>setPage(1),[id]);
 const q=useQuery({queryKey:['answer-history',id,page],queryFn:()=>getHistory(id!,page),enabled:!!id});
 return <Drawer title="答案修订历史" open={!!id} onClose={onClose} size="large">{q.error?<Alert type="error" title={errorMessage(q.error)}/>:<Table rowKey="id" loading={q.isLoading} dataSource={q.data?.results} pagination={{current:page,total:q.data?.count,pageSize:20,onChange:setPage,showSizeChanger:false}} columns={[{title:'原修订号',dataIndex:'previous_revision'},{title:'原录入主体',dataIndex:'previous_recorded_by_name'},{title:'修订人',dataIndex:'actor_name'},{title:'原因',dataIndex:'reason'},{title:'时间',dataIndex:'created_at'}]} expandable={{expandedRowRender:row=><>{row.new_answers&&<Table size="small" rowKey="id" pagination={false} dataSource={historyChanges(row)} columns={[{title:'题目',dataIndex:'title'},{title:'修改前',dataIndex:'before'},{title:'修改后',dataIndex:'after'}]}/>}<Collapse style={{marginTop:12}} items={[{key:'before',label:'修改前完整答案',children:<Snapshot row={row} after={false}/>},{key:'after',label:'修改后完整答案',children:<Snapshot row={row} after/>}]}/></>}}/>}</Drawer>
}
