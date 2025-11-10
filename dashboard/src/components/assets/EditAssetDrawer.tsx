import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { type VideoAsset } from '@/services/asset.service';
import { useUpdateAsset } from '@/hooks/useAssets';
import { toast } from '@/components/feedback/ToastProvider';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  asset: VideoAsset | null;
}

export function EditAssetDrawer({ open, onOpenChange, asset }: Props) {
  const [filename, setFilename] = useState('');
  const [tagsInput, setTagsInput] = useState('');
  const updateMutation = useUpdateAsset();

  useEffect(() => {
    if (asset) {
      setFilename(asset.filename);
      setTagsInput((asset.tags || []).join(', '));
    }
  }, [asset]);

  const onSave = async () => {
    if (!asset) return;
    const tags = tagsInput
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    try {
      await updateMutation.mutateAsync({
        id: asset.id,
        data: { filename: filename.trim(), tags },
      });
      toast('Asset updated', 'success');
      onOpenChange(false);
    } catch (e: any) {
      toast(e?.response?.data?.detail || 'Update failed', 'error');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Asset</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="filename">Filename</Label>
            <Input
              id="filename"
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              disabled={updateMutation.isPending}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="tags">Tags (comma-separated)</Label>
            <Input
              id="tags"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
              disabled={updateMutation.isPending}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={updateMutation.isPending}>
              Cancel
            </Button>
            <Button onClick={onSave} disabled={updateMutation.isPending}>
              Save
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}



