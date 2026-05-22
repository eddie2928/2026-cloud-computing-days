import { type ReactNode, type CSSProperties } from 'react';

interface ScreenContainerProps {
  children: ReactNode;
  style?: CSSProperties;
  className?: string;
}

export function ScreenContainer({ children, style, className }: ScreenContainerProps) {
  return (
    <div
      className={className}
      style={{
        maxWidth: 480,
        width: '100%',
        margin: '0 auto',
        minHeight: '100dvh',
        display: 'flex',
        flexDirection: 'column',
        paddingTop: 'env(safe-area-inset-top, 0px)',
        paddingBottom: 'env(safe-area-inset-bottom, 0px)',
        paddingLeft: 'env(safe-area-inset-left, 0px)',
        paddingRight: 'env(safe-area-inset-right, 0px)',
        position: 'relative',
        ...style,
      }}
    >
      {children}
    </div>
  );
}
