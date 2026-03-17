import { useEffect, useRef } from 'react'
import { useStore } from './store'
import { useWebSocket } from './hooks/useWebSocket'
import TopBar from './components/TopBar'
import TreeNav from './components/TreeNav'
import DecisionCanvas from './components/DecisionCanvas'
import DetailDrawer from './components/DetailDrawer'
import StatusBar from './components/StatusBar'

export default function App() {
  // FIX: Use individual selectors instead of object selector. Object selectors
  // create a new wrapper object on every state change → Object.is fails → component
  // re-renders on ANY store mutation, not just the fields it cares about.
  const setArchive = useStore(s => s.setArchive)
  const selectNode = useStore(s => s.selectNode)
  const toggleSidebar = useStore(s => s.toggleSidebar)
  const toggleDetailDrawer = useStore(s => s.toggleDetailDrawer)
  const setTimelinePosition = useStore(s => s.setTimelinePosition)
  const isPlaying = useStore(s => s.isPlaying)
  const togglePlay = useStore(s => s.togglePlay)
  const theme = useStore(s => s.theme)

  useWebSocket()

  // Apply theme class to root element
  useEffect(() => {
    document.documentElement.classList.remove('theme-dark', 'theme-light')
    document.documentElement.classList.add(`theme-${theme}`)
  }, [theme])

  // Fetch archive on mount as fallback
  useEffect(() => {
    fetch('/api/archive')
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setArchive(data) })
      .catch(() => {})
  }, [setArchive])

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      const step = 0.05 // 5% per keypress
      switch (e.key) {
        case 'Escape':
          selectNode(null)
          break
        case '[':
          toggleSidebar()
          break
        case ']':
          toggleDetailDrawer()
          break
        case 'ArrowLeft':
          e.preventDefault()
          setTimelinePosition(Math.max(0, useStore.getState().timelinePosition - step))
          break
        case 'ArrowRight':
          e.preventDefault()
          setTimelinePosition(Math.min(1, useStore.getState().timelinePosition + step))
          break
        case ' ':
          e.preventDefault()
          togglePlay()
          break
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [selectNode, toggleSidebar, toggleDetailDrawer, setTimelinePosition, togglePlay])

  // Auto-play: advance timeline with requestAnimationFrame
  const rafRef = useRef<number>(0)
  const lastFrameRef = useRef<number>(0)

  useEffect(() => {
    if (!isPlaying) {
      lastFrameRef.current = 0
      return
    }

    const animate = (timestamp: number) => {
      if (lastFrameRef.current === 0) {
        lastFrameRef.current = timestamp
      }
      const delta = timestamp - lastFrameRef.current
      lastFrameRef.current = timestamp

      const { timelinePosition, playSpeed } = useStore.getState()
      const advance = playSpeed * 0.005 * (delta / 16.67) // normalize to ~60fps
      const next = timelinePosition + advance

      if (next >= 1) {
        setTimelinePosition(1)
        useStore.getState().togglePlay() // auto-stop
      } else {
        setTimelinePosition(next)
        rafRef.current = requestAnimationFrame(animate)
      }
    }

    rafRef.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(rafRef.current)
  }, [isPlaying, setTimelinePosition])

  const bgColor = theme === 'light' ? 'bg-[#f0ebe3]' : 'bg-[#0a0a0f]'
  const textColor = theme === 'light' ? 'text-[#2d2b3a]' : 'text-slate-100'

  return (
    <div className={`h-screen w-screen flex flex-col ${bgColor} overflow-hidden ${textColor}`}>
      <TopBar />
      <div className="flex flex-1 min-h-0 relative">
        <TreeNav />
        <DecisionCanvas />
        <DetailDrawer />
      </div>
      <StatusBar />
    </div>
  )
}
