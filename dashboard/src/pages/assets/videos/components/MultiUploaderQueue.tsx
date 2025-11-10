import { useVideoAssetsStore } from '@/store/videoAssetsStore';

export function MultiUploaderQueue() {
  const queue = useVideoAssetsStore((s) => s.uploadQueue);
  if (!queue.length) return null;
  return (
    <div className="space-y-2">
      {queue.map((it) => (
        <div key={it.id} className="flex items-center gap-3 text-sm">
          <div className="flex-1 truncate">{it.file.name}</div>
          <div className="w-48 bg-gray-200 rounded h-2 overflow-hidden">
            <div
              className={`h-2 ${it.status === 'error' ? 'bg-red-500' : 'bg-blue-500'}`}
              style={{ width: `${it.progress}%` }}
            />
          </div>
          <div className="w-20 text-right">
            {it.status === 'uploading' && `${it.progress}%`}
            {it.status === 'success' && 'Done'}
            {it.status === 'error' && 'Error'}
            {it.status === 'queued' && 'Queued'}
          </div>
        </div>
      ))}
    </div>
  );
}


