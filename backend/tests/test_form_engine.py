import json
from pathlib import Path
import pytest
from apps.forms.engine import evaluate_answers
from apps.forms.definition import validate_definition
CASES=json.loads((Path(__file__).resolve().parents[2]/'contracts/form-cases.json').read_text())
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_shared_form_cases(case):
    result=evaluate_answers(case['definition'],case['answers'],case['mode'])
    assert result.visible_ids==case['expected']['visible_ids']
    assert result.answers==case['expected']['answers']
    assert result.errors==case['expected']['errors']
    assert bool(validate_definition(case['definition'],True))==case.get('definition_invalid',False)
@pytest.mark.parametrize('value',[float('inf'),float('-inf'),float('nan')])
def test_non_finite_numbers_rejected(value):
    definition={'protocol_version':1,'title':'测试','questions':[{'id':'a','title':'数字','type':'number'}]}
    assert evaluate_answers(definition,{'a':value},'submit').errors=={'a':['invalid_type']}
