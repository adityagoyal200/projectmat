import { useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

import { cn } from '@/lib/utils';

interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  wrapperClassName?: string;
  panelClassName?: string;
}

const MARGIN = 8;

export function Tooltip({ content, children, wrapperClassName, panelClassName }: TooltipProps) {
  const [open, setOpen] = useState(false);
  const [style, setStyle] = useState<CSSProperties>({ visibility: 'hidden' });
  const triggerRef = useRef<HTMLSpanElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    if (!open) return;

    const reposition = () => {
      const trigger = triggerRef.current;
      const panel = panelRef.current;
      if (!trigger || !panel) return;

      const triggerRect = trigger.getBoundingClientRect();
      const panelRect = panel.getBoundingClientRect();

      let left = triggerRect.left;
      left = Math.min(left, window.innerWidth - panelRect.width - MARGIN);
      left = Math.max(MARGIN, left);

      const spaceBelow = window.innerHeight - triggerRect.bottom;
      const fitsBelow = spaceBelow >= panelRect.height + MARGIN;
      const top = fitsBelow
        ? triggerRect.bottom + MARGIN
        : Math.max(MARGIN, triggerRect.top - panelRect.height - MARGIN);

      setStyle({ position: 'fixed', top, left, visibility: 'visible' });
    };

    reposition();
    window.addEventListener('scroll', reposition, true);
    window.addEventListener('resize', reposition);
    return () => {
      window.removeEventListener('scroll', reposition, true);
      window.removeEventListener('resize', reposition);
    };
  }, [open]);

  const close = () => {
    setOpen(false);
    setStyle({ visibility: 'hidden' });
  };

  return (
    <>
      <span
        ref={triggerRef}
        className={cn('group', wrapperClassName)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={close}
        onFocus={() => setOpen(true)}
        onBlur={close}
      >
        {children}
      </span>
      {open &&
        createPortal(
          <div
            ref={panelRef}
            style={style}
            className={cn(
              'pointer-events-none z-[100] w-72 rounded-lg border border-white/10 bg-black/95 p-3 text-[11px] font-normal leading-relaxed text-neutral-200 shadow-xl backdrop-blur-md',
              panelClassName
            )}
          >
            {content}
          </div>,
          document.body
        )}
    </>
  );
}
