import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { type VideoAsset } from '@/services/asset.service';
import { useAssets, useBatchDelete } from '@/hooks/useAssets';
import { useVideoAssetsStore } from '@/store/videoAssetsStore';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, Trash2 } from 'lucide-react';
import { DragAndDropUploader } from './components/DragAndDropUploader';
import { MultiUploaderQueue } from './components/MultiUploaderQueue';
import { AssetsTable } from './components/AssetsTable';
import { BatchActionsBar } from './components/BatchActionsBar';
import { PreviewModal } from './components/PreviewModal';
import { PaginationControls } from './components/PaginationControls';

export default function VideoAssetsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get('page') || '1', 10);
  const limit = parseInt(searchParams.get('limit') || '25', 10);
  const searchParam = searchParams.get('search') || '';
  const sort = (searchParams.get('sort') as 'filename' | 'created_at' | 'file_size' | 'duration') || 'created_at';
  const direction = (searchParams.get('direction') as 'asc' | 'desc') || 'desc';

  const [search, setSearch] = useState(searchParam);
  const selectedIds = useVideoAssetsStore((s) => s.selectedIds);
  const previewId = useVideoAssetsStore((s) => s.previewAssetId);
  const closePreview = useVideoAssetsStore((s) => s.closePreview);
  const clearSelection = useVideoAssetsStore((s) => s.clearSelection);
  const batchDelete = useBatchDelete();

  // Debounce search and sync URL
  useEffect(() => {
    const h = setTimeout(() => {
      const next = new URLSearchParams(searchParams);
      if (search) next.set('search', search);
      else next.delete('search');
      next.set('page', '1');
      setSearchParams(next, { replace: true });
    }, 300);
    return () => clearTimeout(h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const { data, isLoading, isFetching } = useAssets({ page, limit, search: searchParam || undefined, sort, direction });

  const items = (data?.items || []) as VideoAsset[];
  const pagination = data?.pagination || { page, limit, pages: 1, total: 0 };

  const onPageChange = (p: number) => {
    const next = new URLSearchParams(searchParams);
    next.set('page', String(p));
    next.set('limit', String(limit));
    if (searchParam) next.set('search', searchParam);
    next.set('sort', sort);
    next.set('direction', direction);
    setSearchParams(next, { replace: true });
  };

  const onSortChange = (nextSort: string) => {
    const next = new URLSearchParams(searchParams);
    if (sort === nextSort) {
      next.set('direction', direction === 'asc' ? 'desc' : 'asc');
    } else {
      next.set('sort', nextSort);
      next.set('direction', 'asc');
    }
    next.set('page', '1');
    setSearchParams(next, { replace: true });
  };

  const onBatchDelete = async () => {
    if (!selectedIds.size) return;
    await batchDelete.mutateAsync({ ids: Array.from(selectedIds) });
    clearSelection();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Video Assets</h1>
          <p className="text-gray-500">Manage MP4 loop files</p>
        </div>
        <div className="flex gap-2">
          {!!selectedIds.size && (
            <Button variant="destructive" onClick={onBatchDelete} disabled={batchDelete.isPending}>
              <Trash2 className="w-4 h-4 mr-2" />
              Delete selected ({selectedIds.size})
            </Button>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
          <Input
            placeholder="Search by filename or tags..."
            className="pl-8"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <DragAndDropUploader />
      <MultiUploaderQueue />

  <BatchActionsBar />

      <AssetsTable
        items={items}
        sort={sort}
        direction={direction}
        onSortChange={onSortChange}
        isLoading={isLoading || isFetching}
      />

      <div className="px-2">
        <PaginationControls
          page={pagination.page}
          pages={pagination.pages}
          onPageChange={onPageChange}
        />
      </div>

      <PreviewModal
        open={!!previewId}
        onOpenChange={(open) => (!open ? closePreview() : null)}
        assetId={previewId}
      />
    </div>
  );
}


