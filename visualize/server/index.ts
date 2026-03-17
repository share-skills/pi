/**
 * PI Decision Visualizer — Server Entry Point
 *
 * Express + WebSocket server that serves the decision archive API
 * and pushes live updates to connected clients via WebSocket.
 *
 * Usage:
 *   npx tsx server/index.ts [--source <dir>] [--port <n>] [--no-open] [--production]
 *
 * Licensed under the Apache License, Version 2.0
 */

import { fileURLToPath } from 'url'
import path from 'path'
import fs from 'fs'
import http from 'http'
import express from 'express'
import { WebSocketServer, WebSocket } from 'ws'
import { parseDecisionsDir, deleteSession } from './parser'
import { createWatcher } from './watcher'
import type { DecisionArchive } from '../src/types'
import type { WSMessage } from '../src/types'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// ─── CLI Args ───────────────────────────────────────────────────

function parseArgs(argv: string[]) {
  const args = argv.slice(2)
  let source = path.join(process.env.HOME ?? '~', '.pi', 'decisions')
  let port = 3141
  let noOpen = false
  let production = false
  let mock = false

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--source':
        source = args[++i]
        break
      case '--port':
        port = parseInt(args[++i], 10)
        break
      case '--no-open':
        noOpen = true
        break
      case '--production':
        production = true
        break
      case '--mock':
        mock = true
        break
    }
  }

  return { source, port, noOpen, production, mock }
}

const config = parseArgs(process.argv)

// ─── State ──────────────────────────────────────────────────────

let currentArchive: DecisionArchive = {
  sessions: [],
  generatedAt: new Date().toISOString(),
  sourceDir: config.source,
}

// ─── Express App ────────────────────────────────────────────────

const app = express()
const server = http.createServer(app)

// CORS for Vite dev server
app.use((_req, res, next) => {
  res.header('Access-Control-Allow-Origin', 'http://localhost:5173')
  res.header('Access-Control-Allow-Methods', 'GET, DELETE, OPTIONS')
  res.header('Access-Control-Allow-Headers', 'Content-Type')
  if (_req.method === 'OPTIONS') {
    res.sendStatus(204)
    return
  }
  next()
})

// Cache-Control for API routes
app.use('/api', (_req, res, next) => {
  res.header('Cache-Control', 'no-store')
  next()
})

// API endpoints
app.get('/api/archive', (_req, res) => {
  res.json(currentArchive)
})

app.get('/api/sessions', (_req, res) => {
  // Return sessions without nodes for efficiency
  const sessions = currentArchive.sessions.map(({ nodes: _nodes, ...rest }) => rest)
  res.json({
    sessions,
    generatedAt: currentArchive.generatedAt,
    sourceDir: currentArchive.sourceDir,
  })
})

app.delete('/api/sessions/:id', async (req, res) => {
  const sessionId = req.params.id
  try {
    await deleteSession(config.source, sessionId)
    // Re-parse after deletion
    currentArchive = await parseDecisionsDir(config.source)
    broadcastArchive()
    res.json({ ok: true, message: `Session ${sessionId} deleted` })
  } catch (err) {
    res.status(500).json({ ok: false, error: (err as Error).message })
  }
})

// Mock data generation endpoint — supports on-demand scenario generation
app.get('/api/mock', async (_req, res) => {
  try {
    const { generateMockArchive } = await import('./mock-data')
    const mockArchive = generateMockArchive()
    // Also update the live archive and broadcast to all connected clients
    currentArchive = mockArchive
    broadcastArchive()
    res.json(mockArchive)
  } catch (err) {
    res.status(500).json({ ok: false, error: (err as Error).message })
  }
})

// Serve static files — always serve dist/ when it exists, regardless of --production flag.
// FIX: Previously gated behind --production, which caused "Cannot GET /" white screen
// when users ran `npm start` without the flag.
const distPath = path.resolve(__dirname, '..', 'dist')
if (fs.existsSync(distPath)) {
  app.use(express.static(distPath))
  // SPA fallback: all non-API routes serve index.html for client-side routing
  app.get('*', (_req, res) => {
    res.sendFile(path.join(distPath, 'index.html'))
  })
}

// ─── WebSocket ──────────────────────────────────────────────────

const wss = new WebSocketServer({ server, path: '/ws' })

wss.on('connection', (ws) => {
  console.log('[ws] Client connected')

  // Send connection info
  const connMsg: WSMessage = {
    type: 'connected',
    data: {
      sourceDir: config.source,
      sessionCount: currentArchive.sessions.length,
    },
  }
  ws.send(JSON.stringify(connMsg))

  // Send current archive
  const archiveMsg: WSMessage = { type: 'archive', data: currentArchive }
  ws.send(JSON.stringify(archiveMsg))

  // Handle pong
  ws.on('message', (raw) => {
    try {
      const msg = JSON.parse(raw.toString())
      if (msg.type === 'ping') {
        ws.send(JSON.stringify({ type: 'pong' }))
      }
    } catch { /* ignore malformed messages */ }
  })

  ws.on('close', () => {
    console.log('[ws] Client disconnected')
  })
})

function broadcastArchive() {
  const msg: WSMessage = { type: 'archive', data: currentArchive }
  const payload = JSON.stringify(msg)
  for (const client of wss.clients) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(payload)
    }
  }
}

// ─── Startup ────────────────────────────────────────────────────

async function start() {
  // Initial parse — use mock data if --mock flag is set
  if (config.mock) {
    console.log('[server] Loading MOCK data (covers all SKILL.md scenarios)')
    const { generateMockArchive } = await import('./mock-data')
    currentArchive = generateMockArchive()
    console.log(`[server] Generated ${currentArchive.sessions.length} mock session(s)`)
  } else {
    console.log(`[server] Parsing decisions from: ${config.source}`)
    currentArchive = await parseDecisionsDir(config.source)
    console.log(`[server] Found ${currentArchive.sessions.length} session(s)`)

    // Start file watcher (only for real data)
    createWatcher(config.source, (archive) => {
      currentArchive = archive
      console.log(`[server] Archive updated: ${archive.sessions.length} session(s)`)
      broadcastArchive()
    })
  }

  // Auto-free port if another process occupies it (avoids EADDRINUSE crash)
  try {
    const { execSync } = await import('child_process')
    const pids = execSync(`lsof -ti :${config.port} 2>/dev/null`, { encoding: 'utf-8' }).trim()
    if (pids) {
      console.log(`[server] Port ${config.port} occupied by PID ${pids.replace(/\n/g, ', ')}, killing...`)
      for (const pid of pids.split('\n')) {
        if (pid.trim()) {
          try { process.kill(parseInt(pid.trim()), 'SIGTERM') } catch { /* ignore */ }
        }
      }
      // Wait for the old process to release the port
      await new Promise(r => setTimeout(r, 1500))
    }
  } catch { /* lsof not available or no process — safe to proceed */ }

  server.listen(config.port, '127.0.0.1', async () => {
    const url = `http://127.0.0.1:${config.port}`
    console.log('')
    console.log('  ╔══════════════════════════════════════════╗')
    console.log('  ║   🥧 PI Decision Visualizer             ║')
    console.log(`  ║   Local:  ${url.padEnd(30)}║`)
    console.log(`  ║   WS:     ws://127.0.0.1:${String(config.port).padEnd(18)}║`)
    console.log(`  ║   Source: ${config.source.slice(-30).padEnd(30)}║`)
    console.log('  ╚══════════════════════════════════════════╝')
    console.log('')

    // Open browser unless --no-open
    if (!config.noOpen) {
      try {
        const open = (await import('open')).default
        await open(url)
      } catch {
        console.log(`[server] Could not open browser. Visit ${url} manually.`)
      }
    }
  })
}

start().catch((err) => {
  console.error('[server] Fatal error:', err)
  process.exit(1)
})
