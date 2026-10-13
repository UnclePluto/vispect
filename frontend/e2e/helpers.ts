import {expect,type Page,type Locator,type APIRequestContext} from '@playwright/test';
export const password=process.env.E2E_DEMO_PASSWORD??'E2e-Demo-Strong-Password-2026!';
export async function login(page:Page,tenant:string|null,username:string){
 await page.goto('/login');if(tenant===null)await page.getByText('平台管理',{exact:true}).click();else await page.getByLabel('租户标识',{exact:true}).fill(tenant);
 await page.getByLabel('用户名',{exact:true}).fill(username);
 for(const candidate of [password,`${password}-Updated!`]){
  await page.getByLabel('密码',{exact:true}).fill(candidate);const response=page.waitForResponse(r=>r.url().endsWith(tenant===null?'/api/auth/platform-login/':'/api/auth/tenant-login/')&&r.request().method()==='POST');await page.getByRole('button',{name:/^登\s*录$/}).click();if((await response).status()!==200)continue;
  await page.waitForURL(/\/(change-password|dashboard|tenants)$/);
  if(page.url().endsWith('/change-password')){await page.getByLabel('原密码',{exact:true}).fill(candidate);await page.getByLabel('新密码',{exact:true}).fill(`${password}-Updated!`);await page.getByLabel('确认新密码',{exact:true}).fill(`${password}-Updated!`);await page.getByRole('button',{name:'保存新密码'}).click();await page.waitForURL(/\/(dashboard|tenants)$/)}
  return;
 }
 throw new Error('演示账号登录失败');
}
export async function choose(page:Page,control:Locator,label:string){await control.click();await expect(control).toHaveAttribute('aria-expanded','true');const listId=await control.getAttribute('aria-controls');const popup=page.locator(`[id="${listId}"]`).locator('xpath=ancestor::div[contains(@class,"ant-select-dropdown")][1]');await popup.locator('.ant-select-item-option').filter({hasText:label}).first().click()}
export async function post(request:APIRequestContext,url:string,data:unknown,key=`e2e-${Date.now()}-${Math.random()}`){const csrf=await request.get('/api/auth/csrf/');return request.post(url,{data,headers:{'X-CSRFToken':(await csrf.json()).csrf_token,'Idempotency-Key':key}})}
export async function finishVisit(page:Page){await page.getByRole('button',{name:'完成当前访视'}).click();await page.getByRole('button',{name:/^确\s*定$/}).click();await expect(page.getByText('已完成',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'完成当前访视'})).toBeDisabled()}
