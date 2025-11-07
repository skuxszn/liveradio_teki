/**
 * Video Assets Management page.
 * Upload, manage, and preview video loops.
 */

import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Upload, Trash2, CheckCircle2, XCircle, Play, HardDrive } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import assetService, { type VideoAsset } from '@/services/asset.service';

export default function Assets() {
  const queryClient = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragActive, setDragActive] = useState(false);

  // Fetch assets
  const { data: assets, isLoading } = useQuery({
    queryKey: ['assets'],
    queryFn: () => assetService.getAll(),
  });

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['asset-stats'],
    queryFn: () => assetService.getStats(),
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      assetService.upload(file, (progress) => setUploadProgress(progress)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['asset-stats'] });
      setUploading(false);
      setUploadProgress(0);
      alert('File uploaded successfully!');
    },
    onError: (error: any) => {
      setUploading(false);
      setUploadProgress(0);
      alert(`Upload failed: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (filename: string) => assetService.delete(filename),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['asset-stats'] });
    },
    onError: (error: any) => {
      alert(`Delete failed: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Handle file drop
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = Array.from(e.dataTransfer.files);
    const mp4Files = files.filter((f) => f.name.toLowerCase().endsWith('.mp4'));

    if (mp4Files.length > 0) {
      handleFileUpload(mp4Files[0]);
    } else {
      alert('Please drop an MP4 file');
    }
  }, []);

  // Handle drag over
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  // Handle file input change
  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileUpload(e.target.files[0]);
    }
  };

  // Handle file upload
  const handleFileUpload = (file: File) => {
    if (!file.name.toLowerCase().endsWith('.mp4')) {
      alert('Only MP4 files are allowed');
      return;
    }

    if (file.size > 100 * 1024 * 1024) {
      alert('File too large. Maximum size: 100MB');
      return;
    }

    setUploading(true);
    uploadMutation.mutate(file);
  };

  // Handle delete
  const handleDelete = (asset: VideoAsset) => {
    if (confirm(`Delete ${asset.filename}?`)) {
      deleteMutation.mutate(asset.filename);
    }
  };

  // Format file size
  const formatSize = (bytes: number | null): string => {
    if (!bytes) return 'Unknown';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  // Format duration
  const formatDuration = (seconds: number | null): string => {
    if (!seconds) return 'Unknown';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-gray-500">Loading assets...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Video Assets</h1>
        <p className="text-gray-500">Manage video loop files</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Total Assets</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_assets || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Valid</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats?.valid_assets || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Invalid</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats?.invalid_assets || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Storage</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_storage_mb.toFixed(1) || 0} MB</div>
          </CardContent>
        </Card>
      </div>

      {/* Upload Zone */}
      <Card>
        <CardHeader>
          <CardTitle>Upload Video</CardTitle>
          <CardDescription>Drop an MP4 file or click to browse (max 100MB)</CardDescription>
        </CardHeader>
        <CardContent>
          <div
            onDrop={handleDrop}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
              dragActive
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-300 hover:border-gray-400'
            }`}
            onClick={() => document.getElementById('file-input')?.click()}
          >
            <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
            <p className="text-lg font-medium mb-2">
              {dragActive ? 'Drop file here' : 'Drag & drop an MP4 file here'}
            </p>
            <p className="text-sm text-gray-500">or click to browse</p>
            <input
              id="file-input"
              type="file"
              accept=".mp4"
              className="hidden"
              onChange={handleFileInput}
              disabled={uploading}
            />
          </div>

          {uploading && (
            <div className="mt-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Uploading...</span>
                <span className="text-sm text-gray-600">{uploadProgress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Assets Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {assets?.map((asset) => (
          <Card key={asset.id} className="overflow-hidden">
            <div className="aspect-video bg-gray-900 relative flex items-center justify-center">
              <Play className="w-12 h-12 text-white opacity-50" />
              <div className="absolute top-2 right-2">
                {asset.is_valid ? (
                  <CheckCircle2 className="w-6 h-6 text-green-500" />
                ) : (
                  <XCircle className="w-6 h-6 text-red-500" />
                )}
              </div>
            </div>

            <CardContent className="p-4">
              <h3 className="font-medium truncate mb-2" title={asset.filename}>
                {asset.filename}
              </h3>

              <div className="space-y-1 text-sm text-gray-600 mb-4">
                {asset.resolution && (
                  <div className="flex items-center justify-between">
                    <span>Resolution:</span>
                    <span className="font-medium">{asset.resolution}</span>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <span>Duration:</span>
                  <span className="font-medium">{formatDuration(asset.duration)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Size:</span>
                  <span className="font-medium">{formatSize(asset.file_size)}</span>
                </div>
                {asset.video_codec && (
                  <div className="flex items-center justify-between">
                    <span>Codec:</span>
                    <span className="font-medium">{asset.video_codec}</span>
                  </div>
                )}
              </div>

              <Button
                variant="destructive"
                size="sm"
                className="w-full"
                onClick={() => handleDelete(asset)}
                disabled={deleteMutation.isPending}
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete
              </Button>
            </CardContent>
          </Card>
        ))}

        {assets?.length === 0 && (
          <div className="col-span-full">
            <Alert>
              <HardDrive className="w-4 h-4" />
              <AlertDescription>
                No video assets found. Upload an MP4 file to get started.
              </AlertDescription>
            </Alert>
          </div>
        )}
      </div>
    </div>
  );
}


