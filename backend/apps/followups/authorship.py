def set_answer_recorder(answer, *, staff_id=None, patient_identity_id=None):
    if (staff_id is None) == (patient_identity_id is None):
        raise ValueError('答案必须有且只有一个录入主体')
    answer.recorded_by_id=staff_id
    answer.recorded_by_patient_id=patient_identity_id


def stamp_answer_submission(answer):
    if answer.submission_source is not None:return
    answer.submitted_by_id=answer.recorded_by_id
    answer.submitted_by_patient_id=answer.recorded_by_patient_id
    answer.submission_source='patient' if answer.recorded_by_patient_id else 'proxy' if answer.respondent=='patient' else 'doctor'
    answer.is_proxy=answer.submission_source=='proxy'
