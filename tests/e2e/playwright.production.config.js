const path = require('path');
const { defineConfig, devices } = require('@playwright/test');

const repoRoot = path.resolve(__dirname, '../..');
const productionURL = process.env.VESTRA_PRODUCTION_URL || 'https://possn.github.io/Vestra/';

module.exports = defineConfig({
  testDir: '.',
  testMatch: ['production-smoke.spec.js', 'pwa-lifecycle.spec.js'],
  outputDir: path.join(repoRoot, 'test-results-production'),
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI
    ? [['list'], ['html', { outputFolder: path.join(repoRoot, 'playwright-report-production'), open: 'never' }]]
    : 'list',
  use: {
    baseURL: productionURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    serviceWorkers: 'block'
  },
  projects: [
    {
      name: 'webkit-iphone-production',
      testMatch: 'production-smoke.spec.js',
      use: {
        ...devices['iPhone 15'],
        browserName: 'webkit',
        serviceWorkers: 'block'
      }
    },
    {
      name: 'webkit-iphone-production-pwa',
      testMatch: 'pwa-lifecycle.spec.js',
      use: {
        ...devices['iPhone 15'],
        browserName: 'webkit',
        serviceWorkers: 'allow'
      }
    }
  ]
});
