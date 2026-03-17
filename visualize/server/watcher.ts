/**
 * PI Decision Visualizer — File System Watcher
 *
 * Watches ~/.pi/decisions/ for changes using chokidar.
 * Debounces rapid changes and triggers re-parse on updates.
 *
 * Licensed under the Apache License, Version 2.0
 */

import chokidar from 'chokidar'
import type { FSWatcher } from 'chokidar'
import type { DecisionArchive } from '../src/types'
import { parseDecisionsDir } from './parser'

const DEBOUNCE_MS = 300

/**
 * Create a file system watcher on the decisions directory.
 * On any add/change/unlink event, re-parses the entire directory
 * (debounced) and calls the onChange callback with the new archive.
 */
export function createWatcher(
  dir: string,
  onChange: (archive: DecisionArchive) => void,
): FSWatcher {
  let debounceTimer: ReturnType<typeof setTimeout> | null = null

  const scheduleRebuild = () => {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(async () => {
      try {
        const archive = await parseDecisionsDir(dir)
        onChange(archive)
      } catch (err) {
        console.error('[watcher] Error re-parsing decisions:', (err as Error).message)
      }
    }, DEBOUNCE_MS)
  }

  const watcher = chokidar.watch(dir, {
    ignoreInitial: true,
    persistent: true,
    depth: 3,
    awaitWriteFinish: { stabilityThreshold: 200, pollInterval: 50 },
  })

  watcher
    .on('add', (filePath) => {
      console.log(`[watcher] File added: ${filePath}`)
      scheduleRebuild()
    })
    .on('change', (filePath) => {
      console.log(`[watcher] File changed: ${filePath}`)
      scheduleRebuild()
    })
    .on('unlink', (filePath) => {
      console.log(`[watcher] File removed: ${filePath}`)
      scheduleRebuild()
    })
    .on('error', (err) => {
      console.error('[watcher] Error:', err.message)
    })

  console.log(`[watcher] Watching ${dir}`)
  return watcher
}
