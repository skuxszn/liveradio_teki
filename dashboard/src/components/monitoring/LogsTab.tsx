import * as React from 'react'
import { Button } from '@/components/ui/button'
import api from '@/services/api'
import { Download, Pause, Play } from 'lucide-react'
import { toast } from '@/components/feedback/ToastProvider'

export default function LogsTab() {
  const [lines, setLines] = React.useState<string[]>([])
  const [autoScroll, setAutoScroll] = React.useState(true)
  const [paused, setPaused] = React.useState(false)
  const [filterText, setFilterText] = React.useState('')
  const [filterLevel, setFilterLevel] = React.useState<'all'|'info'|'warn'|'error'>('all')
  const scrollRef = React.useRef<HTMLDivElement>(null)

  const fetchLogs = React.useCallback(async () => {
    if (paused) return
    try {
      const res = await api.get('/logs/stream/logs')
      let content = typeof res.data === 'string' ? res.data : (res.data?.content || JSON.stringify(res.data))
      // Normalize escaped line breaks ("\n") into real newlines
      if (typeof content === 'string') {
        content = content.replace(/\r\n/g, '\n').replace(/\\r\\n/g, '\n').replace(/\\n/g, '\n')
      }
      setLines(String(content || '').split('\n'))
    } catch (e: any) {
      toast(`Failed to load logs: ${e?.message || 'Error'}`, 'error')
    }
  }, [paused])

  React.useEffect(() => { const id = setInterval(fetchLogs, 2000); return () => clearInterval(id) }, [fetchLogs])

  React.useEffect(() => {
    if (autoScroll && scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [lines, autoScroll])

  const download = () => {
    const blob = new Blob([lines.join('\n')], { type: 'text/plain' })
    const url = URL.createObjectURL(blob); const a = document.createElement('a')
    a.href = url; a.download = `stream-logs-${new Date().toISOString()}.txt`; a.click(); URL.revokeObjectURL(url)
  }

  const getLevel = (l: string): 'info'|'warn'|'error'|'other' => {
    const s = l.toLowerCase()
    if (s.includes(' error') || s.includes('] error') || s.includes(' err ')) return 'error'
    if (s.includes(' warn') || s.includes('] warn')) return 'warn'
    if (s.includes(' info') || s.includes('] info')) return 'info'
    return 'other'
  }

  const filtered = lines.filter((l) => {
    const lvl = getLevel(l)
    const levelOk = filterLevel === 'all' ? true : lvl === filterLevel
    const textOk = filterText ? l.toLowerCase().includes(filterText.toLowerCase()) : true
    return levelOk && textOk
  })

  const copyLine = async (l: string) => {
    await navigator.clipboard.writeText(l)
    toast('Line copied', 'success')
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <input
          aria-label="Filter logs"
          value={filterText}
          onChange={(e) => setFilterText(e.target.value)}
          placeholder="Filter text..."
          className="h-9 border rounded px-2 text-sm"
        />
        <select
          aria-label="Filter level"
          value={filterLevel}
          onChange={(e) => setFilterLevel(e.target.value as any)}
          className="h-9 border rounded px-2 text-sm"
        >
          <option value="all">All</option>
          <option value="info">Info</option>
          <option value="warn">Warn</option>
          <option value="error">Error</option>
        </select>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="outline" onClick={() => setPaused((p) => !p)} aria-label={paused ? 'Resume logs' : 'Pause logs'}>
          {paused ? <Play className="w-4 h-4 mr-2" /> : <Pause className="w-4 h-4 mr-2" />}
          {paused ? 'Resume' : 'Pause'}
        </Button>
        <Button variant="outline" onClick={() => setAutoScroll((s) => !s)} aria-label="Toggle auto scroll">
          {autoScroll ? 'Disable Auto-Scroll' : 'Enable Auto-Scroll'}
        </Button>
        <Button variant="outline" onClick={download} aria-label="Download logs"><Download className="w-4 h-4 mr-2" />Download</Button>
      </div>
      <div ref={scrollRef} className="h-[480px] overflow-auto rounded border bg-black text-green-200 text-xs font-mono p-3">
        {filtered.map((l, i) => (
          <div key={i} className="whitespace-pre flex items-start gap-2 group" onClick={() => setPaused(true)}>
            <div className="flex-1">{l}</div>
            <button aria-label="Copy line" onClick={(e) => { e.stopPropagation(); copyLine(l) }} className="opacity-0 group-hover:opacity-100 text-white/70 hover:text-white">
              Copy
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}


