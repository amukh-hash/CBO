import { useEffect, useMemo, useRef, useState } from "react";

import type { Clip } from "./atlasTypes";

type Options = {
  pause?: boolean;
  speedMultiplier?: number;
};

type AnimatorState = {
  frameIndex: number;
  frameId: number;
};

export function useSpriteAnimator(clip: Clip | undefined, options: Options = {}): AnimatorState {
  const { pause = false, speedMultiplier = 1 } = options;
  const [frameIndex, setFrameIndex] = useState(0);

  const rafRef = useRef<number | null>(null);
  const lastTsRef = useRef<number | null>(null);
  const accumulatorRef = useRef(0);

  const stepMs = useMemo(() => {
    if (!clip || clip.fps <= 0 || speedMultiplier <= 0) {
      return Number.POSITIVE_INFINITY;
    }
    return 1000 / (clip.fps * speedMultiplier);
  }, [clip, speedMultiplier]);

  useEffect(() => {
    setFrameIndex(0);
    accumulatorRef.current = 0;
    lastTsRef.current = null;
  }, [clip]);

  useEffect(() => {
    if (!clip || pause || !Number.isFinite(stepMs)) {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      return undefined;
    }

    const frameCount = clip.frames.length;
    if (frameCount <= 1) {
      return undefined;
    }

    const tick = (ts: number) => {
      if (lastTsRef.current === null) {
        lastTsRef.current = ts;
      }

      const dt = ts - lastTsRef.current;
      lastTsRef.current = ts;
      accumulatorRef.current += dt;

      let steps = 0;
      while (accumulatorRef.current >= stepMs) {
        accumulatorRef.current -= stepMs;
        steps += 1;
      }

      if (steps > 0) {
        setFrameIndex((prev) => {
          const raw = prev + steps;
          if (clip.loop) {
            return raw % frameCount;
          }
          return Math.min(raw, frameCount - 1);
        });
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
      accumulatorRef.current = 0;
    };
  }, [clip, pause, stepMs]);

  const frameId = clip?.frames[Math.min(frameIndex, Math.max(clip?.frames.length ?? 1, 1) - 1)] ?? 0;
  return { frameIndex, frameId };
}
