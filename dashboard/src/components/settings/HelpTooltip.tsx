export function HelpTooltip({ text }: { text: string }) {
  return (
    <span
      title={text}
      aria-label="Help"
      className="inline-flex items-center justify-center w-4 h-4 rounded-full text-gray-500 cursor-help select-none border border-gray-300 text-[10px]"
    >
      ?
    </span>
  )
}



