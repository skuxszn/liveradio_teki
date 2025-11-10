import { ChevronDown, ChevronUp } from 'lucide-react';

interface Props {
  label: string;
  field: 'filename' | 'created_at' | 'file_size' | 'duration';
  activeSort: string;
  direction: 'asc' | 'desc';
  onChange: (field: 'filename' | 'created_at' | 'file_size' | 'duration') => void;
}

export function SortableHeader({ label, field, activeSort, direction, onChange }: Props) {
  const isActive = activeSort === field;
  return (
    <button
      type="button"
      onClick={() => onChange(field)}
      className={`inline-flex items-center gap-1 ${isActive ? 'text-gray-900' : 'text-gray-600'}`}
    >
      {label}
      {isActive ? (
        direction === 'asc' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />
      ) : null}
    </button>
  );
}


