import {defineConfig,devices} from '@playwright/test';
import {existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
export default defineConfig({testDir:'./e2e',fullyParallel:false,workers:1,timeout:180000,expect:{timeout:10000},use:{actionTimeout:15000,baseURL:'http://127.0.0.1:5174',trace:'retain-on-failure',screenshot:'only-on-failure'},projects:[{name:'chromium',use:{...devices['Desktop Chrome']}}],webServer:[{command:`uv run --project backend ${existsSync(`${root}/.env`)?'--env-file .env ':''}--no-sync python scripts/e2e-server.py`,cwd:root,url:'http://127.0.0.1:8001/api/health/',reuseExistingServer:false,timeout:120000},{command:'pnpm dev --port 5174',cwd:fileURLToPath(new URL('.',import.meta.url)),url:'http://127.0.0.1:5174',env:{VISPECT_API_TARGET:'http://127.0.0.1:8001'},reuseExistingServer:false,timeout:120000}]});
