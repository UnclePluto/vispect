import json
from pathlib import Path
from django.core.management.base import BaseCommand,CommandError
from django.db import connections
from apps.accounts.migration_mapping import preflight_mapping,apply_mapping
from apps.core.errors import ApiError

class Command(BaseCommand):
    help='按显式手机号映射预检旧账号；只有 --apply 才写入，不输出密码。'
    def add_arguments(self,parser):
        parser.add_argument('--mapping',required=True)
        parser.add_argument('--apply',action='store_true')
    def handle(self,*args,**options):
        if 'migration' not in connections:raise CommandError('请使用 VISPECT_MANAGEMENT=1 和独立迁移凭据运行')
        try:
            document=json.loads(Path(options['mapping']).read_text())
            groups=document['groups']
        except (OSError,ValueError,KeyError,TypeError) as exc:raise CommandError('映射文件须为包含 groups 的有效 JSON') from exc
        report=preflight_mapping(groups)
        self.stdout.write(json.dumps(report,ensure_ascii=False))
        if not report['valid']:raise CommandError('映射预检未通过，未修改数据')
        if options['apply']:
            try:report=apply_mapping(groups)
            except ApiError as exc:raise CommandError(exc.message) from exc
            self.stdout.write(json.dumps(report,ensure_ascii=False))
