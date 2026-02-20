import React from "react";
import { createRoot, type Root } from "react-dom/client";

import { DuoCatSprite } from "./DuoCatSprite";

const mounted = new Map<HTMLElement, Root>();

function readProps(node: HTMLElement) {
  return {
    clip: node.dataset.clip ?? "duo_snuggle",
    hoverClip: node.dataset.hoverClip ?? "duo_groom",
    switchClipOnHover: node.dataset.hoverSwitch !== "false",
    scale: Number.parseFloat(node.dataset.scale ?? "0.25") || 0.25,
    paused: node.dataset.pause === "true",
    speed: Number.parseFloat(node.dataset.speed ?? "1") || 1,
    metadataUrl: node.dataset.metadataUrl ?? "/static/sprites/cats/cats_duo_atlas.json",
  };
}

function mountOne(node: HTMLElement): void {
  if (mounted.has(node)) return;
  const root = createRoot(node);
  root.render(<DuoCatSprite {...readProps(node)} />);
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
