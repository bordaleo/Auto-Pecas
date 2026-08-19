import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { CAR_BRANDS } from '../utils/commerce';

const DRAG_THRESHOLD = 6;
const AUTO_PX_PER_SEC = 42;
const RESUME_AFTER_MS = 1600;

function BrandLogo({ brand }) {
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <span className="brand-chip-logo brand-chip-logo--fallback" aria-hidden="true">
        {brand.abbr}
      </span>
    );
  }

  return (
    <span className="brand-chip-logo">
      <img
        src={brand.logo}
        alt=""
        width={40}
        height={40}
        loading="lazy"
        decoding="async"
        draggable={false}
        onError={() => setFailed(true)}
      />
    </span>
  );
}

export default function BrandMarquee() {
  const trackRef = useRef(null);
  const offsetRef = useRef(0);
  const halfRef = useRef(0);
  const hoverRef = useRef(false);
  const reduceMotionRef = useRef(false);
  const pauseUntilRef = useRef(0);
  const dragRef = useRef({
    active: false,
    pointerId: null,
    startX: 0,
    startOffset: 0,
    moved: false,
    suppressClick: false,
  });

  const items = [...CAR_BRANDS, ...CAR_BRANDS];

  useEffect(() => {
    const track = trackRef.current;
    if (!track) return;

    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const syncMotion = () => {
      reduceMotionRef.current = media.matches;
    };
    syncMotion();
    media.addEventListener?.('change', syncMotion);

    const measure = () => {
      halfRef.current = track.scrollWidth / 2;
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(track);

    const apply = () => {
      const half = halfRef.current;
      if (!half) return;
      let x = offsetRef.current % half;
      if (x < 0) x += half;
      track.style.transform = `translate3d(${-x}px, 0, 0)`;
    };

    let raf = 0;
    let last = performance.now();
    const tick = (now) => {
      const dt = Math.min(now - last, 48);
      last = now;
      const dragging = dragRef.current.active;
      const paused = dragging || hoverRef.current || now < pauseUntilRef.current;
      if (!paused && !reduceMotionRef.current) {
        offsetRef.current += AUTO_PX_PER_SEC * (dt / 1000);
      }
      apply();
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
      media.removeEventListener?.('change', syncMotion);
    };
  }, []);

  const pauseAuto = (ms = RESUME_AFTER_MS) => {
    pauseUntilRef.current = performance.now() + ms;
  };

  const applyNow = () => {
    const track = trackRef.current;
    const half = halfRef.current;
    if (!track || !half) return;
    let x = offsetRef.current % half;
    if (x < 0) x += half;
    track.style.transform = `translate3d(${-x}px, 0, 0)`;
  };

  const onPointerDown = (event) => {
    if (event.button != null && event.button !== 0) return;
    dragRef.current = {
      active: true,
      pointerId: event.pointerId,
      startX: event.clientX,
      startOffset: offsetRef.current,
      moved: false,
      suppressClick: false,
    };
    event.currentTarget.setPointerCapture?.(event.pointerId);
    event.currentTarget.classList.add('is-dragging');
    pauseAuto(60_000);
  };

  const onPointerMove = (event) => {
    const drag = dragRef.current;
    if (!drag.active || drag.pointerId !== event.pointerId) return;
    const dx = event.clientX - drag.startX;
    if (Math.abs(dx) > DRAG_THRESHOLD) {
      drag.moved = true;
      if (event.cancelable) event.preventDefault();
    }
    offsetRef.current = drag.startOffset - dx;
    applyNow();
  };

  const endDrag = (event) => {
    const drag = dragRef.current;
    if (!drag.active) return;
    if (event && drag.pointerId !== event.pointerId) return;
    drag.active = false;
    drag.suppressClick = drag.moved;
    event?.currentTarget?.classList.remove('is-dragging');
    pauseAuto(drag.moved ? 2200 : 400);
  };

  const onClickCapture = (event) => {
    if (!dragRef.current.suppressClick) return;
    event.preventDefault();
    event.stopPropagation();
    dragRef.current.suppressClick = false;
  };

  const onKeyDown = (event) => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
    event.preventDefault();
    offsetRef.current += event.key === 'ArrowRight' ? 120 : -120;
    applyNow();
    pauseAuto();
  };

  return (
    <section className="vehicle-strip wrap" aria-label="Buscar por montadora">
      <div className="vehicle-strip-head">
        <h3>Encontre por veículo</h3>
        <p>Selecione a montadora e veja peças compatíveis</p>
      </div>
      <div
        className="vehicle-marquee"
        tabIndex={0}
        role="region"
        aria-label="Lista de montadoras. Arraste para o lado ou use as setas do teclado."
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onClickCapture={onClickCapture}
        onKeyDown={onKeyDown}
        onMouseEnter={() => { hoverRef.current = true; }}
        onMouseLeave={() => { hoverRef.current = false; }}
      >
        <div ref={trackRef} className="vehicle-track">
          {items.map((brand, index) => (
            <Link
              key={`${brand.slug}-${index}`}
              to={`/pecas/?vehicle_brand=${encodeURIComponent(brand.slug)}`}
              className="brand-chip"
              style={{ '--brand-color': brand.color }}
              title={`Peças para ${brand.name}`}
              draggable={false}
            >
              <BrandLogo brand={brand} />
              {brand.name}
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
