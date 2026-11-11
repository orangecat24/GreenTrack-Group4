import { test } from '@playwright/test'
import { runStudentDemo } from './studentDemo'

test('student demo: explore all views, change dates, and use the mock assistant', async ({ page }) => {
  await runStudentDemo(page, ['http://127.0.0.1:15173'])
})
