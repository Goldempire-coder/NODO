export function AnimatedLogo() {
  return (
    <div aria-label="NODO" className="animated-logo" role="img">
      <span className="animated-logo__mark">
        <span className="animated-logo__n">N</span>
        <span className="animated-logo__arrow" />
      </span>
      <span className="animated-logo__check" aria-hidden="true" />
    </div>
  );
}
