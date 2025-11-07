/**
 * Track Mappings Management page.
 * CRUD interface for track-to-video mappings.
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Search, Upload, Download, Trash2, Edit } from 'lucide-react';
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
import mappingService, { type TrackMapping, type MappingCreateData } from '@/services/mapping.service';

export default function Mappings() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [selectedMappings, setSelectedMappings] = useState<number[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [editingMapping, setEditingMapping] = useState<TrackMapping | null>(null);
  const [formData, setFormData] = useState<MappingCreateData>({
    artist: '',
    title: '',
    video_loop: '',
    azuracast_song_id: '',
    notes: '',
  });
  const [importFile, setImportFile] = useState<File | null>(null);

  // Fetch mappings
  const { data, isLoading } = useQuery({
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
      alert('Mapping created successfully!');
    },
    onError: (error: any) => {
      alert(`Failed to create mapping: ${error.response?.data?.detail || error.message}`);
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
      alert('Mapping updated successfully!');
    },
    onError: (error: any) => {
      alert(`Failed to update mapping: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => mappingService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
      queryClient.invalidateQueries({ queryKey: ['mapping-stats'] });
    },
    onError: (error: any) => {
      alert(`Failed to delete mapping: ${error.response?.data?.detail || error.message}`);
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
      alert(
        `Import complete!\nImported: ${result.imported_count}\nErrors: ${result.error_count}`
      );
    },
    onError: (error: any) => {
      alert(`Import failed: ${error.response?.data?.detail || error.message}`);
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
      video_loop: '',
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
      video_loop: mapping.video_loop,
      azuracast_song_id: mapping.azuracast_song_id || '',
      notes: mapping.notes || '',
    });
    setDialogOpen(true);
  };

  const handleDelete = (id: number) => {
    if (confirm('Are you sure you want to delete this mapping?')) {
      deleteMutation.mutate(id);
    }
  };

  const handleSave = () => {
    if (!formData.artist || !formData.title || !formData.video_loop) {
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
      alert('No mappings selected');
      return;
    }

    if (confirm(`Delete ${selectedMappings.length} selected mappings?`)) {
      bulkDeleteMutation.mutate(selectedMappings);
    }
  };

  const handleImport = () => {
    if (!importFile) {
      alert('Please select a file');
      return;
    }

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
      alert(`Export failed: ${error.message}`);
    }
  };

  const toggleSelection = (id: number) => {
    setSelectedMappings((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-gray-500">Loading mappings...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Track Mappings</h1>
          <p className="text-gray-500">Manage track-to-video mappings</p>
        </div>

        <div className="flex items-center gap-2">
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
                    className="w-4 h-4"
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
                        className="w-4 h-4"
                      />
                    </TableCell>
                    <TableCell className="font-medium">{mapping.artist}</TableCell>
                    <TableCell>{mapping.title}</TableCell>
                    <TableCell className="text-sm text-gray-600">
                      {mapping.video_loop}
                    </TableCell>
                    <TableCell className="text-right">{mapping.play_count}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(mapping)}
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
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

            <div>
              <Label htmlFor="video_loop">Video Loop *</Label>
              <Input
                id="video_loop"
                value={formData.video_loop}
                onChange={(e) => setFormData({ ...formData, video_loop: e.target.value })}
                placeholder="video.mp4"
              />
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
                artist,title,video_loop,azuracast_song_id,notes
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

