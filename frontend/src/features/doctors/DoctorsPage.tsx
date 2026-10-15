import {useState} from 'react';
import {Alert,Button,Card,Input,Popconfirm,Select,Space,Table,Tag,Typography,App} from 'antd';
import {PlusOutlined} from '@ant-design/icons';
import {useQuery,useQueryClient} from '@tanstack/react-query';
import {useActor} from '../auth/AuthProvider';
import {errorMessage} from '../../api/client';
import {DoctorEditor} from './DoctorEditor';
import {DoctorDetail} from './DoctorDetail';
import {getDoctors,deleteDoctor,setDoctorEnabled,type Doctor} from './api';
export function DoctorsPage(){
    const actor=useActor(),cache=useQueryClient(),{message}=App.useApp(),[page,setPage]=useState(1),[search,setSearch]=useState(''),[enabled,setEnabled]=useState<boolean>(),[editor,setEditor]=useState<Doctor|null|undefined>(),[detail,setDetail]=useState<Doctor|null>(null);
    const query=useQuery({queryKey:['doctors',page,search,enabled],queryFn:()=>getDoctors(page,search,enabled)}),admin=actor?.role==='tenant_admin';
    const refresh=()=>cache.invalidateQueries({queryKey:['doctors']});
    async function action(run:()=>Promise<Doctor>){try{await run();await refresh();message.success('操作成功')}catch(e){message.error(errorMessage(e))}}
    const columns=[{title:'姓名',dataIndex:'name',render:(_:unknown,d:Doctor)=><Button type="link" onClick={()=>setDetail(d)}>{d.name}</Button>},{title:'登录手机号',dataIndex:'login_phone'},{title:'所属单位',dataIndex:'organization'},{title:'科室',dataIndex:'department'},{title:'职称',dataIndex:'title'},{title:'联系方式',dataIndex:'phone'},{title:'本机构成员状态',render:(_:unknown,d:Doctor)=><Tag color={d.enabled?'green':'default'}>{d.enabled?'启用':'停用'}</Tag>},{title:'操作',render:(_:unknown,d:Doctor)=><Space><Button type="link" onClick={()=>setEditor(d)}>编辑</Button>{admin&&<><Button type="link" onClick={()=>action(()=>setDoctorEnabled(d,!d.enabled))}>{d.enabled?'停用':'启用'}</Button><Popconfirm title="删除医生档案？" description="删除前需转交患者及未结束研究的负责关系。" onConfirm={()=>action(()=>deleteDoctor(d))}><Button type="link" danger>删除</Button></Popconfirm></>}</Space>}];
    return <><div className="page-heading"><div><Typography.Title level={3}>{admin?'医生管理':'我的资料'}</Typography.Title><Typography.Text type="secondary">管理账号、专业资料与启用状态</Typography.Text></div>{admin&&<Button type="primary" icon={<PlusOutlined/>} onClick={()=>setEditor(null)}>新增医生</Button>}</div><Card><Space className="search-bar" wrap><Input.Search placeholder="搜索姓名或手机号" allowClear onSearch={v=>{setSearch(v);setPage(1)}} style={{width:280}}/><Select placeholder="全部状态" allowClear onChange={v=>{setEnabled(v);setPage(1)}} style={{width:140}} options={[{value:true,label:'启用'},{value:false,label:'停用'}]}/></Space>{query.error&&<Alert type="error" title={errorMessage(query.error)} style={{marginBottom:16}}/>}<Table rowKey="id" columns={columns} dataSource={query.isError?[]:query.data?.results} loading={query.isLoading} pagination={{current:page,total:query.data?.count,pageSize:20,onChange:setPage,showSizeChanger:false,showTotal:total=>`共 ${total} 名医生`}} scroll={{x:1000}}/></Card><DoctorEditor open={editor!==undefined} doctor={editor} onCancel={()=>setEditor(undefined)} onSaved={()=>{setEditor(undefined);refresh()}}/><DoctorDetail doctor={detail} onClose={()=>setDetail(null)}/></>
}
