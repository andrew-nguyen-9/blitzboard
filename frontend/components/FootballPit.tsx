"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";

// ── Physics 404 ──────────────────────────────────────────────────────────────
// Draggable footballs in a gravity well. They collide with each other (circle↔
// circle, elastic) AND with the real DOM text/buttons (circle↔AABB, measured live
// from getBoundingClientRect). Grab to drag, release to throw. Reduced-motion →
// static scatter, no loop. No canvas, no physics lib — just rAF + vector math.

interface Ball {
  x: number; y: number; vx: number; vy: number;
  r: number; rot: number; vrot: number;
  el: HTMLDivElement | null; dragging: boolean;
}

const GRAVITY = 0.45;
const REST = 0.62;       // wall/obstacle bounciness
const FRICTION = 0.992;
const BALL_REST = 0.9;   // ball↔ball

function Football() {
  return (
    <svg viewBox="0 0 60 38" width="60" height="38" aria-hidden>
      <defs>
        <linearGradient id="fb" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#9A5B33" /><stop offset="1" stopColor="#6F3D1E" />
        </linearGradient>
      </defs>
      <ellipse cx="30" cy="19" rx="29" ry="18" fill="url(#fb)" stroke="#3f2412" strokeWidth="1.5" />
      <path d="M14 19h32" stroke="#F4EFE6" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M19 19v6M24 14v10M30 13v12M36 14v10M41 19v6" stroke="#F4EFE6" strokeWidth="2" strokeLinecap="round" />
      <path d="M6 12c4 4 4 10 0 14M54 12c-4 4-4 10 0 14" stroke="#F4EFE6" strokeWidth="2" strokeLinecap="round" fill="none" />
    </svg>
  );
}

export default function FootballPit() {
  const pit = useRef<HTMLDivElement>(null);
  const balls = useRef<Ball[]>([]);
  const COUNT = 11;

  // attach ball DOM refs
  if (balls.current.length === 0) {
    balls.current = Array.from({ length: COUNT }, () => ({
      x: 0, y: 0, vx: 0, vy: 0, r: 26, rot: Math.random() * 360, vrot: 0, el: null, dragging: false,
    }));
  }

  useEffect(() => {
    const container = pit.current;
    if (!container) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const bounds = () => container.getBoundingClientRect();
    const obstacles = () => {
      const cb = bounds();
      return Array.from(container.querySelectorAll<HTMLElement>("[data-obstacle]")).map((el) => {
        const r = el.getBoundingClientRect();
        return { x: r.left - cb.left, y: r.top - cb.top, w: r.width, h: r.height };
      });
    };

    // seed positions across the top
    const b = bounds();
    balls.current.forEach((ball, i) => {
      ball.x = (b.width / (COUNT + 1)) * (i + 1);
      ball.y = 40 + Math.random() * 80;
      ball.vx = (Math.random() - 0.5) * 6;
      ball.vy = Math.random() * 2;
      ball.vrot = (Math.random() - 0.5) * 8;
    });

    let obs = obstacles();
    const remeasure = () => { obs = obstacles(); };
    window.addEventListener("resize", remeasure);
    const remT = setTimeout(remeasure, 300); // after fonts settle

    function step() {
      const bb = bounds();
      const W = bb.width, H = bb.height;
      const arr = balls.current;

      for (const ball of arr) {
        if (ball.dragging) continue;
        ball.vy += GRAVITY;
        ball.vx *= FRICTION; ball.vy *= FRICTION;
        ball.x += ball.vx; ball.y += ball.vy;
        ball.rot += ball.vrot; ball.vrot *= 0.98;

        // walls
        if (ball.x < ball.r) { ball.x = ball.r; ball.vx = -ball.vx * REST; ball.vrot = -ball.vx; }
        if (ball.x > W - ball.r) { ball.x = W - ball.r; ball.vx = -ball.vx * REST; ball.vrot = -ball.vx; }
        if (ball.y > H - ball.r) { ball.y = H - ball.r; ball.vy = -ball.vy * REST; ball.vx *= 0.96; }
        if (ball.y < ball.r) { ball.y = ball.r; ball.vy = -ball.vy * REST; }

        // obstacles (circle ↔ AABB)
        for (const o of obs) {
          const cx = Math.max(o.x, Math.min(ball.x, o.x + o.w));
          const cy = Math.max(o.y, Math.min(ball.y, o.y + o.h));
          const dx = ball.x - cx, dy = ball.y - cy;
          const d2 = dx * dx + dy * dy;
          if (d2 < ball.r * ball.r && d2 > 0.0001) {
            const d = Math.sqrt(d2);
            const nx = dx / d, ny = dy / d;
            ball.x = cx + nx * ball.r; ball.y = cy + ny * ball.r;
            const dot = ball.vx * nx + ball.vy * ny;
            ball.vx = (ball.vx - 2 * dot * nx) * REST;
            ball.vy = (ball.vy - 2 * dot * ny) * REST;
            ball.vrot += (ball.vx - ball.vy) * 0.3;
          }
        }
      }

      // ball ↔ ball
      for (let i = 0; i < arr.length; i++) {
        for (let j = i + 1; j < arr.length; j++) {
          const a = arr[i], c = arr[j];
          const dx = c.x - a.x, dy = c.y - a.y;
          const dist = Math.hypot(dx, dy) || 0.001;
          const min = a.r + c.r;
          if (dist < min) {
            const nx = dx / dist, ny = dy / dist;
            const overlap = (min - dist) / 2;
            if (!a.dragging) { a.x -= nx * overlap; a.y -= ny * overlap; }
            if (!c.dragging) { c.x += nx * overlap; c.y += ny * overlap; }
            const dvx = c.vx - a.vx, dvy = c.vy - a.vy;
            const p = (dvx * nx + dvy * ny) * BALL_REST;
            if (p < 0) {
              if (!a.dragging) { a.vx += p * nx; a.vy += p * ny; }
              if (!c.dragging) { c.vx -= p * nx; c.vy -= p * ny; }
              a.vrot += p * 2; c.vrot -= p * 2;
            }
          }
        }
      }

      for (const ball of arr) {
        if (ball.el) ball.el.style.transform = `translate(${ball.x - ball.r}px, ${ball.y - ball.r}px) rotate(${ball.rot}deg)`;
      }
      raf = requestAnimationFrame(step);
    }

    let raf = 0;
    if (!reduce) raf = requestAnimationFrame(step);
    else {
      // static scatter
      balls.current.forEach((ball) => { if (ball.el) ball.el.style.transform = `translate(${ball.x - ball.r}px, ${ball.y - ball.r}px) rotate(${ball.rot}deg)`; });
    }

    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", remeasure); clearTimeout(remT); };
  }, []);

  // drag handling (pointer)
  function onPointerDown(i: number, e: React.PointerEvent) {
    const ball = balls.current[i];
    const container = pit.current; if (!container) return;
    ball.dragging = true;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    const cb = container.getBoundingClientRect();
    let lastX = e.clientX, lastY = e.clientY;
    const move = (ev: PointerEvent) => {
      ball.x = ev.clientX - cb.left; ball.y = ev.clientY - cb.top;
      ball.vx = ev.clientX - lastX; ball.vy = ev.clientY - lastY;
      ball.vrot = ball.vx * 1.5;
      lastX = ev.clientX; lastY = ev.clientY;
      if (ball.el) ball.el.style.transform = `translate(${ball.x - ball.r}px, ${ball.y - ball.r}px) rotate(${ball.rot}deg)`;
    };
    const up = () => {
      ball.dragging = false;
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }

  return (
    <div ref={pit} className="relative mx-auto flex min-h-[78vh] max-w-wide flex-col items-center justify-center overflow-hidden px-5 text-center">
      {/* obstacles = real content the footballs collide with */}
      <div data-obstacle className="font-scoreboard text-score-xl leading-none text-accent" style={{ textShadow: "0 0 60px var(--accent-soft)" }}>
        404
      </div>
      <p data-obstacle className="mt-2 font-display text-display-md">That play didn&apos;t connect.</p>
      <p data-obstacle className="mt-3 max-w-md text-body text-ink-muted">
        Fourth down, turnover on downs. Toss the footballs around while you&apos;re here — they bounce off everything.
      </p>
      <Link
        href="/"
        data-obstacle
        data-cursor="home"
        className="mt-8 inline-block rounded-full bg-accent px-6 py-3 font-semibold text-bg transition hover:scale-[1.03]"
      >
        Back to the war room
      </Link>

      {/* the footballs */}
      {Array.from({ length: COUNT }).map((_, i) => (
        <div
          key={i}
          ref={(el) => { balls.current[i].el = el; }}
          onPointerDown={(e) => onPointerDown(i, e)}
          data-cursor="grab"
          className="absolute left-0 top-0 z-10 touch-none select-none active:scale-105"
          style={{ width: 52, height: 52, cursor: "grab" }}
        >
          <div className="grid h-[52px] w-[52px] place-items-center drop-shadow-lg">
            <Football />
          </div>
        </div>
      ))}
    </div>
  );
}
