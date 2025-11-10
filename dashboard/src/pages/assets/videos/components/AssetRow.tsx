import { Button } from '@/components/ui/button';
import { TableCell, TableRow } from '@/components/ui/table';
import { useVideoAssetsStore } from '@/store/videoAssetsStore';
import type { VideoAsset } from '@/services/asset.service';
import { useDeleteAsset } from '@/hooks/useAssets';
import { toast } from '@/components/feedback/ToastProvider';
import { HoverPreview } from './HoverPreview';
import { InlineTagEditor } from './InlineTagEditor';
import { Edit2, Trash2 } from 'lucide-react';

function formatSize(bytes?: number | null) {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatDuration(seconds?: number | null) {
  if (!seconds) return '—';
  const mins = Math.floor(seconds);
  const hh = Math.floor(mins / 3600);
  const mm = Math.floor((mins % 3600) / 60);
  const ss = Math.floor(mins % 60);
  return hh > 0 ? `${hh}:${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}` : `${mm}:${String(ss).padStart(2, '0')}`;
}

export function AssetRow({ asset }: { asset: VideoAsset }) {
  const toggleSelect = useVideoAssetsStore((s) => s.toggleSelect);
  const selectedIds = useVideoAssetsStore((s) => s.selectedIds);
  const openPreview = useVideoAssetsStore((s) => s.openPreview);
  const del = useDeleteAsset();

  return (
    <TableRow onDoubleClick={() => openPreview(asset.id)}>
      <TableCell className="w-10">
        <input
          type="checkbox"
          checked={selectedIds.has(asset.id)}
          onChange={() => toggleSelect(asset.id)}
        />
      </TableCell>
      <TableCell className="font-medium">
        <div className="relative group">
          <span className="cursor-pointer underline decoration-dotted" onMouseEnter={() => {}} onClick={() => openPreview(asset.id)}>
            {asset.filename}
          </span>
          <HoverPreview assetId={asset.id} />
        </div>
      </TableCell>
      <TableCell>{formatDuration(asset.duration)}</TableCell>
      <TableCell>{formatSize(asset.file_size)}</TableCell>
      <TableCell>{asset.created_at ? new Date(asset.created_at).toLocaleString() : '—'}</TableCell>
      <TableCell>
        <InlineTagEditor asset={asset} />
      </TableCell>
      <TableCell className="text-right space-x-2">
        <Button variant="outline" size="sm" onClick={() => openPreview(asset.id)}>
          <Edit2 className="w-4 h-4 mr-1" />
          Preview
        </Button>
        <Button
          variant="destructive"
          size="sm"
          onClick={async () => {
            try {
              await del.mutateAsync({ id: asset.id });
              toast('Deleted', 'success');
            } catch (e: any) {
              toast(e?.response?.data?.detail || 'Delete failed', 'error');
            }
          }}
        >
          <Trash2 className="w-4 h-4 mr-1" />
          Delete
        </Button>
      </TableCell>
    </TableRow>
  );
}


