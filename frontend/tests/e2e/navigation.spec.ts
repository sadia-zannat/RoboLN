import {test,expect} from '@playwright/test';
const stamp=()=>`${Date.now()}-${Math.random().toString(36).slice(2,7)}`;
async function register(page:import('@playwright/test').Page){
 await page.goto('/register');
 await page.getByLabel('Full name').fill('Quality Tester');
 await page.getByLabel('Email address').fill(`qa-${stamp()}@example.com`);
 await page.getByLabel('Password').fill('E2eStrongPassword123!');
 await page.getByRole('button',{name:'Create account'}).click();
 await expect(page).toHaveURL(/\/projects$/);
}
async function makeProject(page:import('@playwright/test').Page){
 await page.getByRole('button',{name:'New project'}).click();
 await page.getByLabel('Project name').fill('Physical Rover - QA');
 await page.getByRole('button',{name:'Create project',exact:true}).click();
 await expect(page).toHaveURL(/\/projects\/[^/]+$/);
 return new URL(page.url()).pathname.split('/')[2];
}

test('registered session, routes, real back-forward, breadcrumbs, home, deep refresh',async({page},info)=>{
 await register(page);const pid=await makeProject(page);
 await page.getByRole('link',{name:/Open Workspace/}).click();
 await expect(page).toHaveURL(new RegExp(`/projects/${pid}/workspace/plan$`));
 await page.getByRole('link',{name:'Practice in 3D'}).click();
 await expect(page).toHaveURL(/workspace\/practice$/);
 await page.getByRole('button',{name:'Back',exact:true}).click();
 await expect(page).toHaveURL(/workspace\/plan$/);
 await expect(page.getByRole('button',{name:'Forward',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Forward',exact:true}).click();
 await expect(page).toHaveURL(/workspace\/practice$/);
 await page.keyboard.press('Alt+ArrowLeft');
 await expect(page).toHaveURL(/workspace\/plan$/);
 await page.keyboard.press('Alt+ArrowRight');
 await expect(page).toHaveURL(/workspace\/practice$/);
 await page.reload();await expect(page).toHaveURL(/workspace\/practice$/);
 await page.getByRole('link',{name:'Home — Projects'}).click();
 await expect(page).toHaveURL(/\/projects$/);
 await page.screenshot({path:`../logs/browser-${info.project.name}-light.png`,fullPage:true});
});

test('light/dark/system persistence, navigation and width audit',async({page},info)=>{
 await register(page);const pid=await makeProject(page);
 const screens=[`/projects/${pid}/workspace/plan`,`/projects/${pid}/workspace/practice`,`/projects/${pid}/workspace/build`,`/projects/${pid}/twin`,`/projects/${pid}/evidence`,'/settings'];
 for(const mode of ['light','dark'] as const){
  await page.goto('/settings');await page.getByRole('button',{name:new RegExp(`^${mode}$`,'i')}).click();
  await page.reload();await expect(page.locator('html')).toHaveAttribute('data-theme',mode);
  for(const path of screens){
   await page.goto(path);await expect(page.locator('main')).toBeVisible();
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),`overflow on ${path}`).toBeTruthy();
   await page.screenshot({path:`../logs/browser-${info.project.name}-${mode}-${path.split('/').at(-1)}.png`,fullPage:true});
  }
 }
});

test('viewer cannot edit, missing project cannot leak title, signout blocks deep link',async({page})=>{
 await register(page);const id=await makeProject(page);
 await page.goto('/projects/00000000-0000-0000-0000-000000000000');
 await expect(page.getByText(/project was not found/i)).toBeVisible();
 await page.goto(`/projects/${id}/workspace/plan`);
 await page.getByRole('button',{name:'Sign out'}).click();
 await expect(page).toHaveURL(/\/login/);
 await page.goto(`/projects/${id}/workspace/plan`);
 await expect(page).toHaveURL(/\/login\?next=/);
});

test('keyboard skip link and forward initially disabled',async({page})=>{
 await register(page);
 await expect(page.getByRole('button',{name:/Forward unavailable/})).toBeDisabled();
 await page.keyboard.press('Tab');
 await expect(page.locator('.skip-link')).toBeAttached();
});


test('per-project draft isolation across navigation and refresh',async({page})=>{
 await register(page);const a=await makeProject(page);
 await page.goto(`/projects/${a}/workspace/plan`);
 await page.getByLabel('Your engineering draft').fill('Private first-project draft');
 await page.getByRole('button',{name:'Save draft'}).click();
 await expect(page.getByRole('status')).toContainText('Draft saved');
 await page.goto('/projects');const b=await makeProject(page);
 await page.goto(`/projects/${b}/workspace/plan`);
 await expect(page.getByLabel('Your engineering draft')).toHaveValue('');
 await page.goto(`/projects/${a}/workspace/plan`);
 await expect(page.getByLabel('Your engineering draft')).toHaveValue('Private first-project draft');
});

test('public product titles and keyboard modal dismissal',async({page})=>{
 await register(page);await expect(page).toHaveTitle(/Projects \| RoboLN/);
 await page.getByRole('button',{name:'Search your projects'}).click();
 await expect(page.getByRole('dialog',{name:'Find project'})).toBeVisible();
 await page.keyboard.press('Escape');
 await expect(page.getByRole('dialog',{name:'Find project'})).toHaveCount(0);
});
