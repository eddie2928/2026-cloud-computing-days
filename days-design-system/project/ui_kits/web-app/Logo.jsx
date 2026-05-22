/* global React */

function Daisy({ size = 14, petalFill = '#FFFFFF', petalStroke = '#D5A646', centerFill = '#D5A646', centerStroke = '#A7842D', style }) {
  const petal = "M 12 11 C 9.5 11, 7.6 8.5, 7.6 5.6 C 7.6 2.4, 9.5 0.4, 12 0.4 C 14.5 0.4, 16.4 2.4, 16.4 5.6 C 16.4 8.5, 14.5 11, 12 11 Z";
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0, ...style }}>
      <g fill={petalFill} stroke={petalStroke} strokeWidth="0.6">
        <path d={petal}/>
        <path d={petal} transform="rotate(60 12 12)"/>
        <path d={petal} transform="rotate(120 12 12)"/>
        <path d={petal} transform="rotate(180 12 12)"/>
        <path d={petal} transform="rotate(240 12 12)"/>
        <path d={petal} transform="rotate(300 12 12)"/>
      </g>
      <circle cx="12" cy="12" r="4.4" fill={centerFill} stroke={centerStroke} strokeWidth="0.5"/>
    </svg>
  );
}

function Logo({ size = 32 }) {
  const daisySize = size * 0.48;
  // Approximate baseline of italic Playfair Display sits ~0.78 of font-size from the top.
  // Drop daisy so its CENTER sits at the visual bottom of 's' (cap-base): translateY pulls it down from baseline.
  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'baseline',
      gap: 1,
      fontFamily: 'var(--font-serif)',
      fontStyle: 'italic',
      fontWeight: 400,
      fontSize: size,
      letterSpacing: '-0.02em',
      color: 'var(--ink-coffee)',
      lineHeight: 1,
    }}>
      <span>days</span>
      <Daisy size={daisySize} style={{ transform: `translateY(${daisySize * 0.10}px)` }}/>
    </div>
  );
}

window.Logo = Logo;
window.Daisy = Daisy;
