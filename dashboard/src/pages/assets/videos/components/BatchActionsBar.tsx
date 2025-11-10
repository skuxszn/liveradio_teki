import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useBatchDelete, useBatchTags, useBatchUpdate } from '@/hooks/useAssets';
import { useVideoAssetsStore } from '@/store/videoAssetsStore';
import { toast } from '@/components/feedback/ToastProvider';

export function BatchActionsBar() {
  const selectedIds = useVideoAssetsStore((s) => s.selectedIds);
  const clearSelection = useVideoAssetsStore((s) => s.clearSelection);
  const [prefix, setPrefix] = useState('');
  const [suffix, setSuffix] = useState('');
  const [tagInput, setTagInput] = useState('');
  const [force, setForce] = useState(false);
  const del = useBatchDelete();
  const upd = useBatchUpdate();
  const tags = useBatchTags();

  if (!selectedIds.size) return null;
  const ids = Array.from(selectedIds);

  return (
    <div className="flex flex-wrap items-center gap-2 rounded border p-3">
      <div className="text-sm">Selected: {ids.length}</div>
      <label className="text-xs flex items-center gap-1">
        <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} />
        Force
      </label>
      <Button
        variant="destructive"
        size="sm"
        onClick={async () => {
          try {
            const res = await del.mutateAsync({ ids, force });
            const ok = res?.results?.filter((r: any) => r.success).length ?? 0;
            const fail = res?.results?.length ? res.results.length - ok : 0;
            toast(`Deleted ${ok}${fail ? `, failed ${fail}` : ''}`, fail ? 'warning' : 'success');
            clearSelection();
          } catch (e: any) {
            toast(e?.response?.data?.detail || 'Batch delete failed', 'error');
          }
        }}
        disabled={del.isPending}
      >
        Delete
      </Button>
      <div className="flex items-center gap-1">
        <input
          className="border rounded px-2 py-1 text-sm"
          placeholder="prefix_"
          value={prefix}
          onChange={(e) => setPrefix(e.target.value)}
        />
        <input
          className="border rounded px-2 py-1 text-sm"
          placeholder="_suffix"
          value={suffix}
          onChange={(e) => setSuffix(e.target.value)}
        />
        <Button
          size="sm"
          onClick={async () => {
            await upd.mutateAsync({ ids, filename_prefix: prefix || undefined, filename_suffix: suffix || undefined });
            setPrefix('');
            setSuffix('');
          }}
        >
          Apply rename
        </Button>
      </div>
      <div className="flex items-center gap-1">
        <input
          className="border rounded px-2 py-1 text-sm"
          placeholder="tag1, tag2"
          value={tagInput}
          onChange={(e) => setTagInput(e.target.value)}
        />
        <Button
          size="sm"
          onClick={async () => {
            const items = tagInput.split(',').map((t) => t.trim()).filter(Boolean);
            await tags.mutateAsync({ ids, add: items });
            setTagInput('');
          }}
        >
          Add tags
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={async () => {
            const items = tagInput.split(',').map((t) => t.trim()).filter(Boolean);
            await tags.mutateAsync({ ids, remove: items });
            setTagInput('');
          }}
        >
          Remove tags
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onClick={async () => {
            const items = tagInput.split(',').map((t) => t.trim()).filter(Boolean);
            await tags.mutateAsync({ ids, replace: items });
            setTagInput('');
          }}
        >
          Replace tags
        </Button>
      </div>
      <Button size="sm" variant="ghost" onClick={() => clearSelection()}>
        Clear
      </Button>
    </div>
  );
}


