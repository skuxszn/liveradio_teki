import * as React from 'react'

export default function OfflineBanner() {
  const [online, setOnline] = React.useState(navigator.onLine)
  React.useEffect(() => {
    const on = () => setOnline(true)
    const off = () => setOnline(false)
    window.addEventListener('online', on)
    window.addEventListener('offline', off)
    return () => {
      window.removeEventListener('online', on)
      window.removeEventListener('offline', off)
    }
  }, [])
  if (online) return null
  return (
    <div className="w-full bg-yellow-100 text-yellow-900 text-sm px-4 py-2 text-center">
      You are offline. Changes will be sent when connection is restored.
    </div>
  )
}



