import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { useDeleteAsset } from '@/hooks/useAssets';
import { toast } from '@/components/feedback/ToastProvider';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  assetId: number | null;
  filename?: string;
}

export function DeleteAssetDialog({ open, onOpenChange, assetId, filename }: Props) {
  const deleteMutation = useDeleteAsset();

  const onConfirm = async () => {
    if (!assetId) return;
    try {
      await deleteMutation.mutateAsync({ id: assetId });
      toast('Asset deleted', 'success');
      onOpenChange(false);
    } catch (e: any) {
      toast(e?.response?.data?.detail || 'Delete failed', 'error');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete Asset</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-gray-600">Are you sure you want to delete <span className="font-medium">{filename}</span>? This cannot be undone.</p>
        <div className="flex justify-end gap-2 pt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={deleteMutation.isPending}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={onConfirm} disabled={deleteMutation.isPending}>
            Delete
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}



