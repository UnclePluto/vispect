import {expect,type Page,type Locator,type APIRequestContext} from '@playwright/test';
export const password=process.env.E2E_DEMO_PASSWORD??'E2e-Demo-Strong-Password-2026!';
const tokens=new WeakMap<APIRequestContext,string>();
export function bindWorkspace(request:APIRequestContext,token:string){tokens.set(request,token)}
export function phoneFor(tenant:string|null,username:string){
 const phones:Record<string,string>={'platform':'19900001000','demo-a:admin':'19900001001','demo-b:admin':'19900001002','demo-a:doctor1':'19900001003','demo-a:doctor2':'19900001004','demo-b:doctor1':'19900001001','demo-b:doctor2':'19900001005','e2e-zero:admin':'19900001006'};
 const phone=phones[tenant===null?'platform':`${tenant}:${username}`];if(!phone)throw Error('未配置演示手机号');return phone;
}
export async function login(page:Page,tenant:string|null,username:string){
 await page.goto('/login');await page.getByLabel('手机号',{exact:true}).fill(phoneFor(tenant,username));
 for(const candidate of [password,`${password}-Updated!`]){
  await page.getByLabel('密码',{exact:true}).fill(candidate);const response=page.waitForResponse(r=>r.url().endsWith('/api/auth/login/')&&r.request().method()==='POST');await page.getByRole('button',{name:/^登\s*录$/}).click();const logged=await response;if(logged.status()!==200)continue;
  let data=await logged.json();
  if(data.next==='change_password'){
   await page.waitForURL('/change-password');await page.getByLabel('原密码',{exact:true}).fill(candidate);await page.getByLabel('新密码',{exact:true}).fill(`${password}-Updated!`);await page.getByLabel('确认新密码',{exact:true}).fill(`${password}-Updated!`);
   const changed=page.waitForResponse(r=>r.url().endsWith('/api/auth/change-password/')&&r.request().method()==='POST');await page.getByRole('button',{name:'保存新密码'}).click();const result=await changed;expect(result.status()).toBe(200);data=await result.json();
  }
  if(data.next==='choose_workspace'){
   await page.waitForURL('/select-workspace');const option=data.workspaces.find((w:{tenant:{slug:string}|null;role:string})=>tenant===null?w.role==='platform_admin':w.tenant?.slug===tenant);
   if(!option)throw Error('目标机构未分配给该手机号');const switched=page.waitForResponse(r=>r.url().endsWith('/api/auth/switch-workspace/')&&r.request().method()==='POST');await choose(page,page.getByRole('combobox',{name:'当前机构'}),tenant===null?'平台管理中心':option.tenant.name);const result=await switched;expect(result.status()).toBe(200);data=await result.json();
  }
  bindWorkspace(page.request,data.workspace_token);await page.waitForURL(/\/(dashboard|tenants)$/);return;
 }
 throw new Error('演示手机号登录失败');
}
export async function choose(page:Page,control:Locator,label:string){await control.click();await expect(control).toHaveAttribute('aria-expanded','true');const listId=await control.getAttribute('aria-controls');const popup=page.locator(`[id="${listId}"]`).locator('xpath=ancestor::div[contains(@class,"ant-select-dropdown")][1]');await popup.locator('.ant-select-item-option').filter({hasText:label}).first().click()}
export async function get(request:APIRequestContext,url:string){const token=tokens.get(request);if(!token)throw Error('缺少页面捕获的空间令牌');return request.get(url,{headers:{'X-Workspace-Token':token}})}
export async function post(request:APIRequestContext,url:string,data:unknown,key=`e2e-${Date.now()}-${Math.random()}`){const token=tokens.get(request);if(!token)throw Error('缺少页面捕获的空间令牌');const csrf=await request.get('/api/auth/csrf/');return request.post(url,{data,headers:{'X-CSRFToken':(await csrf.json()).csrf_token,'X-Workspace-Token':token,'Idempotency-Key':key}})}
export async function finishVisit(page:Page){await page.getByRole('button',{name:'完成当前访视'}).click();await page.getByRole('button',{name:/^确\s*定$/}).click();await expect(page.getByText('已完成',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'完成当前访视'})).toBeDisabled()}
