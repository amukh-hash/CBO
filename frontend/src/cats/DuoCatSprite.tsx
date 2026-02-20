import { motion } from "framer-motion";
import { useEffect, useState } from "react";

import type { AtlasMeta } from "./atlasTypes";
import { useSpriteAnimator } from "./useSpriteAnimator";

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
};

const defaultMetaUrl = "/static/sprites/cats/cats_duo_atlas.json";
let cachedMeta: AtlasMeta | null = null;

export function DuoCatSprite({
  clip = "duo_snuggle",
  hoverClip = "duo_groom",
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
}: DuoCatSpriteProps) {
  const [resolvedMeta, setResolvedMeta] = useState<AtlasMeta | null>(meta ?? cachedMeta);
  const [isHovered, setIsHovered] = useState(false);

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

  const activeClipName =
    isHovered && switchClipOnHover && hoverClip && resolvedMeta?.clips[hoverClip] ? hoverClip : clip;
  const pausedState = paused ?? pause ?? false;
  const speedMultiplierState = speed ?? speedMultiplier ?? 1;
  const { rect: frameRect } = useSpriteAnimator(resolvedMeta, activeClipName, {
    paused: pausedState,
    speed: speedMultiplierState,
  });

  if (!resolvedMeta || !frameRect) {
    return null;
  }

  const atlasWidth = resolvedMeta.cols * resolvedMeta.frameW;
  const atlasHeight = resolvedMeta.rows * resolvedMeta.frameH;
  const spriteWidth = resolvedMeta.frameW;
  const spriteHeight = resolvedMeta.frameH;
  const displayWidth = spriteWidth * scale;
  const displayHeight = spriteHeight * scale;

  return (
    <motion.div
      className={className ?? "duo-cat-sprite"}
      initial={{ opacity: 0.8 }}
      animate={{ opacity: 1 }}
      whileHover={{ scale: 1.02 }}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
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
          backgroundImage: `url(${resolvedMeta.imagePath})`,
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
