import { useEffect, useMemo, useRef, useState } from "react";

import type { AtlasMeta, Clip, FrameRect } from "./atlasTypes";

type Options = {
  paused?: boolean;
  speed?: number;
};

type AnimatorState = {
  frameId: number | null;
  frameIndex: number;
  rect: FrameRect | null;
  imagePath: string | null;
  pageIndex: number | null;
  cellIndex: number | null;
};

type OnDone = (clipName: string) => void;

function clipFrameCount(clip: Clip | null | undefined): number {
  if (!clip) return 0;
  if (Array.isArray(clip.timeline) && clip.timeline.length > 0) return clip.timeline.length;
  if (typeof clip.frame_count === "number" && clip.frame_count > 0) return clip.frame_count;
  if (Array.isArray(clip.frames)) return clip.frames.length;
  return 0;
}

function rectFromCell(meta: AtlasMeta, cellIndex: number): FrameRect {
  const col = cellIndex % meta.cols;
  const row = Math.floor(cellIndex / meta.cols);
  return {
    id: cellIndex,
    x: col * meta.frameW,
    y: row * meta.frameH,
    w: meta.frameW,
    h: meta.frameH,
  };
}

function emptyAnimatorState(): AnimatorState {
  return {
    frameId: null,
    frameIndex: 0,
    rect: null,
    imagePath: null,
    pageIndex: null,
    cellIndex: null,
  };
}

export function useSpriteAnimator(
  meta: AtlasMeta | null | undefined,
  clipName: string,
  options: Options = {},
  onDone?: OnDone,
  playNonce = 0
): AnimatorState {
  const { paused = false, speed = 1 } = options;
  const clip = meta?.clips?.[clipName];
  const frameCount = clipFrameCount(clip);

  const frameById = useMemo(() => {
    const map = new Map<number, FrameRect>();
    if (!meta || !Array.isArray(meta.frames)) return map;
    for (const frame of meta.frames) {
      map.set(frame.id, frame);
    }
    return map;
  }, [meta]);

  const rafRef = useRef<number | null>(null);
  const lastTsRef = useRef<number | null>(null);
  const accMsRef = useRef(0);
  const frameIdxRef = useRef(0);
  const doneRef = useRef(false);
  const doneNonceRef = useRef<number>(playNonce);

  const [frameIndex, setFrameIndex] = useState<number>(0);

  const frameDurationMs = useMemo(() => {
    if (!clip || clip.fps <= 0 || speed <= 0) return Number.POSITIVE_INFINITY;
    return 1000 / (clip.fps * speed);
  }, [clip, speed]);

  useEffect(() => {
    frameIdxRef.current = 0;
    lastTsRef.current = null;
    accMsRef.current = 0;
    doneRef.current = false;
    doneNonceRef.current = playNonce;
    setFrameIndex(0);
  }, [clipName, meta, playNonce]);

  useEffect(() => {
    if (!clip || frameCount === 0 || paused || !Number.isFinite(frameDurationMs)) {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      return undefined;
    }

    if (frameCount <= 1) {
      if (!clip.loop && !doneRef.current && typeof onDone === "function" && doneNonceRef.current === playNonce) {
        doneRef.current = true;
        onDone(clipName);
      }
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
          setFrameIndex(nextIdx);
        }

        if (!clip.loop && nextIdx >= frameCount - 1) {
          if (!doneRef.current && typeof onDone === "function" && doneNonceRef.current === playNonce) {
            doneRef.current = true;
            onDone(clipName);
          }
          rafRef.current = null;
          return;
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
  }, [clip, clipName, frameCount, frameDurationMs, onDone, paused, playNonce]);

  return useMemo(() => {
    if (!clip || !meta || frameCount <= 0) return emptyAnimatorState();

    const resolvedIndex = Math.max(0, Math.min(frameIndex, frameCount - 1));
    const fallbackImagePath = clip.imagePath ?? meta.imagePath ?? null;

    if (Array.isArray(clip.timeline) && clip.timeline.length > 0) {
      const entry = clip.timeline[resolvedIndex];
      const pageIndex = Array.isArray(entry) && typeof entry[0] === "number" ? entry[0] : -1;
      const cellIndex = Array.isArray(entry) && typeof entry[1] === "number" ? entry[1] : -1;
      const pagePath =
        pageIndex >= 0 && Array.isArray(clip.pages) && clip.pages[pageIndex]
          ? clip.pages[pageIndex].imagePath
          : undefined;

      let rect: FrameRect | null = null;
      if (cellIndex >= 0) {
        rect = rectFromCell(meta, cellIndex);
      }
      return {
        frameId: null,
        frameIndex: resolvedIndex,
        rect,
        imagePath: pagePath ?? fallbackImagePath,
        pageIndex: pageIndex >= 0 ? pageIndex : null,
        cellIndex: cellIndex >= 0 ? cellIndex : null,
      };
    }

    const frameIds = Array.isArray(clip.frames) ? clip.frames : [];
    const frameId = frameIds[resolvedIndex] ?? null;
    let rect: FrameRect | null = null;
    if (typeof frameId === "number") {
      rect = frameById.get(frameId) ?? null;
      if (!rect) {
        rect = rectFromCell(meta, frameId);
      }
    }
    return {
      frameId: typeof frameId === "number" ? frameId : null,
      frameIndex: resolvedIndex,
      rect,
      imagePath: fallbackImagePath,
      pageIndex: null,
      cellIndex: typeof frameId === "number" ? frameId : null,
    };
  }, [clip, frameById, frameCount, frameIndex, meta]);
}
