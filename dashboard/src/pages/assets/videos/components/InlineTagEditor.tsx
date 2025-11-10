import { useEffect, useRef, useState } from 'react';
import type { VideoAsset } from '@/services/asset.service';
import { useUpdateAsset } from '@/hooks/useAssets';

export function InlineTagEditor({ asset }: { asset: VideoAsset }) {
  const [tags, setTags] = useState<string[]>(asset.tags || []);
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const update = useUpdateAsset();

  useEffect(() => {
    setTags(asset.tags || []);
  }, [asset.tags]);

  const commit = async (next: string[]) => {
    setTags(next);
    await update.mutateAsync({ id: asset.id, data: { tags: next } });
  };

  const onKeyDown = async (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && input.trim()) {
      const next = Array.from(new Set([...tags, input.trim()]));
      setInput('');
      await commit(next);
    } else if (e.key === 'Backspace' && !input && tags.length) {
      const next = tags.slice(0, -1);
      await commit(next);
    }
  };

  return (
    <div className="flex items-center flex-wrap gap-1">
      {tags.map((t) => (
        <span
          key={t}
          className="px-2 py-0.5 text-xs bg-gray-100 rounded cursor-pointer"
          onClick={async () => {
            const next = tags.filter((x) => x !== t);
            await commit(next);
          }}
        >
          {t}
        </span>
      ))}
      <input
        ref={inputRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={onKeyDown}
        className="outline-none text-xs px-1 py-0.5 min-w-[60px]"
        placeholder="Add tag"
      />
    </div>
  );
}


