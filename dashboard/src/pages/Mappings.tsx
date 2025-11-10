/**
 * Track Mappings Management page.
 * CRUD interface for track-to-video mappings.
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Search, Upload, Download, Trash2, Edit, ChevronsUpDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { BulkActionToolbar } from '@/components/mappings/BulkActionToolbar';
import { ConfirmDialog } from '@/components/feedback/ConfirmDialog';
import { useViewsStore } from '@/store/viewsStore';
import mappingService, { type TrackMapping, type MappingCreateData } from '@/services/mapping.service';
import assetService from '@/services/asset.service';
import { TableSkeleton } from '@/components/skeletons/TableSkeleton';
import { toast } from '@/components/feedback/ToastProvider';
import { QueryError } from '@/components/common/QueryError';

export default function Mappings() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [selectedMappings, setSelectedMappings] = useState<number[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [editingMapping, setEditingMapping] = useState<TrackMapping | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  const [confirmBulkOpen, setConfirmBulkOpen] = useState(false);
  const { views, saveView } = useViewsStore();
  const [newViewName, setNewViewName] = useState('');
  const [formData, setFormData] = useState<MappingCreateData>({
    artist: '',
    title: '',
    filename: '',
    azuracast_song_id: '',
    notes: '',
  });
  // Asset search (typeahead)
  const [assetQuery, setAssetQuery] = useState('');
  const [assetPage, setAssetPage] = useState(1);
  const [comboOpen, setComboOpen] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(0);
  const { data: assetSearch } = useQuery({
    queryKey: ['asset-search', assetQuery, assetPage],
    queryFn: () => assetService.search(assetQuery, assetPage, 20),
    enabled: assetQuery.length >= 1,
  });
  const [importFile, setImportFile] = useState<File | null>(null);

  // Fetch mappings
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['mappings', page, search],
    queryFn: () => mappingService.getAll({ page, limit: 50, search }),
  });

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['mapping-stats'],
    queryFn: () => mappingService.getStats(),
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: MappingCreateData) => mappingService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
      queryClient.invalidateQueries({ queryKey: ['mapping-stats'] });
      setDialogOpen(false);
      resetForm();
      toast('Mapping created successfully!', 'success');
    },
    onError: (error: any) => {
      toast(`Failed to create mapping: ${error.response?.data?.detail || error.message}`, 'error');
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: MappingCreateData }) =>
      mappingService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
      setDialogOpen(false);
      setEditingMapping(null);
      resetForm();
      toast('Mapping updated successfully!', 'success');
    },
    onError: (error: any) => {
      toast(`Failed to update mapping: ${error.response?.data?.detail || error.message}`, 'error');
    },
  });

  // Delete mutation with optimistic update
  const deleteMutation = useMutation({
    mutationFn: (id: number) => mappingService.delete(id),
    onMutate: async (id: number) => {
      await queryClient.cancelQueries({ queryKey: ['mappings', page, search] })
      const prev = queryClient.getQueryData<any>(['mappings', page, search])
      const next = prev ? { ...prev, mappings: prev.mappings.filter((m: any) => m.id !== id) } : prev
      if (next) queryClient.setQueryData(['mappings', page, search], next)
      return { prev }
    },
    onError: (error: any, _id, context) => {
      if (context?.prev) queryClient.setQueryData(['mappings', page, search], context.prev)
      toast(`Failed to delete mapping: ${error.response?.data?.detail || error.message}`, 'error')
    },
    onSuccess: () => {
      toast('Mapping deleted', 'success')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['mappings'] })
      queryClient.invalidateQueries({ queryKey: ['mapping-stats'] })
    },
  });

  // Bulk import mutation
  const importMutation = useMutation({
    mutationFn: (file: File) => mappingService.bulkImport(file),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
      queryClient.invalidateQueries({ queryKey: ['mapping-stats'] });
      setImportDialogOpen(false);
      setImportFile(null);
      toast(`Import complete: ${result.imported_count} imported, ${result.error_count} errors`, result.error_count ? 'warning' : 'success');
    },
    onError: (error: any) => {
      toast(`Import failed: ${error.response?.data?.detail || error.message}`, 'error');
    },
  });

  // Bulk delete mutation
  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: number[]) => mappingService.bulkDelete(ids),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
      queryClient.invalidateQueries({ queryKey: ['mapping-stats'] });
      setSelectedMappings([]);
      alert(`Deleted ${result.deleted_count} mappings`);
    },
  });

  const resetForm = () => {
    setFormData({
      artist: '',
      title: '',
      filename: '',
      azuracast_song_id: '',
      notes: '',
    });
  };

  const handleAdd = () => {
    setEditingMapping(null);
    resetForm();
    setDialogOpen(true);
  };

  const handleEdit = (mapping: TrackMapping) => {
    setEditingMapping(mapping);
    setFormData({
      artist: mapping.artist,
      title: mapping.title,
      filename: mapping.filename,
      azuracast_song_id: mapping.azuracast_song_id || '',
      notes: mapping.notes || '',
    });
    setDialogOpen(true);
  };

  const handleDelete = (id: number) => {
    setConfirmDeleteId(id);
  };

  const handleSave = () => {
    if (!formData.artist || !formData.title || !formData.filename) {
      alert('Artist, Title, and Video Loop are required');
      return;
    }

    if (editingMapping) {
      updateMutation.mutate({ id: editingMapping.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleBulkDelete = () => {
    if (selectedMappings.length === 0) {
      toast('No mappings selected', 'warning');
      return;
    }
    setConfirmBulkOpen(true);
  };

  const handleImport = () => {
    if (!importFile) { toast('Please select a file', 'warning'); return; }
    importMutation.mutate(importFile);
  };

  const handleExport = async () => {
    try {
      const result = await mappingService.export();
      const blob = new Blob([result.csv_data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `mappings-${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (error: any) {
      toast(`Export failed: ${error.message}`, 'error');
    }
  };

  const toggleSelection = (id: number) => {
    setSelectedMappings((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  if (isLoading) { return <TableSkeleton rows={10} /> }

  return (
    <div className="space-y-6">
      {error && (
        <QueryError message={(error as any)?.message} onRetry={() => refetch()} />
      )}
      <ConfirmDialog
        open={confirmDeleteId !== null}
        onOpenChange={(o) => { if (!o) setConfirmDeleteId(null) }}
        title="Delete mapping"
        description="This action cannot be undone."
        variant="destructive"
        confirmText="Delete"
        onConfirm={() => { if (confirmDeleteId !== null) { deleteMutation.mutate(confirmDeleteId); setConfirmDeleteId(null) } }}
      />
      <ConfirmDialog
        open={confirmBulkOpen}
        onOpenChange={setConfirmBulkOpen}
        title="Delete selected mappings"
        description={`Delete ${selectedMappings.length} selected mappings? This cannot be undone.`}
        variant="destructive"
        confirmText="Delete"
        onConfirm={() => { bulkDeleteMutation.mutate(selectedMappings); setConfirmBulkOpen(false) }}
      />
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Track Mappings</h1>
          <p className="text-gray-500">Manage track-to-video mappings</p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2">
            <select
              aria-label="Saved views"
              className="h-10 border rounded px-2 text-sm"
              onChange={(e) => {
                const v = views.find(v => v.id === e.target.value)
                if (v) { setSearch(v.params.search || ''); setPage(v.params.page || 1) }
              }}
            >
              <option value="">Saved views…</option>
              {views.map((v) => (
                <option key={v.id} value={v.id}>{v.name}</option>
              ))}
            </select>
            <input
              aria-label="New view name"
              value={newViewName}
              onChange={(e) => setNewViewName(e.target.value)}
              placeholder="View name"
              className="h-10 border rounded px-2 text-sm"
            />
            <Button variant="outline" onClick={() => { if (newViewName.trim()) { saveView(newViewName.trim(), { search, page }); setNewViewName(''); toast('View saved', 'success') } }}>
              Save View
            </Button>
          </div>
          <Button variant="outline" onClick={() => setImportDialogOpen(true)}>
            <Upload className="w-4 h-4 mr-2" />
            Import
          </Button>
          <Button variant="outline" onClick={handleExport}>
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
          <Button onClick={handleAdd}>
            <Plus className="w-4 h-4 mr-2" />
            Add Mapping
          </Button>
        </div>
      </div>

      <BulkActionToolbar count={selectedMappings.length} onDelete={handleBulkDelete} />

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Total Mappings</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_mappings || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Most Played</CardTitle>
          </CardHeader>
          <CardContent>
            {stats?.most_played?.[0] ? (
              <div className="text-sm">
                <div className="font-medium truncate">
                  {stats.most_played[0].artist} - {stats.most_played[0].title}
                </div>
                <div className="text-gray-500">{stats.most_played[0].play_count} plays</div>
              </div>
            ) : (
              <div className="text-sm text-gray-500">No data</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Selected</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{selectedMappings.length}</div>
            {selectedMappings.length > 0 && (
              <Button
                variant="destructive"
                size="sm"
                className="mt-2"
                onClick={handleBulkDelete}
              >
                <Trash2 className="w-4 h-4 mr-1" />
                Delete Selected
              </Button>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            placeholder="Search artist or title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">
                  <input
                    type="checkbox"
                    checked={
                      selectedMappings.length === data?.mappings.length &&
                      data?.mappings.length > 0
                    }
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedMappings(data?.mappings.map((m) => m.id) || []);
                      } else {
                        setSelectedMappings([]);
                      }
                    }}
                    aria-label="Select all"
                    className="w-5 h-5"
                  />
                </TableHead>
                <TableHead>Artist</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Video Loop</TableHead>
                <TableHead className="text-right">Play Count</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.mappings.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                    No mappings found. Click "Add Mapping" to create one.
                  </TableCell>
                </TableRow>
              ) : (
                data?.mappings.map((mapping) => (
                  <TableRow key={mapping.id}>
                    <TableCell>
                      <input
                        type="checkbox"
                        checked={selectedMappings.includes(mapping.id)}
                        onChange={() => toggleSelection(mapping.id)}
                        aria-label={`Select ${mapping.artist} - ${mapping.title}`}
                        className="w-5 h-5"
                      />
                    </TableCell>
                    <TableCell className="font-medium">{mapping.artist}</TableCell>
                    <TableCell>{mapping.title}</TableCell>
                    <TableCell className="text-sm text-gray-600">
                      {mapping.filename}
                    </TableCell>
                    <TableCell className="text-right">{mapping.play_count}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          aria-label={`Edit mapping ${mapping.artist} - ${mapping.title}`}
                          onClick={() => handleEdit(mapping)}
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          aria-label={`Delete mapping ${mapping.artist} - ${mapping.title}`}
                          onClick={() => handleDelete(mapping.id)}
                        >
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Pagination */}
      {data && data.pagination.pages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            Previous
          </Button>
          <span className="text-sm text-gray-600">
            Page {page} of {data.pagination.pages}
          </span>
          <Button
            variant="outline"
            onClick={() => setPage((p) => Math.min(data.pagination.pages, p + 1))}
            disabled={page === data.pagination.pages}
          >
            Next
          </Button>
        </div>
      )}

      {/* Add/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingMapping ? 'Edit Mapping' : 'Add New Mapping'}
            </DialogTitle>
            <DialogDescription>
              Map a track to a video loop file.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label htmlFor="artist">Artist *</Label>
              <Input
                id="artist"
                value={formData.artist}
                onChange={(e) => setFormData({ ...formData, artist: e.target.value })}
                placeholder="Artist name"
              />
            </div>

            <div>
              <Label htmlFor="title">Title *</Label>
              <Input
                id="title"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="Track title"
              />
            </div>

            <div className="relative">
              <Label htmlFor="filename">Video Loop *</Label>
              <Input
                id="filename"
                value={formData.filename}
                onChange={(e) => {
                  const v = e.target.value;
                  setFormData({ ...formData, filename: v });
                  setAssetQuery(v);
                  setAssetPage(1);
                  setComboOpen(true);
                  setHighlightIndex(0);
                }}
                placeholder="Type to search…"
                role="combobox"
                aria-expanded={comboOpen}
                aria-controls="asset-combobox-list"
                onFocus={() => setComboOpen(true)}
                onKeyDown={(e) => {
                  if (!assetSearch?.results?.length) return;
                  if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    setComboOpen(true);
                    setHighlightIndex((i) => Math.min(i + 1, assetSearch.results.length - 1));
                  } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    setHighlightIndex((i) => Math.max(i - 1, 0));
                  } else if (e.key === 'Enter' && comboOpen) {
                    e.preventDefault();
                    const pick = assetSearch.results[highlightIndex];
                    if (pick) {
                      setFormData({ ...formData, filename: pick.filename });
                      setComboOpen(false);
                    }
                  } else if (e.key === 'Escape') {
                    setComboOpen(false);
                  }
                }}
              />
              <button
                type="button"
                aria-label="Toggle assets"
                className="absolute right-2 top-8 text-gray-500 hover:text-gray-700"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => setComboOpen((o) => !o)}
              >
                <ChevronsUpDown className="w-4 h-4" />
              </button>
              {comboOpen && assetSearch?.results && (
                <div id="asset-combobox-list" role="listbox" className="absolute z-10 mt-1 w-full max-h-56 overflow-auto rounded border bg-white shadow">
                  {assetSearch.results.length === 0 && (
                    <div className="p-2 text-sm text-gray-500">No matches</div>
                  )}
                  {assetSearch.results.map((r, idx) => (
                    <button
                      key={r.id}
                      type="button"
                      className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-100 ${idx === highlightIndex ? 'bg-gray-100' : ''}`}
                      role="option"
                      aria-selected={idx === highlightIndex}
                      onMouseEnter={() => setHighlightIndex(idx)}
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => { setFormData({ ...formData, filename: r.filename }); setComboOpen(false); }}
                    >
                      <span className="font-mono">{r.filename}</span>
                      {!r.is_valid && <span className="text-red-500 ml-2">(invalid)</span>}
                    </button>
                  ))}
                  {assetSearch.pagination && assetSearch.pagination.pages > 1 && (
                    <div className="flex items-center justify-between px-2 py-1 border-t bg-gray-50">
                      <Button variant="outline" size="sm" onClick={() => setAssetPage(Math.max(1, assetPage - 1))} disabled={assetPage === 1}>
                        Prev
                      </Button>
                      <div className="text-xs text-gray-600">
                        Page {assetPage} of {assetSearch.pagination.pages}
                      </div>
                      <Button variant="outline" size="sm" onClick={() => setAssetPage(Math.min(assetSearch.pagination.pages, assetPage + 1))} disabled={assetPage === assetSearch.pagination.pages}>
                        Next
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div>
              <Label htmlFor="azuracast_song_id">AzuraCast Song ID</Label>
              <Input
                id="azuracast_song_id"
                value={formData.azuracast_song_id}
                onChange={(e) =>
                  setFormData({ ...formData, azuracast_song_id: e.target.value })
                }
                placeholder="Optional"
              />
            </div>

            <div>
              <Label htmlFor="notes">Notes</Label>
              <Input
                id="notes"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Optional notes"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {createMutation.isPending || updateMutation.isPending ? 'Saving...' : 'Save'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Import Dialog */}
      <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Import Mappings</DialogTitle>
            <DialogDescription>
              Upload a CSV or JSON file to import multiple mappings at once.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label htmlFor="import-file">File (CSV or JSON)</Label>
              <Input
                id="import-file"
                type="file"
                accept=".csv,.json"
                onChange={(e) => setImportFile(e.target.files?.[0] || null)}
              />
            </div>

            <div className="text-sm text-gray-600">
              <p className="font-medium mb-1">CSV Format:</p>
              <code className="block bg-gray-50 p-2 rounded text-xs">
                artist,title,filename,azuracast_song_id,notes
              </code>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setImportDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleImport} disabled={!importFile || importMutation.isPending}>
              {importMutation.isPending ? 'Importing...' : 'Import'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

