import * as SwitchPr from '@radix-ui/react-switch'
import { cn } from '@/utils/cn'

export function Switch({ checked, onCheckedChange, className }: { checked: boolean; onCheckedChange: (v: boolean) => void; className?: string }) {
  return (
    <SwitchPr.Root checked={checked} onCheckedChange={onCheckedChange} className={cn('w-10 h-6 bg-gray-300 data-[state=checked]:bg-blue-600 rounded-full relative transition-colors', className)}>
      <SwitchPr.Thumb className="block w-5 h-5 bg-white rounded-full translate-x-0.5 data-[state=checked]:translate-x-4.5 transition-transform will-change-transform" />
    </SwitchPr.Root>
  )
}


