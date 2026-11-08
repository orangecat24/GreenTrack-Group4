import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { resolve } from 'node:path'

// Use the same repository-local Python 3.14 environment on Windows and Linux.
// An absolute executable path also handles spaces in this student's checkout.
const root = resolve(import.meta.dirname, '../..')
const python = resolve(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')
if (!existsSync(python)) {
  console.error('Missing .venv. Create it with Python 3.14 and install api/requirements-dev.txt first.')
  process.exit(1)
}

// Do not pass AWS settings from a developer/CI shell into the demo process.
// Values are neither read for application use nor printed. The mock repository
// has no cloud clients; pytest separately blocks application network connections.
const env = { ...process.env, APP_DATA_MODE: 'mock' }
for (const name of Object.keys(env)) {
  if (name.startsWith('AWS_')) delete env[name]
}
env.AWS_EC2_METADATA_DISABLED = 'true'

const child = spawn(python, [
  '-m', 'uvicorn', 'app.main:app', '--app-dir', 'api',
  '--host', '127.0.0.1', '--port', '18000',
], { cwd: root, env, stdio: 'inherit', windowsHide: true })

child.on('error', () => {
  console.error('Could not start the mock API. Check .venv and the installed Python dependencies.')
  process.exitCode = 1
})
child.on('exit', code => { process.exitCode = code ?? 1 })
// Playwright owns this process tree and tears it down after success or failure.
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => { child.kill(signal) })
}
