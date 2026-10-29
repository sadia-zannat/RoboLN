import {defineConfig,devices} from '@playwright/test';
export default defineConfig({
  testDir:'../tests/e2e', timeout:45000, retries:0, workers:1,
  reporter:[['list'],['html',{outputFolder:'../logs/playwright-report',open:'never'}]],
  use:{baseURL:'http://127.0.0.1:3000',trace:'retain-on-failure',screenshot:'only-on-failure'},
  projects:[
    {name:'desktop-1440',use:{...devices['Desktop Chrome'],viewport:{width:1440,height:900}}},
    {name:'tablet-768',use:{...devices['Desktop Chrome'],viewport:{width:768,height:1024}}},
    {name:'mobile-390',use:{...devices['Desktop Chrome'],viewport:{width:390,height:844},isMobile:true,hasTouch:true}},
    {name:'mobile-320',use:{...devices['Desktop Chrome'],viewport:{width:320,height:700},isMobile:true,hasTouch:true}}
  ],
  webServer:[
    {command:'python -m uvicorn app.api:app --host 127.0.0.1 --port 8000',cwd:'../backend',url:'http://127.0.0.1:8000/api/health',reuseExistingServer:!process.env.CI,timeout:45000},
    {command:'npm run dev',cwd:'.',url:'http://127.0.0.1:3000/login',reuseExistingServer:!process.env.CI,timeout:60000}
  ]
});
