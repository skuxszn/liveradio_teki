import * as React from 'react'
import { Bell, X } from 'lucide-react'

interface AppNotification { id: string; title: string; message: string; createdAt: string }

export default function NotificationsCenter() {
  const [open, setOpen] = React.useState(false)
  const [items, setItems] = React.useState<AppNotification[]>([])

  React.useEffect(() => {
    ;(window as any).pushNotification = (title: string, message: string) => {
      setItems((s) => [{ id: crypto.randomUUID(), title, message, createdAt: new Date().toISOString() }, ...s].slice(0, 100))
    }
  }, [])

  const remove = (id: string) => setItems((s) => s.filter((i) => i.id !== id))

  return (
    <div className="relative">
      <button aria-label="Notifications" className="p-2 rounded hover:bg-gray-100 relative" onClick={() => setOpen((o) => !o)}>
        <Bell className="w-5 h-5" />
        {items.length > 0 && <span className="absolute -top-0.5 -right-0.5 bg-red-600 text-white text-[10px] rounded-full px-1">{items.length}</span>}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-96 max-h-[70vh] overflow-auto rounded border bg-white shadow-lg z-50">
          <div className="p-3 border-b font-medium">Notifications</div>
          <div className="divide-y">
            {items.length === 0 ? (
              <div className="p-4 text-sm text-gray-500">No notifications</div>
            ) : items.map((n) => (
              <div key={n.id} className="p-3 text-sm flex items-start gap-2">
                <div className="flex-1">
                  <div className="font-medium">{n.title}</div>
                  <div className="text-gray-600">{n.message}</div>
                  <div className="text-[10px] text-gray-400 mt-1">{new Date(n.createdAt).toLocaleString()}</div>
                </div>
                <button aria-label="Dismiss" onClick={() => remove(n.id)} className="p-1 rounded hover:bg-gray-100">
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}



