import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Props {
  page: number;
  pages: number;
  onPageChange: (page: number) => void;
}

export function PaginationControls({ page, pages, onPageChange }: Props) {
  const prevDisabled = page <= 1;
  const nextDisabled = page >= pages;
  return (
    <div className="flex items-center justify-between gap-2 py-2">
      <div className="text-sm text-gray-600">
        Page <span className="font-medium">{page}</span> of <span className="font-medium">{pages || 1}</span>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" disabled={prevDisabled} onClick={() => onPageChange(page - 1)}>
          <ChevronLeft className="w-4 h-4 mr-1" /> Prev
        </Button>
        <Button variant="outline" size="sm" disabled={nextDisabled} onClick={() => onPageChange(page + 1)}>
          Next <ChevronRight className="w-4 h-4 ml-1" />
        </Button>
      </div>
    </div>
  );
}



