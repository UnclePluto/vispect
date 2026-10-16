from .selectors import visible_answers


def revision_policy(actor,answer):
    if not actor or not visible_answers(actor).filter(id=answer.id).exists():return False,'当前没有此答案的修订权限'
    if answer.status!='submitted':return False,'草稿请直接保存'
    visit=answer.visit;e=visit.enrollment;study=e.study;form=answer.form_version.form
    if study.state!='active':return False,'研究当前只读'
    if e.state=='stopped' or visit.status=='stopped':return False,'随访已停止，答案只读'
    if form.paused or form.deleted_at:return False,'表单已暂停或删除，答案只读'
    if answer.respondent=='patient' and visit.status=='completed':return True,None
    if visit.status=='pending' and e.state in ['screening','following'] and e.current_visit_id==visit.id:return True,None
    return False,'只有当前未完成访视允许修订此答案'
