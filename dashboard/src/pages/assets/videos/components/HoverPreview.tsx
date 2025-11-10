import { useEffect, useRef, useState } from 'react';
import { assetService } from '@/services/asset.service';

export function HoverPreview({ assetId }: { assetId: number }) {
  const [visible, setVisible] = useState(false);
  const [pos, setPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current?.parentElement;
    if (!el) return;
    const onEnter = (e: MouseEvent) => {
      setVisible(true);
      setPos({ x: e.clientX + 12, y: e.clientY + 12 });
    };
    const onMove = (e: MouseEvent) => {
      setPos({ x: e.clientX + 12, y: e.clientY + 12 });
    };
    const onLeave = () => setVisible(false);
    el.addEventListener('mouseenter', onEnter);
    el.addEventListener('mousemove', onMove);
    el.addEventListener('mouseleave', onLeave);
    return () => {
      el.removeEventListener('mouseenter', onEnter);
      el.removeEventListener('mousemove', onMove);
      el.removeEventListener('mouseleave', onLeave);
    };
  }, []);

  return (
    <div ref={containerRef}>
      {visible && (
        <div
          className="fixed z-50 rounded border bg-black/70"
          style={{ left: pos.x, top: pos.y, width: 240, height: 135 }}
        >
          <video
            src={assetService.getVideoUrlById(assetId)}
            muted
            autoPlay
            loop
            playsInline
            className="w-full h-full object-cover rounded"
          />
        </div>
      )}
    </div>
  );
}


