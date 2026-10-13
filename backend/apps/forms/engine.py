import math,re
from datetime import date
from decimal import Decimal
from dataclasses import dataclass
from .definition import validate_definition

@dataclass
class EvaluationResult:
    visible_ids:list[str]
    answers:dict
    errors:dict[str,list[str]]

def missing(value):return value is None or value=='' or value==[]
def condition_matches(condition,answers):
    if not condition:return True
    def match(rule):
        key=rule['question_id'];op=rule['operator']
        if key not in answers:return False
        value=answers[key];target=rule.get('value')
        if op=='answered':return True
        if op=='eq':return value==target
        if op=='neq':return value!=target
        if op=='contains':return target in value
        if op=='gt':return value>target
        if op=='gte':return value>=target
        if op=='lt':return value<target
        if op=='lte':return value<=target
        return False
    values=[match(r) for r in condition['rules']]
    return all(values) if condition['mode']=='all' else any(values)

def answer_error(q,value):
    kind=q['type']
    if kind in ['text','textarea']:
        if not isinstance(value,str):return 'invalid_type'
        if len(value)<q.get('min_length',0) or len(value)>q.get('max_length',100000):return 'length'
    elif kind in ['number','slider']:
        if type(value) not in [int,float] or not math.isfinite(value):return 'invalid_type'
        if value<q.get('min',-1e12) or value>q.get('max',1e12):return 'out_of_range'
        decimal=Decimal(str(value))
        if 'precision' in q and max(0,-decimal.normalize().as_tuple().exponent)>q['precision']:return 'precision'
        if kind=='slider' and (decimal-Decimal(str(q['min'])))%Decimal(str(q['step']))!=0:return 'step'
    elif kind=='date':
        if not isinstance(value,str):return 'invalid_type'
        try:
            if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value):return 'invalid_date'
            date.fromisoformat(value)
        except ValueError:return 'invalid_date'
    elif kind in ['radio','select']:
        if not isinstance(value,str):return 'invalid_type'
        if value not in [o['id'] for o in q['options']]:return 'invalid_option'
    elif kind=='checkbox':
        if not isinstance(value,list) or any(not isinstance(v,str) for v in value):return 'invalid_type'
        if len(set(value))!=len(value) or any(v not in [o['id'] for o in q['options']] for v in value):return 'invalid_option'
        if len(value)<q.get('min_selections',0) or len(value)>q.get('max_selections',len(q['options'])):return 'selection_count'
    return None

def evaluate_answers(definition,answers,mode):
    errors=validate_definition(definition)
    if errors:return EvaluationResult([],{},errors)
    if mode not in ['draft','submit'] or not isinstance(answers,dict):return EvaluationResult([],{}, {'_answers':['invalid_type']})
    questions=definition['questions'];ids=[q['id'] for q in questions]
    result=EvaluationResult([],{}, {key:['unknown_question'] for key in answers if key not in ids})
    skip_until=0
    for i,q in enumerate(questions):
        key=q['id']
        if i<skip_until or not condition_matches(q.get('condition'),result.answers):continue
        result.visible_ids.append(key);value=answers.get(key)
        if missing(value):
            if mode=='submit' and q.get('required'):result.errors[key]=['required']
            continue
        error=answer_error(q,value)
        if error:result.errors[key]=[error];continue
        result.answers[key]=value
        if q['type'] in ['radio','select'] and value in q.get('jumps',{}):skip_until=ids.index(q['jumps'][value])
    return result
