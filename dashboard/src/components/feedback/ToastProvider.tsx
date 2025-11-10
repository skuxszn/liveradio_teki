import * as React from 'react'
import * as Toast from '@radix-ui/react-toast'

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = React.useState(false)
  const [message, setMessage] = React.useState<string>('')
  const [variant, setVariant] = React.useState<'default'|'success'|'error'|'warning'>('default')

  const showToast = (msg: string, v: typeof variant = 'default') => {
    setMessage(msg)
    setVariant(v)
    setOpen(false)
    requestAnimationFrame(() => setOpen(true))
  }

  ;(window as any).appToast = showToast

  const bg = {
    default: 'bg-gray-900 text-white',
    success: 'bg-green-600 text-white',
    error: 'bg-red-600 text-white',
    warning: 'bg-yellow-600 text-white',
  }[variant]

  return (
    <Toast.Provider swipeDirection="right">
      {children}
      <Toast.Root open={open} onOpenChange={setOpen} className={`rounded-md p-4 shadow-lg ${bg}`}>
        <Toast.Title className="font-medium text-sm">{message}</Toast.Title>
      </Toast.Root>
      <Toast.Viewport className="fixed bottom-4 right-4 z-[100]" />
    </Toast.Provider>
  )
}

export function toast(msg: string, variant?: 'default'|'success'|'error'|'warning') {
  ;(window as any).appToast?.(msg, variant || 'default')
}



