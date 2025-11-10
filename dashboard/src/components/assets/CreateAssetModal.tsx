import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useCreateAsset } from '@/hooks/useAssets';
import { toast } from '@/components/feedback/ToastProvider';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateAssetModal({ open, onOpenChange }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [tagsInput, setTagsInput] = useState<string>('');
  const [progress, setProgress] = useState<number>(0);
  const createMutation = useCreateAsset();

  const handleSubmit = async () => {
    if (!file) {
      toast('Please choose an MP4 file', 'warning');
      return;
    }
    if (!file.name.toLowerCase().endsWith('.mp4')) {
      toast('Only MP4 files are allowed', 'warning');
      return;
    }
    const tags = tagsInput
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    try {
      await createMutation.mutateAsync({ file, tags, onProgress: setProgress });
      toast('Asset uploaded', 'success');
      setFile(null);
      setTagsInput('');
      setProgress(0);
      onOpenChange(false);
    } catch (e: any) {
      toast(e?.response?.data?.detail || 'Upload failed', 'error');
      setProgress(0);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload Video Asset</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="file">MP4 File</Label>
            <Input
              id="file"
              type="file"
              accept=".mp4"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              disabled={createMutation.isPending}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="tags">Tags (comma-separated)</Label>
            <Input
              id="tags"
              placeholder="intro, promo, chill"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
              disabled={createMutation.isPending}
            />
          </div>
          {createMutation.isPending && (
            <div className="text-sm text-gray-600">Uploading... {progress}%</div>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={createMutation.isPending}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={createMutation.isPending}>
              Upload
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}



