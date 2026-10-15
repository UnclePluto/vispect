#!/usr/bin/env python3
"""默认只预检固定虚构演示映射，显式 --apply 原子应用；不改变临床记录。"""
import argparse,json,os,sys,tempfile
from pathlib import Path
from io import StringIO
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'));os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');os.environ['VISPECT_MANAGEMENT']='1'
import django;django.setup()
from apps.accounts.demo_upgrade import demo_identity_mapping
from django.core.management import call_command
report=demo_identity_mapping()
if args.apply:
    if not report['valid'] or report['legacy_unmapped_account_ids']:
        print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit('存在冲突或未映射旧账号，未应用。请提供明确映射后再处理。')
    with tempfile.NamedTemporaryFile(mode='w',suffix='.json',encoding='utf-8') as mapping:
        json.dump({'groups':report['groups']},mapping,ensure_ascii=False);mapping.flush();result=StringIO()
        call_command('migrate_login_identities',mapping=mapping.name,apply=True,stdout=result)
        print(result.getvalue(),end='')
else:print(json.dumps(report,ensure_ascii=False,indent=2))
