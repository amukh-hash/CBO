import { motion } from "framer-motion";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { AtlasMeta } from "./atlasTypes";
import { useDuoCatClipController } from "./useDuoCatClipController";
import { useDuoCatPlaylist } from "./useDuoCatPlaylist";
import { useSpriteAnimator } from "./useSpriteAnimator";

type DuoCatController = {
  playOnce: (name: string) => Promise<void>;
  queue: (names: string[]) => Promise<void>;
  setIdle: () => void;
};

type DuoCatSpriteProps = {
  clip?: string;
  hoverClip?: string;
  switchClipOnHover?: boolean;
  scale?: number;
  paused?: boolean;
  pause?: boolean;
  speed?: number;
  speedMultiplier?: number;
  meta?: AtlasMeta;
  metadataUrl?: string;
  className?: string;
  spriteClassName?: string;
  onController?: (controller: DuoCatController) => void;
  playlist?: string;
  playlistEnabled?: boolean;
  clickQueue?: string[];
};

const defaultMetaUrl = "/static/sprites/cats/cats_duo_pack.json?v=cat-tree-41";
let cachedMeta: AtlasMeta | null = null;

function isDebugLoggingEnabled(): boolean {
  if (typeof window === "undefined") return false;
  if ((window as { __DUO_CATS_DEBUG__?: boolean }).__DUO_CATS_DEBUG__ === true) return true;
  const host = window.location?.hostname ?? "";
  return host === "localhost" || host === "127.0.0.1";
}

export function DuoCatSprite({
  clip,
  hoverClip = "nose_boop",
  switchClipOnHover = true,
  scale = 1,
  paused,
  pause,
  speed,
  speedMultiplier,
  meta,
  metadataUrl = defaultMetaUrl,
  className,
  spriteClassName,
  onController,
  playlist = "ambient_random",
  playlistEnabled = true,
  clickQueue,
}: DuoCatSpriteProps) {
  const [resolvedMeta, setResolvedMeta] = useState<AtlasMeta | null>(meta ?? cachedMeta);
  const hoverPlayedRef = useRef(false);
  const initialClipAppliedRef = useRef(false);
  const activeUserActionsRef = useRef(0);
  const [playlistSuspended, setPlaylistSuspended] = useState(false);
  const mountLoggedRef = useRef(false);

  useEffect(() => {
    if (meta) {
      cachedMeta = meta;
      setResolvedMeta(meta);
      return;
    }
    if (cachedMeta) {
      setResolvedMeta(cachedMeta);
      return;
    }
    let cancelled = false;
    fetch(metadataUrl, { credentials: "same-origin" })
      .then((res) => res.json() as Promise<AtlasMeta>)
      .then((loaded) => {
        if (cancelled) return;
        cachedMeta = loaded;
        setResolvedMeta(loaded);
      })
      .catch(() => {
        if (!cancelled) setResolvedMeta(null);
      });
    return () => {
      cancelled = true;
    };
  }, [meta, metadataUrl]);

  const ctrl = useDuoCatClipController(resolvedMeta);
  const playlistIsEnabled = Boolean(playlistEnabled) && !playlistSuspended;
  useDuoCatPlaylist(
    resolvedMeta,
    {
      playOnce: ctrl.playOnce,
      setIdle: ctrl.setIdle,
      isBusy: ctrl.isBusy,
    },
    playlist,
    playlistIsEnabled
  );

  const baseClip = clip || resolvedMeta?.default_clip || "snuggle_idle";
  const baseClipExists = Boolean(resolvedMeta?.clips?.[baseClip]);
  const hoverClipExists = Boolean(resolvedMeta?.clips?.[hoverClip]);

  useEffect(() => {
    if (!isDebugLoggingEnabled()) return;
    if (!resolvedMeta?.clips) return;
    if (mountLoggedRef.current) return;
    mountLoggedRef.current = true;
    console.log("[DuoCats][mount]", {
      playlist,
      playlistEnabled: Boolean(playlistEnabled),
      default_clip: resolvedMeta.default_clip ?? "snuggle_idle",
      clip: baseClip,
      hoverClip,
    });
  }, [baseClip, hoverClip, playlist, playlistEnabled, resolvedMeta]);

  useEffect(() => {
    if (playlistEnabled) return;
    if (!resolvedMeta?.clips) return;
    if (initialClipAppliedRef.current) return;
    initialClipAppliedRef.current = true;

    if (baseClipExists) {
      const baseCfg = resolvedMeta.clips[baseClip];
      ctrl.playOnce(baseClip).then(() => {
        if (!baseCfg?.loop) {
          ctrl.setIdle();
        }
      });
      return;
    }
    ctrl.setIdle();
  }, [baseClip, baseClipExists, ctrl, playlistEnabled, resolvedMeta]);

  useEffect(() => {
    if (!resolvedMeta?.clips || typeof onController !== "function") return;
    onController({
      playOnce: ctrl.playOnce,
      queue: ctrl.queue,
      setIdle: ctrl.setIdle,
    });
  }, [ctrl.playOnce, ctrl.queue, ctrl.setIdle, onController, resolvedMeta]);

  const pausedState = paused ?? pause ?? false;
  const speedMultiplierState = speed ?? speedMultiplier ?? 1;
  const defaultClickQueue = useMemo(() => ["mutual_groom", "paw_batting", "snuggle_curl"], []);
  const requestedClickQueue = useMemo(() => {
    if (Array.isArray(clickQueue) && clickQueue.length > 0) {
      return clickQueue;
    }
    return defaultClickQueue;
  }, [clickQueue, defaultClickQueue]);
  const validClickQueue = useMemo(() => {
    if (!resolvedMeta?.clips) return [];
    return requestedClickQueue.filter((name) => Boolean(resolvedMeta.clips[name]));
  }, [requestedClickQueue, resolvedMeta]);

  const runUserAction = useCallback(
    async (runner: () => Promise<void>) => {
      const debug = isDebugLoggingEnabled();
      activeUserActionsRef.current += 1;
      setPlaylistSuspended(true);
      if (debug) {
        console.log("[DuoCats][playlist]", "pause", {
          activeUserActions: activeUserActionsRef.current,
        });
      }
      try {
        await runner();
      } finally {
        activeUserActionsRef.current -= 1;
        if (activeUserActionsRef.current <= 0) {
          activeUserActionsRef.current = 0;
          ctrl.setIdle();
          setPlaylistSuspended(false);
          if (debug) {
            console.log("[DuoCats][playlist]", "resume");
          }
        }
      }
    },
    [ctrl.setIdle]
  );

  const { rect: frameRect, imagePath: resolvedImagePath, frameIndex, pageIndex, cellIndex } = useSpriteAnimator(
    resolvedMeta,
    ctrl.clipName,
    {
      paused: pausedState,
      speed: speedMultiplierState,
    },
    ctrl.onDone,
    ctrl.playNonce
  );
  const clipImagePath = resolvedImagePath;

  useEffect(() => {
    const debugEnabled = typeof window !== "undefined" && (window as { __DUO_CATS_DEBUG__?: boolean }).__DUO_CATS_DEBUG__;
    if (!debugEnabled) return;
    console.log("[DuoCats][frame]", {
      clip: ctrl.clipName,
      logicalFrameIndex: frameIndex,
      pageIndex,
      cellIndex,
      imagePath: clipImagePath,
    });
  }, [cellIndex, clipImagePath, ctrl.clipName, frameIndex, pageIndex]);

  if (!resolvedMeta || !frameRect || !resolvedMeta.clips?.[ctrl.clipName]) {
    return null;
  }

  const atlasWidth = resolvedMeta.cols * resolvedMeta.frameW;
  const atlasHeight = resolvedMeta.rows * resolvedMeta.frameH;
  const spriteWidth = resolvedMeta.frameW;
  const spriteHeight = resolvedMeta.frameH;
  const displayWidth = spriteWidth * scale;
  const displayHeight = spriteHeight * scale;

  if (!clipImagePath) {
    return null;
  }

  const handleHoverStart = () => {
    if (!switchClipOnHover || !hoverClipExists) return;
    if (hoverPlayedRef.current) return;
    hoverPlayedRef.current = true;
    void runUserAction(() => ctrl.playOnce(hoverClip));
  };

  const handleHoverEnd = () => {
    hoverPlayedRef.current = false;
    if (!playlistEnabled) {
      ctrl.setIdle();
    }
  };

  const handleClickBurst = () => {
    if (validClickQueue.length === 0) return;
    void runUserAction(() => ctrl.queue(validClickQueue));
  };

  const handleKeyDown: React.KeyboardEventHandler<HTMLDivElement> = (event) => {
    if (event.key !== "Enter" && event.key !== " " && event.key !== "Spacebar") return;
    event.preventDefault();
    handleClickBurst();
  };

  return (
    <motion.div
      className={className ?? "duo-cat-sprite"}
      initial={{ opacity: 0.8 }}
      animate={{ opacity: 1 }}
      whileHover={{ scale: 1.02 }}
      onHoverStart={handleHoverStart}
      onHoverEnd={handleHoverEnd}
      onClick={handleClickBurst}
      onKeyDown={handleKeyDown}
      role={validClickQueue.length > 0 ? "button" : undefined}
      tabIndex={validClickQueue.length > 0 ? 0 : undefined}
      aria-label={validClickQueue.length > 0 ? "Play interaction burst" : undefined}
      transition={{ duration: 0.2, ease: "easeOut" }}
      style={{
        width: `${displayWidth}px`,
        height: `${displayHeight}px`,
        overflow: "hidden",
        transformOrigin: "center bottom",
      }}
    >
      <div
        className={spriteClassName ?? "duo-cat-sprite-frame"}
        style={{
          width: `${spriteWidth}px`,
          height: `${spriteHeight}px`,
          transform: `scale(${scale})`,
          transformOrigin: "top left",
          backgroundImage: `url(${clipImagePath})`,
          backgroundRepeat: "no-repeat",
          backgroundSize: `${atlasWidth}px ${atlasHeight}px`,
          // Atlas rects are pixel offsets into the sprite sheet; negate x/y to reveal the selected cell.
          backgroundPosition: `${-frameRect.x}px ${-frameRect.y}px`,
          imageRendering: "pixelated",
        }}
      />
    </motion.div>
  );
}
