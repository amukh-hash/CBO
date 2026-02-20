import { useEffect, useMemo, useRef, useState } from "react";

import type { AtlasMeta, FrameRect } from "./atlasTypes";

type Options = {
  paused?: boolean;
  speed?: number;
};

type AnimatorState = {
  frameId: number | null;
  rect: FrameRect | null;
};

export function useSpriteAnimator(
  meta: AtlasMeta | null | undefined,
  clipName: string,
  options: Options = {}
): AnimatorState {
  const { paused = false, speed = 1 } = options;
  const clip = meta?.clips[clipName];
  const frameCount = clip?.frames.length ?? 0;
  const frameById = useMemo(() => {
    if (!meta) return new Map<number, FrameRect>();
    return new Map(meta.frames.map((frame) => [frame.id, frame]));
  }, [meta]);

  const rafRef = useRef<number | null>(null);
  const lastTsRef = useRef<number | null>(null);
  const accMsRef = useRef(0);
  const frameIdxRef = useRef(0);

  const firstFrameId = frameCount > 0 ? (clip?.frames[0] ?? null) : null;
  const [frameId, setFrameId] = useState<number | null>(firstFrameId);

  const frameDurationMs = useMemo(() => {
    if (!clip || clip.fps <= 0 || speed <= 0) {
      return Number.POSITIVE_INFINITY;
    }
    return 1000 / (clip.fps * speed);
  }, [clip, speed]);

  useEffect(() => {
    frameIdxRef.current = 0;
    lastTsRef.current = null;
    accMsRef.current = 0;
    setFrameId(firstFrameId);
  }, [firstFrameId, clipName, meta]);

  useEffect(() => {
    if (!clip || frameCount === 0 || paused || !Number.isFinite(frameDurationMs)) {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      return undefined;
    }

    if (frameCount <= 1) {
      return undefined;
    }

    const tick = (ts: number) => {
      if (lastTsRef.current === null) {
        lastTsRef.current = ts;
      }
      const dt = ts - lastTsRef.current;
      lastTsRef.current = ts;
      accMsRef.current += Math.max(0, dt);

      const steps = Math.floor(accMsRef.current / frameDurationMs);
      if (steps > 0) {
        accMsRef.current -= steps * frameDurationMs;
        const prevIdx = frameIdxRef.current;
        let nextIdx = prevIdx;
        if (clip.loop) {
          nextIdx = (prevIdx + steps) % frameCount;
        } else {
          nextIdx = Math.min(prevIdx + steps, frameCount - 1);
        }
        frameIdxRef.current = nextIdx;
        if (nextIdx !== prevIdx) {
          setFrameId(clip.frames[nextIdx] ?? null);
        }
      }

      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }
      rafRef.current = null;
      lastTsRef.current = null;
      accMsRef.current = 0;
    };
  }, [clip, frameCount, frameDurationMs, paused]);

  const rect = frameId === null ? null : (frameById.get(frameId) ?? null);
  return { frameId, rect };
}
