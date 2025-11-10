import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAssets } from '@/hooks/useAssets';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Plus, Search, Edit2, Trash2 } from 'lucide-react';
import { PaginationControls } from '@/components/common/PaginationControls';
import { CreateAssetModal } from '@/components/assets/CreateAssetModal';
import { EditAssetDrawer } from '@/components/assets/EditAssetDrawer';
import { DeleteAssetDialog } from '@/components/assets/DeleteAssetDialog';
import { type VideoAsset } from '@/services/asset.service';

export default function VideoAssetsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const pageParam = parseInt(searchParams.get('page') || '1', 10);
  const limitParam = parseInt(searchParams.get('limit') || '25', 10);
  const searchParam = searchParams.get('search') || '';

  const [search, setSearch] = useState(searchParam);
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [selected, setSelected] = useState<VideoAsset | null>(null);

  // Debounce search
  useEffect(() => {
    const h = setTimeout(() => {
      const next = new URLSearchParams(searchParams);
      if (search) next.set('search', search);
      else next.delete('search');
      next.set('page', '1'); // reset page
      setSearchParams(next, { replace: true });
    }, 300);
    return () => clearTimeout(h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const { data, isLoading, isFetching } = useAssets({
    page: pageParam,
    limit: limitParam,
    search: searchParam || undefined,
  });

  const items = (data?.items || []) as VideoAsset[];
  const pagination = data?.pagination || { page: pageParam, limit: limitParam, pages: 1, total: 0 };

  const onPageChange = (p: number) => {
    const next = new URLSearchParams(searchParams);
    next.set('page', String(p));
    next.set('limit', String(limitParam));
    if (searchParam) next.set('search', searchParam);
    setSearchParams(next, { replace: true });
  };

  const formatSize = (bytes?: number | null) => {
    if (!bytes) return '—';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  const formatDuration = (seconds?: number | null) => {
    if (!seconds) return '—';
    const mins = Math.floor(seconds);
    const hh = Math.floor(mins / 3600);
    const mm = Math.floor((mins % 3600) / 60);
    const ss = Math.floor(mins % 60);
    return hh > 0 ? `${hh}:${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}` : `${mm}:${String(ss).padStart(2, '0')}`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Video Assets</h1>
          <p className="text-gray-500">Manage video loop files</p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Upload
        </Button>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Search</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
              <Input
                placeholder="Search by filename or tag..."
                className="pl-8"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Filename</TableHead>
              <TableHead>Duration</TableHead>
              <TableHead>Size</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Tags</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((a: VideoAsset) => (
              <TableRow key={a.id}>
                <TableCell className="font-medium">{a.filename}</TableCell>
                <TableCell>{formatDuration(a.duration)}</TableCell>
                <TableCell>{formatSize(a.file_size)}</TableCell>
                <TableCell>{a.created_at ? new Date(a.created_at).toLocaleString() : '—'}</TableCell>
                <TableCell>
                  {(a.tags || []).length ? (
                    <div className="flex flex-wrap gap-1">
                      {(a.tags || []).map((t: string) => (
                        <span key={t} className="px-2 py-0.5 text-xs bg-gray-100 rounded">{t}</span>
                      ))}
                    </div>
                  ) : (
                    '—'
                  )}
                </TableCell>
                <TableCell className="text-right space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSelected(a);
                      setEditOpen(true);
                    }}
                  >
                    <Edit2 className="w-4 h-4 mr-1" />
                    Edit
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => {
                      setSelected(a);
                      setDeleteOpen(true);
                    }}
                  >
                    <Trash2 className="w-4 h-4 mr-1" />
                    Delete
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {!items.length && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-sm text-gray-600 py-8">
                  {isLoading || isFetching ? 'Loading...' : 'No assets found'}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        <div className="px-4">
          <PaginationControls
            page={pagination.page}
            pages={pagination.pages}
            onPageChange={onPageChange}
          />
        </div>
      </div>

      <CreateAssetModal open={createOpen} onOpenChange={setCreateOpen} />
      <EditAssetDrawer open={editOpen} onOpenChange={setEditOpen} asset={selected} />
      <DeleteAssetDialog open={deleteOpen} onOpenChange={setDeleteOpen} assetId={selected?.id || null} filename={selected?.filename} />
    </div>
  );
}


