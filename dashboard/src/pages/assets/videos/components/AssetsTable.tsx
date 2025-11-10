import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useVideoAssetsStore } from '@/store/videoAssetsStore';
import type { VideoAsset } from '@/services/asset.service';
import { SortableHeader } from './SortableHeader';
import { AssetRow } from './AssetRow';

interface Props {
  items: VideoAsset[];
  sort: 'filename' | 'created_at' | 'file_size' | 'duration';
  direction: 'asc' | 'desc';
  onSortChange: (field: 'filename' | 'created_at' | 'file_size' | 'duration') => void;
  isLoading?: boolean;
}

export function AssetsTable({ items, sort, direction, onSortChange, isLoading }: Props) {
  const selectedIds = useVideoAssetsStore((s) => s.selectedIds);
  const clearSelection = useVideoAssetsStore((s) => s.clearSelection);
  const selectAll = useVideoAssetsStore((s) => s.selectAll);
  const allIds = items.map((i) => i.id);
  const allSelected = allIds.length > 0 && allIds.every((id) => selectedIds.has(id));

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-10">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={(e) => (e.target.checked ? selectAll(allIds) : clearSelection())}
              />
            </TableHead>
            <TableHead>
              <SortableHeader field="filename" label="Filename" activeSort={sort} direction={direction} onChange={onSortChange} />
            </TableHead>
            <TableHead>
              <SortableHeader field="duration" label="Duration" activeSort={sort} direction={direction} onChange={onSortChange} />
            </TableHead>
            <TableHead>
              <SortableHeader field="file_size" label="Size" activeSort={sort} direction={direction} onChange={onSortChange} />
            </TableHead>
            <TableHead>
              <SortableHeader field="created_at" label="Created" activeSort={sort} direction={direction} onChange={onSortChange} />
            </TableHead>
            <TableHead>Tags</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((a) => (
            <AssetRow key={a.id} asset={a} />
          ))}
          {!items.length && !isLoading && (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-sm text-gray-600 py-8">
                No assets found
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}


