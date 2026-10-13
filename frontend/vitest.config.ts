import {defineConfig} from 'vitest/config';
import react from '@vitejs/plugin-react';
export default defineConfig({plugins:[react()],test:{environment:'jsdom',globals:true,pool:'forks',poolOptions:{forks:{execArgv:['--no-experimental-webstorage']}},setupFiles:['./src/test/setup.ts'],exclude:['e2e/**','node_modules/**']}});
