import { expect, test } from '@playwright/test'

test('student demo: explore all views, change dates, and use the mock assistant', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  // This smoke flow must never contact an external service. Do not intercept
  // and replace API results: the purpose is to test real React -> Vite -> FastAPI.
  await page.route('**/*', route => {
    if (new URL(route.request().url()).origin !== 'http://127.0.0.1:15173') {
      errors.push('Unexpected external browser request')
      return route.abort()
    }
    return route.continue()
  })

  await page.goto('/')
  const total = page.getByRole('article').filter({ hasText: 'Total consumption' })
  await expect(total).toContainText('111.80')
  // The badge also contains a decorative dot; match its human-readable text.
  await expect(page.getByText(/Demo data/)).toBeVisible()

  // A real calendar filter should change the API result, not just the label.
  const history = page.getByRole('group', { name: 'Historical period (UTC)' })
  await history.getByLabel('Through', { exact: false }).fill('2009-06-01')
  await expect(total).toContainText('13.46')
  await history.getByLabel('Through', { exact: false }).fill('2009-06-07')
  await expect(total).toContainText('111.80')

  const tabs = page.getByRole('navigation', { name: 'Energy views' })
  await tabs.getByRole('button', { name: 'Anomalies' }).click()
  await expect(page.getByRole('row')).toHaveCount(4) // Header + three actual API records.
  await expect(page.getByText('Synthetic fixture spike; not a model detection.', { exact: true })).toHaveCount(3)

  await tabs.getByRole('button', { name: 'Forecast' }).click()
  await expect(page.getByRole('img', { name: /168 actual and 24 forecast intervals/ })).toBeVisible()
  await expect(page.getByText('Actual consumption', { exact: true })).toBeVisible()
  await expect(page.getByText('Illustrative forecast', { exact: true })).toBeVisible()
  await expect(page.getByText(/not a trained model or validated prediction/)).toBeVisible()
  await expect(page.getByText(/Origin: 08 Jun, 00:00 UTC/)).toBeVisible()

  await tabs.getByRole('button', { name: 'Assistant' }).click()
  await page.getByLabel('Your question').fill('Why was consumption high this week?')
  await page.getByRole('button', { name: 'Send question' }).click()
  const conversation = page.getByRole('log', { name: 'Assistant conversation' })
  await expect(conversation.getByText('Placeholder: chat is not implemented. Bedrock is not connected.', { exact: true })).toBeVisible()
  await expect(conversation.getByText(/Assistant disconnected/)).toBeVisible()
  await expect(conversation.getByText('No citations returned.', { exact: true })).toBeVisible()
  await expect(page.getByLabel('Your question')).toHaveValue('')

  // A second action must not discard a question the student has not sent yet.
  await page.getByLabel('Your question').fill('Keep this draft for later.')
  await page.getByRole('button', { name: 'Request weekly summary' }).click()
  await expect(conversation.getByText('Placeholder: weekly summary is not implemented. Bedrock is not connected.', { exact: true })).toBeVisible()
  await expect(page.getByLabel('Your question')).toHaveValue('Keep this draft for later.')
  expect(errors).toEqual([])
})
