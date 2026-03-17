import type { SessionMetrics } from '../types'

interface MetricsPanelProps {
  metrics: SessionMetrics
}

interface MetricCard {
  label: string
  value: string | number
  icon: string
  color: string
}

export default function MetricsPanel({ metrics }: MetricsPanelProps) {
  const cards: MetricCard[] = [
    {
      label: 'Tokens',
      value: metrics.total_tokens > 1000
        ? `${(metrics.total_tokens / 1000).toFixed(1)}k`
        : metrics.total_tokens,
      icon: '🎯',
      color: metrics.total_tokens > 50000 ? 'text-amber-400' : 'text-slate-300',
    },
    {
      label: 'Complexity',
      value: `${metrics.complexity_score}/5`,
      icon: '🧩',
      color: metrics.complexity_score >= 4 ? 'text-red-400' : metrics.complexity_score >= 3 ? 'text-amber-400' : 'text-green-400',
    },
    {
      label: 'Deep Explore',
      value: metrics.deep_exploration_count,
      icon: '🔬',
      color: metrics.deep_exploration_count > 3 ? 'text-amber-400' : 'text-slate-300',
    },
    {
      label: 'Loops',
      value: metrics.loop_count,
      icon: '🔄',
      color: metrics.loop_count > 2 ? 'text-red-400' : 'text-slate-300',
    },
    {
      label: 'Quality',
      value: metrics.quality_score,
      icon: '⭐',
      color: metrics.quality_score >= 80 ? 'text-green-400' : metrics.quality_score >= 50 ? 'text-amber-400' : 'text-red-400',
    },
    {
      label: 'Max Battle',
      value: `L${metrics.max_battle_level}`,
      icon: '⚔️',
      color: metrics.max_battle_level >= 4 ? 'text-red-400' : metrics.max_battle_level >= 2 ? 'text-amber-400' : 'text-slate-300',
    },
    {
      label: 'Beast',
      value: metrics.beast_activations,
      icon: '🐉',
      color: metrics.beast_activations > 0 ? 'text-purple-400' : 'text-slate-500',
    },
  ]

  return (
    <div className="grid grid-cols-2 gap-2">
      {cards.map(card => (
        <div
          key={card.label}
          className="bg-pi-surface-hover rounded-lg px-2.5 py-2 border border-pi-border"
        >
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="text-xs">{card.icon}</span>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider">{card.label}</span>
          </div>
          <span className={`text-sm font-semibold font-mono ${card.color}`}>
            {card.value}
          </span>
        </div>
      ))}
    </div>
  )
}
