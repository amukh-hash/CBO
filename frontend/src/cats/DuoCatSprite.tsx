import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";

import type { AtlasMeta } from "./atlasTypes";
import { useSpriteAnimator } from "./useSpriteAnimator";

type DuoCatSpriteProps = {
  clip: string;
  scale?: number;
  pause?: boolean;
  speedMultiplier?: number;
  meta?: AtlasMeta;
  metadataUrl?: string;
  className?: string;
};

const defaultMetaUrl = "/static/sprites/cats/cats_duo_atlas.json";
let cachedMeta: AtlasMeta | null = null;

export function DuoCatSprite({
  clip,
  scale = 1,
  pause = false,
  speedMultiplier = 1,
  meta,
  metadataUrl = defaultMetaUrl,
  className,
}: DuoCatSpriteProps) {
  const [resolvedMeta, setResolvedMeta] = useState<AtlasMeta | null>(meta ?? cachedMeta);

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

  const activeClip = resolvedMeta?.clips[clip];
  const { frameId } = useSpriteAnimator(activeClip, { pause, speedMultiplier });
  const frameRect = useMemo(
    () => resolvedMeta?.frames.find((frame) => frame.id === frameId),
    [resolvedMeta, frameId]
  );

  if (!resolvedMeta || !activeClip || !frameRect) {
    return null;
  }

  const atlasWidth = resolvedMeta.cols * resolvedMeta.frameW;
  const atlasHeight = resolvedMeta.rows * resolvedMeta.frameH;
  const spriteWidth = resolvedMeta.frameW * scale;
  const spriteHeight = resolvedMeta.frameH * scale;

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0.8 }}
      animate={{ opacity: 1 }}
      whileHover={{ scale: 1.02 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      style={{
        width: `${spriteWidth}px`,
        height: `${spriteHeight}px`,
        backgroundImage: `url(${resolvedMeta.imagePath})`,
        backgroundRepeat: "no-repeat",
        backgroundSize: `${atlasWidth * scale}px ${atlasHeight * scale}px`,
        backgroundPosition: `${-frameRect.x * scale}px ${-frameRect.y * scale}px`,
        imageRendering: "pixelated",
      }}
    />
  );
}
