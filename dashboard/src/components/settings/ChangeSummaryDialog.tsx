import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

export function ChangeSummaryDialog({ open, onOpenChange, changes, onConfirm }: { open: boolean; onOpenChange: (o: boolean) => void; changes: Array<{ key: string; from: string; to: string }>; onConfirm: () => void; }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Review changes</DialogTitle>
          <DialogDescription>These settings will be updated. Some may require a stream restart.</DialogDescription>
        </DialogHeader>
        <div className="max-h-72 overflow-auto border rounded">
          <table className="w-full text-sm">
            <thead><tr className="bg-gray-50"><th className="p-2 text-left">Setting</th><th className="p-2 text-left">From</th><th className="p-2 text-left">To</th></tr></thead>
            <tbody>
              {changes.map(c => (
                <tr key={c.key} className="border-t">
                  <td className="p-2">{c.key}</td>
                  <td className="p-2 text-gray-500">{c.from || '—'}</td>
                  <td className="p-2">{c.to || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={onConfirm}>Apply Changes</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}



