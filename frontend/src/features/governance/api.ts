import {api} from '../../api/client';
import type {Page,Revision} from '../../api/types';
export type AuditEvent={id:string;tenant_id:string|null;actor_id:string;actor_name:string;action:string;object_type:string;object_id:string;changes:Record<string,unknown>;created_at:string};
export type Recycled=Revision&{resource:'doctor'|'patient'|'study'|'form';name:string;deleted_at:string};
export const resourceLabels:Record<string,string>={doctor:'医生',patient:'患者',study:'研究',form:'表单',enrollment:'受试者',visit:'访视',answer:'答案',tenant:'机构',account:'账号'};
export const actionLabels:Record<string,string>={create:'创建',update:'修改',delete:'删除',restore:'恢复',assign_doctors:'分配负责医生',save_draft:'保存草稿',publish:'发布',pause:'暂停表单',resume:'恢复表单',protocol:'配置访视',members:'配置成员',state:'变更研究状态',add_subject:'加入研究',confirm_enrollment:'确认入组',transfer:'转交随访',submit:'提交答案',revise:'修订答案',complete:'完成访视',stop:'停止随访',export:'导出',seed_demo_complete:'初始化演示资料',bootstrap_platform:'初始化平台账号',create_tenant:'创建机构',update_tenant:'配置机构',configure_administrator:'配置机构管理员',reset_global_password:'重置全局密码',set_global_enabled:'变更全局账号状态'};
export const getAudit=(platform:boolean,page:number,action='',object_type='')=>api<Page<AuditEvent>>(`/api/${platform?'platform/':''}audit/?${new URLSearchParams({page:String(page),action,object_type})}`);
export const getRecycle=(page:number,resource='')=>api<Page<Recycled>>(`/api/recycle/?${new URLSearchParams({page:String(page),resource})}`);
export const restoreRecord=(record:Recycled)=>api(`/api/${({doctor:'doctors',patient:'patients',study:'studies',form:'forms'})[record.resource]}/${record.id}/restore/`,{method:'POST',body:{expected_revision:record.revision}});
export function formatTime(value:string){return new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(new Date(value))}
