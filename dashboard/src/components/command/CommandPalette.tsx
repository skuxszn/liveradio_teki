import * as React from 'react'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { useNavigate } from 'react-router-dom'
import { streamService } from '@/services/stream.service'

const commands = [
  { label: 'Go: Dashboard', run: (nav: any) => nav('/') },
  { label: 'Go: Stream', run: (nav: any) => nav('/stream') },
  { label: 'Go: Track Mappings', run: (nav: any) => nav('/mappings') },
  { label: 'Go: Video Assets', run: (nav: any) => nav('/assets') },
  { label: 'Go: Monitoring', run: (nav: any) => nav('/monitoring') },
  { label: 'Go: Logs', run: (nav: any) => nav('/monitoring?tab=logs') },
  { label: 'Go: Settings', run: (nav: any) => nav('/settings') },
  { label: 'Settings: Stream', run: (nav: any) => nav('/settings?tab=stream') },
  { label: 'Settings: Encoding', run: (nav: any) => nav('/settings?tab=encoding') },
  { label: 'Settings: Notifications', run: (nav: any) => nav('/settings?tab=notifications') },
  { label: 'Settings: Database', run: (nav: any) => nav('/settings?tab=database') },
  { label: 'Settings: Security', run: (nav: any) => nav('/settings?tab=security') },
  { label: 'Settings: Paths', run: (nav: any) => nav('/settings?tab=paths') },
  { label: 'Settings: Advanced', run: (nav: any) => nav('/settings?tab=advanced') },
  { label: 'Action: Start Stream', run: async () => { await streamService.start() } },
  { label: 'Action: Stop Stream', run: async () => { await streamService.stop() } },
  { label: 'Action: Restart Stream', run: async () => { await streamService.restart() } },
]

export default function CommandPalette() {
  const [open, setOpen] = React.useState(false)
  const [q, setQ] = React.useState('')
  const nav = useNavigate()

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setOpen(true) }
    }
    window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey)
  }, [])

  const list = commands.filter(c => c.label.toLowerCase().includes(q.toLowerCase()))

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="p-0">
        <div className="border-b px-3 py-2">
          <input autoFocus placeholder="Type a command…" value={q} onChange={(e) => setQ(e.target.value)} className="w-full outline-none text-sm" />
        </div>
        <div className="max-h-80 overflow-auto" aria-label="Command results (Ctrl/Cmd+K)">
          {list.map((c, i) => (
            <button key={i} onClick={async () => { await c.run(nav); setOpen(false) }} className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50">
              {c.label}
            </button>
          ))}
          {list.length === 0 && <div className="px-3 py-6 text-sm text-gray-500">No results</div>}
        </div>
      </DialogContent>
    </Dialog>
  )
}


