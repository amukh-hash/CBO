import { useEffect, useMemo, useRef } from "react";

import type { AtlasMeta, Playlist } from "./atlasTypes";

type PlaylistController = {
  playOnce: (name: string) => Promise<void>;
  setIdle: () => void;
  isBusy?: () => boolean;
};

type PlaylistPhase = "enter_idle" | "pick_clip";

function isDebugLoggingEnabled(): boolean {
  if (typeof window === "undefined") return false;
  if ((window as { __DUO_CATS_DEBUG__?: boolean }).__DUO_CATS_DEBUG__ === true) return true;
  const host = window.location?.hostname ?? "";
  return host === "localhost" || host === "127.0.0.1";
}

function clampMs(value: unknown, fallback = 0): number {
  if (typeof value !== "number" || !Number.isFinite(value)) return fallback;
  return Math.max(0, Math.floor(value));
}

function randomRange(range: [number, number] | undefined, fallback: number): number {
  if (!Array.isArray(range) || range.length !== 2) return fallback;
  const min = clampMs(range[0], fallback);
  const max = clampMs(range[1], fallback);
  if (max <= min) return min;
  return min + Math.floor(Math.random() * (max - min + 1));
}

function weightedPick(pool: [string, number][]): string | null {
  let total = 0;
  for (const [, weight] of pool) {
    if (Number.isFinite(weight) && weight > 0) {
      total += weight;
    }
  }
  if (total <= 0) return null;

  let cursor = Math.random() * total;
  for (const [clip, weight] of pool) {
    if (!Number.isFinite(weight) || weight <= 0) continue;
    cursor -= weight;
    if (cursor <= 0) return clip;
  }
  return pool.length > 0 ? pool[pool.length - 1][0] : null;
}

function sleep(ms: number, cancel: { current: boolean }): Promise<void> {
  const duration = Math.max(0, Math.floor(ms));
  if (duration <= 0) return Promise.resolve();
  return new Promise((resolve) => {
    const timer = window.setTimeout(resolve, duration);
    if (cancel.current) {
      window.clearTimeout(timer);
      resolve();
    }
  });
}

export function useDuoCatPlaylist(
  meta: AtlasMeta | null | undefined,
  controller: PlaylistController,
  playlistName: string | undefined,
  enabled: boolean
): void {
  const nextPickAtRef = useRef(0);
  const phaseRef = useRef<PlaylistPhase>("enter_idle");
  const sequenceIndexRef = useRef(0);

  const playlist = useMemo<Playlist | null>(() => {
    if (!meta?.library?.playlists || !playlistName) return null;
    return meta.library.playlists[playlistName] ?? null;
  }, [meta, playlistName]);

  useEffect(() => {
    if (!enabled || !meta || !playlist) return undefined;
    const debug = isDebugLoggingEnabled();

    const cancelled = { current: false };
    const clips = meta.clips ?? {};
    const foundation = meta.library?.foundation;
    const idleClip = playlist.idle_clip ?? foundation ?? meta.default_clip ?? "snuggle_idle";
    nextPickAtRef.current = 0;
    phaseRef.current = "enter_idle";
    sequenceIndexRef.current = 0;

    const isBusy = (): boolean => {
      if (typeof controller.isBusy !== "function") return false;
      try {
        return Boolean(controller.isBusy());
      } catch (_error) {
        return false;
      }
    };

    const readIdleHoldMs = (): number => {
      if (playlist.mode === "sequence") {
        return clampMs(playlist.idle_hold_ms, 0);
      }
      return randomRange(playlist.idle_hold_ms_range, 0);
    };

    const readBetweenHoldMs = (): number => {
      if (playlist.mode === "sequence") {
        return clampMs(playlist.between_hold_ms, 0);
      }
      return randomRange(playlist.between_hold_ms_range, 0);
    };

    const pickNextClip = (): string | null => {
      if (playlist.mode === "sequence") {
        if (Array.isArray(playlist.clips) && playlist.clips.length > 0) {
          const clip = playlist.clips[sequenceIndexRef.current % playlist.clips.length] ?? null;
          sequenceIndexRef.current += 1;
          return clip;
        }
        return null;
      }
      if (Array.isArray(playlist.pool) && playlist.pool.length > 0) {
        return weightedPick(playlist.pool);
      }
      return null;
    };

    const setNextPickDelay = (delayMs: number): void => {
      nextPickAtRef.current = Date.now() + clampMs(delayMs, 0);
    };

    if (debug) {
      console.log("[DuoCats][playlist]", "start", {
        playlist: playlistName ?? "",
        mode: playlist.mode,
        idleClip,
      });
    }

    const run = async () => {
      while (!cancelled.current) {
        const now = Date.now();
        const busy = isBusy();
        const waitMs = Math.max(0, nextPickAtRef.current - now);

        if (debug) {
          console.log("[DuoCats][playlist]", "tick", {
            playlist: playlistName ?? "",
            mode: playlist.mode,
            idleClip,
            phase: phaseRef.current,
            busy,
            waitMs,
          });
        }

        if (busy) {
          await sleep(120, cancelled);
          continue;
        }

        if (waitMs > 0) {
          await sleep(Math.min(waitMs, 250), cancelled);
          continue;
        }

        try {
          if (phaseRef.current === "enter_idle") {
            if (clips[idleClip]) {
              await controller.playOnce(idleClip);
            } else {
              controller.setIdle();
            }
            if (cancelled.current) return;

            const idleHoldMs = readIdleHoldMs();
            setNextPickDelay(idleHoldMs);
            phaseRef.current = "pick_clip";
            continue;
          }

          const nextClip = pickNextClip();
          if (debug) {
            console.log("[DuoCats][playlist]", "next", {
              playlist: playlistName ?? "",
              clip: nextClip,
            });
          }

          if (nextClip && clips[nextClip]) {
            await controller.playOnce(nextClip);
            if (cancelled.current) return;
            const holdLastMs = clampMs(clips[nextClip]?.hold_last_ms, 0);
            if (holdLastMs > 0) {
              await sleep(holdLastMs, cancelled);
              if (cancelled.current) return;
            }
          }

          setNextPickDelay(readBetweenHoldMs());
          phaseRef.current = "enter_idle";
        } catch (_error) {
          await sleep(120, cancelled);
        }
      }
    };

    void run();
    return () => {
      cancelled.current = true;
      nextPickAtRef.current = 0;
      if (debug) {
        console.log("[DuoCats][playlist]", "stop", {
          playlist: playlistName ?? "",
        });
      }
    };
  }, [controller.isBusy, controller.playOnce, controller.setIdle, enabled, meta, playlist, playlistName]);
}
