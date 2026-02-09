import { cn } from '@/lib/utils';

type BrandLogoProps = {
  className?: string;
  labelClassName?: string;
  size?: 'sm' | 'md';
};

export function BrandLogo({ className, labelClassName, size = 'md' }: BrandLogoProps) {
  const isSmall = size === 'sm';

  return (
    <div className={cn('inline-flex items-center gap-2', className)}>
      <div
        className={cn(
          'relative isolate overflow-hidden border border-indigo-400/35 bg-zinc-900 shadow-[0_0_18px_rgba(99,102,241,0.22)] transition-all duration-300 group-hover:-translate-y-0.5 group-hover:border-indigo-300/60',
          isSmall ? 'h-7 w-7 rounded-lg' : 'h-8 w-8 rounded-xl'
        )}
      >
        <span className="absolute inset-0 bg-[radial-gradient(circle_at_30%_22%,rgba(129,140,248,0.35),rgba(24,24,27,0.2)_52%),linear-gradient(150deg,rgba(99,102,241,0.22),rgba(24,24,27,0.05))]" />
        <span
          className={cn(
            'absolute rounded-[inherit] border border-white/10',
            isSmall ? 'inset-[3px]' : 'inset-[4px]'
          )}
        />
        <span
          className={cn(
            'absolute rounded-full bg-emerald-300/90 shadow-[0_0_8px_rgba(110,231,183,0.85)]',
            isSmall ? 'right-[4px] top-[4px] h-[3px] w-[3px]' : 'right-[5px] top-[5px] h-[3px] w-[3px]'
          )}
        />
        <span
          className={cn(
            'absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 font-semibold leading-none text-indigo-100 tracking-[0.02em]',
            isSmall ? 'text-[9px]' : 'text-[10px]'
          )}
        >
          CQ
        </span>
      </div>
      <span
        className={cn(
          'font-semibold tracking-tight text-white transition-colors',
          isSmall ? 'text-sm' : 'text-base',
          labelClassName
        )}
      >
        CodebaseQA
      </span>
    </div>
  );
}
