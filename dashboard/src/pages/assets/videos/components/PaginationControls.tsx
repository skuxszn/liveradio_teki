interface Props {
  page: number;
  pages: number;
  onPageChange: (p: number) => void;
}

export function PaginationControls({ page, pages, onPageChange }: Props) {
  if (pages <= 1) return null;
  const prev = () => onPageChange(Math.max(1, page - 1));
  const next = () => onPageChange(Math.min(pages, page + 1));
  return (
    <div className="flex items-center justify-between py-3">
      <button className="text-sm text-gray-700" onClick={prev} disabled={page <= 1}>
        Previous
      </button>
      <div className="text-sm text-gray-600">
        Page {page} of {pages}
      </div>
      <button className="text-sm text-gray-700" onClick={next} disabled={page >= pages}>
        Next
      </button>
    </div>
  );
}


