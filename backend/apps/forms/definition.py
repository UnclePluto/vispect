import json
import math
from pathlib import Path
from jsonschema import Draft7Validator
SCHEMA=json.loads((Path(__file__).resolve().parents[3]/'contracts/form-definition.schema.json').read_text())
VALIDATOR=Draft7Validator(SCHEMA)

def validate_definition(definition,publish=False):
    invalid={'_definition':['invalid_definition']}
    try:
        if list(VALIDATOR.iter_errors(definition)):return invalid
        json.dumps(definition,allow_nan=False)
        questions=definition['questions'];ids=[q['id'] for q in questions]
        if len(ids)!=len(set(ids)):return invalid
        if publish and (not definition['title'].strip() or not questions):return invalid
        for i,q in enumerate(questions):
            kind=q['type'];options=q.get('options',[]);option_ids=[o['id'] for o in options]
            if publish and not q['title'].strip():return invalid
            if len(option_ids)!=len(set(option_ids)):return invalid
            if kind in ['radio','checkbox','select'] and not options:return invalid
            if kind not in ['radio','checkbox','select'] and 'options' in q:return invalid
            for lo,hi in [('min','max'),('min_length','max_length'),('min_selections','max_selections')]:
                if lo in q and hi in q and q[lo]>q[hi]:return invalid
            if kind=='slider' and (not all(k in q for k in ['min','max','step']) or q['min']>=q['max']):return invalid
            if any(k in q for k in ['min','max','precision']) and kind not in ['number','slider']:return invalid
            if 'step' in q and kind!='slider':return invalid
            if any(k in q for k in ['min_length','max_length']) and kind not in ['text','textarea']:return invalid
            if any(k in q for k in ['min_selections','max_selections']) and kind!='checkbox':return invalid
            if q.get('min_selections',0)>len(options):return invalid
            for rule in q.get('condition',{}).get('rules',[]):
                ref=rule['question_id'];op=rule['operator'];value=rule.get('value')
                if ref not in ids[:i]:return invalid
                source=questions[ids.index(ref)];source_type=source['type']
                if op!='answered' and 'value' not in rule:return invalid
                if op in ['gt','gte','lt','lte'] and (source_type not in ['number','slider'] or type(value) not in [int,float]):return invalid
                if op=='contains' and (source_type!='checkbox' or value not in [o['id'] for o in source.get('options',[])]):return invalid
                if op in ['eq','neq']:
                    if source_type=='checkbox':return invalid
                    if source_type in ['number','slider'] and type(value) not in [int,float]:return invalid
                    if source_type not in ['number','slider'] and not isinstance(value,str):return invalid
                    if source_type in ['radio','select'] and value not in [o['id'] for o in source['options']]:return invalid
            if 'jumps' in q:
                if kind not in ['radio','select']:return invalid
                if any(option not in option_ids or target not in ids[i+1:] for option,target in q['jumps'].items()):return invalid
        return {}
    except (TypeError,ValueError,KeyError,OverflowError):return invalid
