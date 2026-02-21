import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { AtlasMeta, Clip } from "./atlasTypes";

function resolveDefaultClip(meta: AtlasMeta | null | undefined): string {
  if (!meta || !meta.clips) return "";
  if (meta.default_clip && meta.clips[meta.default_clip]) return meta.default_clip;
  if (meta.clips.snuggle_idle) return "snuggle_idle";
  if (meta.clips.duo_snuggle) return "duo_snuggle";
  const keys = Object.keys(meta.clips);
  return keys.length > 0 ? keys[0] : "";
}

function clipFrameCount(clip: Clip | null | undefined): number {
  if (!clip) return 0;
  if (Array.isArray(clip.timeline) && clip.timeline.length > 0) return clip.timeline.length;
  if (typeof clip.frame_count === "number" && clip.frame_count > 0) return clip.frame_count;
  if (Array.isArray(clip.frames)) return clip.frames.length;
  return 0;
}

type ClipController = {
  clipName: string;
  playNonce: number;
  setIdle: () => void;
  playOnce: (name: string) => Promise<void>;
  queue: (names: string[]) => Promise<void>;
  isBusy: () => boolean;
  onDone: (doneClipName: string) => void;
};

export function useDuoCatClipController(meta: AtlasMeta | null | undefined): ClipController {
  const defaultClip = useMemo(() => resolveDefaultClip(meta), [meta]);

  const [clipName, setClipName] = useState(defaultClip);
  const [playNonce, setPlayNonce] = useState(0);

  const pendingRef = useRef(Promise.resolve());
  const inQueueRef = useRef(false);
  const resolveRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!meta?.clips?.[clipName]) {
      setClipName(defaultClip);
      setPlayNonce((prev) => prev + 1);
    }
  }, [clipName, defaultClip, meta]);

  const setIdle = useCallback(() => {
    if (!defaultClip) return;
    setClipName(defaultClip);
    setPlayNonce((prev) => prev + 1);
  }, [defaultClip]);

  const playOnce = useCallback(
    (name: string): Promise<void> => {
      return new Promise((resolve) => {
        if (!meta?.clips?.[name]) {
          resolveRef.current?.();
          resolveRef.current = null;
          resolve();
          return;
        }

        resolveRef.current?.();
        resolveRef.current = () => {
          resolveRef.current = null;
          resolve();
        };

        setClipName(name);
        setPlayNonce((prev) => prev + 1);

        const clip = meta.clips[name];
        if (!clip || clip.loop || clipFrameCount(clip) <= 1) {
          resolveRef.current?.();
        }
      });
    },
    [meta]
  );

  const queue = useCallback(
    (names: string[]): Promise<void> => {
      const safeNames = Array.isArray(names) ? names.slice() : [];
      pendingRef.current = pendingRef.current.then(async () => {
        inQueueRef.current = true;
        try {
          for (const name of safeNames) {
            await playOnce(name);
          }
        } finally {
          inQueueRef.current = false;
          setIdle();
        }
      });
      return pendingRef.current;
    },
    [playOnce, setIdle]
  );

  const onDone = useCallback(
    (doneClipName: string) => {
      resolveRef.current?.();
      if (inQueueRef.current) return;
      const doneClip = meta?.clips?.[doneClipName];
      const returnTo = doneClip?.return_to && meta?.clips?.[doneClip.return_to] ? doneClip.return_to : defaultClip;
      if (!returnTo) return;
      setClipName(returnTo);
      setPlayNonce((prev) => prev + 1);
    },
    [defaultClip, meta]
  );

  const isBusy = useCallback(() => {
    return inQueueRef.current || resolveRef.current !== null;
  }, []);

  return {
    clipName,
    playNonce,
    setIdle,
    playOnce,
    queue,
    isBusy,
    onDone,
  };
}
