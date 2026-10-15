import {test,expect} from '@playwright/test';
import {login,choose} from './helpers';
test('跨机构不同角色切换与未保存确认',async({page})=>{
 await login(page,'demo-a','admin');await expect(page.getByRole('heading',{name:'工作台'})).toBeVisible();
 await page.goto('/patients');await page.getByRole('button',{name:'新增患者'}).click();await page.getByLabel('姓名',{exact:true}).fill('未提交的修改');
 // A header behind a modal is not interactive; cancel the editor to use the header.
 await page.getByRole('dialog').getByRole('button',{name:/取\s*消/}).click();
 await page.goto('/forms');await page.getByRole('button',{name:'新建表单'}).click();await page.getByLabel('表单名称').fill('切换前未保存表单');
 await choose(page,page.getByRole('combobox',{name:'当前机构'}),'示例健康机构 B');
 await expect(page.getByRole('dialog',{name:'有未保存的修改，是否切换机构？'})).toBeVisible();await page.getByRole('button',{name:/取\s*消/}).click();await expect(page.getByLabel('表单名称')).toHaveValue('切换前未保存表单');
 await choose(page,page.getByRole('combobox',{name:'当前机构'}),'示例健康机构 B');await page.getByRole('button',{name:'放弃修改并切换'}).click();await page.waitForURL('/dashboard');await expect(page.getByText('我的资料',{exact:true})).toBeVisible();await expect(page.getByText('机构审计',{exact:true})).toHaveCount(0);
 const switcher=page.getByRole('combobox',{name:'当前机构'});await expect(switcher).toBeVisible();
 await choose(page,switcher,'示例健康机构 A');await page.waitForURL('/dashboard');await expect(page.getByText('机构审计',{exact:true})).toBeVisible();
});
test('同会话旧标签页即使没有广播也不能向新机构写入或导出',async({page,context})=>{
 await login(page,'demo-a','admin');const initial=await (await page.request.get('/api/auth/me/')).json();const oldToken=initial.workspace_token;
 const old=await context.newPage();await old.addInitScript(()=>{Object.defineProperty(window,'BroadcastChannel',{value:undefined})});await old.goto('/patients');await old.getByRole('button',{name:'新增患者'}).click();await old.getByLabel('档案编号').fill('STALE-PATIENT');await old.getByLabel('姓名',{exact:true}).fill('不应写入新机构');
 const switching=page.waitForResponse(r=>r.url().endsWith('/api/auth/switch-workspace/')&&r.request().method()==='POST');await choose(page,page.getByRole('combobox',{name:'当前机构'}),'示例健康机构 B');const next=await (await switching).json();expect(next.actor.role).toBe('doctor');
 const csrf=(await (await old.request.get('/api/auth/csrf/')).json()).csrf_token;
 const stale=await old.request.post('/api/patients/',{data:{code:'STALE-PATIENT',name:'不应写入新机构'},headers:{'X-CSRFToken':csrf,'X-Workspace-Token':oldToken}});expect(stale.status()).toBe(409);expect((await stale.json()).code).toBe('workspace_changed');
 const exported=await old.request.get('/api/studies/00000000-0000-0000-0000-000000000001/export/',{headers:{'X-Workspace-Token':oldToken}});expect(exported.status()).toBe(409);
 const patients=await old.request.get('/api/patients/?search=STALE-PATIENT',{headers:{'X-Workspace-Token':next.workspace_token}});expect(patients.status()).toBe(200);expect((await patients.json()).count).toBe(0);
 const rejected=old.waitForResponse(r=>r.url().endsWith('/api/patients/')&&r.request().method()==='POST');await choose(old,old.getByRole('dialog').getByLabel('负责医生'),'示例医生1');await old.getByRole('dialog').getByRole('button',{name:/保\s*存/}).click();expect((await rejected).status()).toBe(409);await expect(old.getByRole('dialog')).toHaveCount(0);
});

test('平台与机构身份并存，切换后权限独立',async({page,browser},testInfo)=>{
 const helper=await import('./helpers');await login(page,'demo-a','admin');
 const added=await helper.post(page.request,'/api/doctors/',{login_phone:'19900001000',name:'平台账号的机构医生资料'});expect(added.status()).toBe(201);
 const context=await browser.newContext({baseURL:testInfo.project.use.baseURL}),platform=await context.newPage();await login(platform,null,'platform');expect((await helper.get(platform.request,'/api/patients/')).status()).toBe(403);
 await choose(platform,platform.getByRole('combobox',{name:'当前机构'}),'示例健康机构 A');await platform.waitForURL('/dashboard');await expect(platform.getByText('我的资料',{exact:true})).toBeVisible();await expect(platform.getByText('全局账号',{exact:true})).toHaveCount(0);
 const current=await (await platform.request.get('/api/auth/me/')).json();expect(current.actor.role).toBe('doctor');expect((await platform.request.get('/api/platform/accounts/?phone=19900001000',{headers:{'X-Workspace-Token':current.workspace_token}})).status()).toBe(403);
 await choose(platform,platform.getByRole('combobox',{name:'当前机构'}),'平台管理中心');await platform.waitForURL('/tenants');await expect(platform.getByText('全局账号',{exact:true})).toBeVisible();await context.close();
});

test('停用 B 成员后统一身份仍能进入 A',async({page,browser},testInfo)=>{
 const helper=await import('./helpers');await login(page,'demo-b','doctor1');
 const context=await browser.newContext({baseURL:testInfo.project.use.baseURL}),admin=await context.newPage();await login(admin,'demo-b','admin');
 const doctors=(await (await helper.get(admin.request,'/api/doctors/')).json()).results;const doctor=doctors.find((d:{login_phone:string})=>d.login_phone==='+8619900001001');
 expect((await helper.post(admin.request,`/api/doctors/${doctor.id}/enabled/`,{enabled:false,expected_revision:doctor.revision})).status()).toBe(200);
 await page.goto('/patients');await page.waitForURL('/select-workspace');await expect(page.getByRole('heading',{name:'选择机构'})).toBeVisible();
 await choose(page,page.getByRole('combobox',{name:'当前机构'}),'示例健康机构 A');await page.waitForURL('/dashboard');await expect(page.getByText('机构审计',{exact:true})).toBeVisible();
 const after=(await (await helper.get(admin.request,`/api/doctors/${doctor.id}/`)).json());expect((await helper.post(admin.request,`/api/doctors/${doctor.id}/enabled/`,{enabled:true,expected_revision:after.revision})).status()).toBe(200);await context.close();
});
