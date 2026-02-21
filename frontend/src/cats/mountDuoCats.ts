import React from "react";
import { createRoot, type Root } from "react-dom/client";

import { DuoCatSprite } from "./DuoCatSprite";

const mounted = new Map<HTMLElement, Root>();

function isDebugLoggingEnabled(): boolean {
  if (typeof window === "undefined") return false;
  if ((window as { __DUO_CATS_DEBUG__?: boolean }).__DUO_CATS_DEBUG__ === true) return true;
  const host = window.location?.hostname ?? "";
  return host === "localhost" || host === "127.0.0.1";
}

function readBoolean(value: string | undefined, defaultValue: boolean): boolean {
  if (typeof value !== "string") return defaultValue;
  const normalized = value.trim().toLowerCase();
  if (normalized === "false") return false;
  if (normalized === "true") return true;
  return defaultValue;
}

function readCsvList(value: string | undefined, fallback: string[]): string[] {
  if (typeof value !== "string") return fallback.slice();
  const parsed = value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
  return parsed.length > 0 ? parsed : fallback.slice();
}

function readProps(node: HTMLElement) {
  return {
    clip: node.dataset.clip ?? "snuggle_idle",
    hoverClip: node.dataset.hoverClip ?? "nose_boop",
    switchClipOnHover: node.dataset.hoverSwitch !== "false",
    scale: Number.parseFloat(node.dataset.scale ?? "0.25") || 0.25,
    paused: node.dataset.pause === "true",
    speed: Number.parseFloat(node.dataset.speed ?? "1") || 1,
    metadataUrl: node.dataset.metadataUrl ?? "/static/sprites/cats/cats_duo_pack.json?v=cat-tree-41",
    playlist: node.dataset.playlist ?? "ambient_random",
    playlistEnabled: readBoolean(node.dataset.playlistEnabled, true),
    clickQueue: readCsvList(node.dataset.clickQueue, ["mutual_groom", "paw_batting", "snuggle_curl"]),
  };
}

function mountOne(node: HTMLElement): void {
  if (mounted.has(node)) return;
  const props = readProps(node);
  if (isDebugLoggingEnabled()) {
    console.log("[DuoCats][mount-props]", {
      playlist: props.playlist,
      playlistEnabled: props.playlistEnabled,
      clip: props.clip,
      hoverClip: props.hoverClip,
      clickQueue: props.clickQueue,
    });
  }
  const root = createRoot(node);
  root.render(<DuoCatSprite {...props} />);
  mounted.set(node, root);
}

function unmountOne(node: HTMLElement): void {
  const root = mounted.get(node);
  if (!root) return;
  root.unmount();
  mounted.delete(node);
}

function scan(scope: ParentNode = document): HTMLElement[] {
  const nodes = Array.from(scope.querySelectorAll<HTMLElement>("[data-duo-cat]"));
  if (scope instanceof HTMLElement && scope.matches("[data-duo-cat]")) {
    nodes.unshift(scope);
  }
  return nodes;
}

export function mountDuoCats(scope?: ParentNode): void {
  scan(scope ?? document).forEach(mountOne);
}

export function unmountDuoCats(scope?: ParentNode): void {
  scan(scope ?? document).forEach(unmountOne);
}

export function refreshDuoCat(node: HTMLElement): void {
  unmountOne(node);
  mountOne(node);
}

document.addEventListener("DOMContentLoaded", () => {
  mountDuoCats(document);
});

document.body.addEventListener("htmx:beforeSwap", (event: Event) => {
  const target = (event as CustomEvent).detail?.target as ParentNode | undefined;
  if (!target) return;
  unmountDuoCats(target);
});

document.body.addEventListener("htmx:afterSwap", (event: Event) => {
  const target = (event as CustomEvent).detail?.target as ParentNode | undefined;
  if (!target) return;
  mountDuoCats(target);
});
