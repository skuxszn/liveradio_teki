import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { assetService } from '@/services/asset.service';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  assetId: number | null;
}

export function PreviewModal({ open, onOpenChange, assetId }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl">
        <DialogHeader>
          <DialogTitle>Video Preview</DialogTitle>
        </DialogHeader>
        {assetId ? (
          <div className="space-y-4">
            <video
              src={assetService.getVideoUrlById(assetId)}
              controls
              autoPlay
              className="w-full h-[60vh] bg-black rounded"
            />
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}


