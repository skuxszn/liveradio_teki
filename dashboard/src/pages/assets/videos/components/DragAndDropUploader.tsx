import { useCallback } from 'react';
import { useCreateAsset } from '@/hooks/useAssets';
import { useVideoAssetsStore } from '@/store/videoAssetsStore';
import { v4 as uuid } from 'uuid';

export function DragAndDropUploader() {
  const enqueue = useVideoAssetsStore((s) => s.enqueue);
  const updateItem = useVideoAssetsStore((s) => s.updateQueueItem);
  const create = useCreateAsset();

  const onFiles = useCallback(
    async (fileList: FileList | null) => {
      if (!fileList) return;
      const files = Array.from(fileList).filter((f) => f.name.toLowerCase().endsWith('.mp4'));
      for (const f of files) {
        const id = uuid();
        enqueue({ id, file: f, progress: 0, status: 'queued' });
        // start upload
        updateItem(id, { status: 'uploading' });
        try {
          await create.mutateAsync({
            file: f,
            onProgress: (p) => updateItem(id, { progress: p }),
          });
          updateItem(id, { progress: 100, status: 'success' });
        } catch (e: any) {
          updateItem(id, { status: 'error', error: e?.response?.data?.detail || 'Upload failed' });
        }
      }
    },
    [enqueue, updateItem, create]
  );

  return (
    <div
      className="border border-dashed rounded p-6 text-center text-sm text-gray-600 hover:bg-gray-50"
      onDragOver={(e) => {
        e.preventDefault();
      }}
      onDrop={(e) => {
        e.preventDefault();
        onFiles(e.dataTransfer.files);
      }}
    >
      Drag and drop MP4 files here or
      <label className="ml-1 underline cursor-pointer">
        choose files
        <input
          type="file"
          multiple
          accept=".mp4"
          className="hidden"
          onChange={(e) => onFiles(e.target.files)}
        />
      </label>
    </div>
  );
}


