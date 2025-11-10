import { Button } from '@/components/ui/button'
import { Trash2 } from 'lucide-react'

export function BulkActionToolbar({ count, onDelete }: { count: number; onDelete: () => void; }) {
  if (count === 0) return null
  return (
    <div className="sticky top-0 z-10 bg-white border rounded-md p-3 flex items-center justify-between shadow-sm">
      <div className="text-sm">{count} selected</div>
      <div className="flex items-center gap-2">
        <Button variant="destructive" size="sm" onClick={onDelete} aria-label="Delete selected mappings">
          <Trash2 className="w-4 h-4 mr-1" /> Delete Selected
        </Button>
      </div>
    </div>
  )
}



