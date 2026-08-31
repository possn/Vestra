const path = require('path');
const { defineConfig, devices } = require('@playwright/test');

const repoRoot = path.resolve(__dirname, '../..');

module.exports = defineConfig({
  testDir: '.',
  outputDir: path.join(repoRoot, 'test-results'),
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI
    ? [['list'], ['html', { outputFolder: path.join(repoRoot, 'playwright-report'), open: 'never' }]]
    : 'list',
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    serviceWorkers: 'block'
  },
  projects: [
    {
      name: 'webkit-iphone',
      use: {
        ...devices['iPhone 15'],
        browserName: 'webkit'
      }
    }
  ],
  webServer: {
    command: `python3 -m http.server 4173 --bind 127.0.0.1 --directory "${repoRoot}"`,
    url: 'http://127.0.0.1:4173/index.html',
    reuseExistingServer: !process.env.CI,
    timeout: 30_000
  }
});
