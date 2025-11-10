import { Virtuoso } from 'react-virtuoso'

export function VirtualizedTable<T>({ data, row, header }: { data: T[]; row: (item: T, index: number) => React.ReactNode; header: React.ReactNode; }) {
  return (
    <div className="rounded-lg border bg-white shadow-sm">
      <div className="border-b">{header}</div>
      <Virtuoso totalCount={data.length} className="h-[560px]" itemContent={(index) => row(data[index], index)} />
    </div>
  )
}



