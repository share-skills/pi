/**
 * PI Decision Visualizer — Error Boundary
 *
 * Prevents blank/black screen when React components crash.
 * Shows a user-friendly error message instead of a blank page.
 *
 * Licensed under the Apache License, Version 2.0
 */

import { Component, type ReactNode, type ErrorInfo } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Log to console for debugging — no printStackTrace per project rules
    console.error('[PI Visualizer] React error boundary caught:', error.message)
    console.error('[PI Visualizer] Component stack:', info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          height: '100vh',
          width: '100vw',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#0a0a0f',
          color: '#e2e8f0',
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          padding: '2rem',
        }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⚠️</div>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem' }}>
            PI Visualizer encountered an error
          </h1>
          <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginBottom: '1.5rem', textAlign: 'center', maxWidth: '400px' }}>
            {this.state.error?.message ?? 'An unexpected error occurred'}
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '0.5rem 1.5rem',
              background: '#6366f1',
              color: 'white',
              border: 'none',
              borderRadius: '0.5rem',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: 500,
            }}
          >
            Reload Page
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
