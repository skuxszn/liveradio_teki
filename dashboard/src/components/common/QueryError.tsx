import { Button } from '@/components/ui/button'

export function QueryError({ message, onRetry }: { message?: string; onRetry: () => void }) {
  return (
    <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700 flex items-center justify-between">
      <div>{message || 'Failed to load data.'}</div>
      <Button size="sm" variant="outline" onClick={onRetry} aria-label="Retry loading">
        Retry
      </Button>
    </div>
  )
}



