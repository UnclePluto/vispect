from .schedule import local_today

def enrollment_payload(e):
    return {'id':str(e.id),'study_id':str(e.study_id),'study_name':e.study.name,'patient_id':str(e.patient_id),'patient_code':e.patient.code,'patient_name':e.patient.name,'doctor_id':str(e.doctor_id),'doctor_name':e.doctor.name,'observation_code':e.observation_code,'enrollment_code':e.enrollment_code,'added_on':e.added_on.isoformat(),'enrolled_on':e.enrolled_on.isoformat() if e.enrolled_on else None,'state':e.state,'current_visit_id':str(e.current_visit_id) if e.current_visit_id else None,'revision':e.revision,'stop_type':e.stop_type,'stop_reason':e.stop_reason}

def visit_payload(v,detail=False):
    today=local_today();e=v.enrollment
    data={'id':str(v.id),'enrollment_id':str(v.enrollment_id),'study_id':str(v.study_id),'study_name':e.study.name,'patient_id':str(e.patient_id),'patient_code':e.patient.code,'patient_name':e.patient.name,'doctor_id':str(e.doctor_id),'doctor_name':e.doctor.name,'stage_id':str(v.stage_id),'stage_name':v.stage.name,'stage_kind':v.stage.kind,'position':v.stage.position,'planned_on':v.planned_on.isoformat(),'window_start':v.window_start.isoformat(),'window_end':v.window_end.isoformat(),'status':v.status,'is_current':e.current_visit_id==v.id,'is_today':v.planned_on==today,'overdue':v.status=='pending' and today>v.window_end,'revision':v.revision,'completed_at':v.completed_at.isoformat() if v.completed_at else None,'writable':e.study.state=='active' and e.state in ['screening','following'] and v.status=='pending' and e.current_visit_id==v.id,'study_state':e.study.state,'enrollment_state':e.state}
    if detail:data['bindings']=[{'id':str(b.id),'form_version_id':str(b.form_version_id),'definition':b.form_version.definition,'form_paused':b.form_version.form.paused,'respondent':b.respondent,'required':b.required} for b in v.stage.bindings.select_related('form_version__form')]
    return data

def recorder_name(staff,patient_identity):
    return staff.name if staff else f'患者账号（尾号 {patient_identity.phone[-4:]}）' if patient_identity else '—'


def answer_payload(answer):
    return {'id':str(answer.id),'visit_id':str(answer.visit_id),'binding_id':str(answer.binding_id),'form_version_id':str(answer.form_version_id),'respondent':answer.respondent,'is_proxy':answer.is_proxy,'recorded_by_kind':'patient' if answer.recorded_by_patient_id else 'staff','recorded_by_id':str(answer.recorded_by_id) if answer.recorded_by_id else None,'recorded_by_patient_id':str(answer.recorded_by_patient_id) if answer.recorded_by_patient_id else None,'recorded_by_name':recorder_name(answer.recorded_by,answer.recorded_by_patient),'submission_source':answer.submission_source,'submitted_by_id':str(answer.submitted_by_id) if answer.submitted_by_id else None,'submitted_by_patient_id':str(answer.submitted_by_patient_id) if answer.submitted_by_patient_id else None,'submitted_by_name':recorder_name(answer.submitted_by,answer.submitted_by_patient),'answers':answer.answers,'status':answer.status,'revision':answer.revision,'submitted_at':answer.submitted_at.isoformat() if answer.submitted_at else None,'updated_at':answer.updated_at.isoformat()}
