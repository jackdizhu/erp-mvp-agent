import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'

function loadCustomEnv(envDir, fileName) {
  const filePath = path.join(envDir, fileName)
  const env = {}
  if (fs.existsSync(filePath)) {
    const content = fs.readFileSync(filePath, 'utf-8')
    content.split('\n').forEach(line => {
      line = line.trim()
      if (!line || line.startsWith('#')) return
      const idx = line.indexOf('=')
      if (idx > 0) {
        const key = line.slice(0, idx).trim()
        const val = line.slice(idx + 1).trim()
        env[key] = val
      }
    })
  }
  return env
}

export default defineConfig(({ mode }) => {
  const projectRoot = process.cwd()
  
  // Load .default.env as base, then .development.env or .production.env as override
  const defaultEnv = loadCustomEnv(projectRoot, '.default.env')
  const modeFileName = mode === 'production' ? '.production.env' : '.development.env'
  const modeEnv = loadCustomEnv(projectRoot, modeFileName)
  
  const env = { ...defaultEnv, ...modeEnv }
  
  return {
    plugins: [react()],
    define: {
      'import.meta.env.VITE_API_PORT': JSON.stringify(env.VITE_API_PORT || '9000'),
    },
  }
})
