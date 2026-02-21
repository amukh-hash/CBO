(function () {
  "use strict";

  var nav = document.querySelector(".tree-nav.exact-tree-nav");
  if (!nav) {
    return;
  }

  var tabs = Array.prototype.slice.call(nav.querySelectorAll(".tree-tab.tree-hotspot:not(.hotspot-lock)"));
  if (!tabs.length) {
    return;
  }

  var states = new WeakMap();

  function getConnectSide(_tab) {
    // Keep all tags connected at the left edge (where label text starts).
    return "left";
  }

  function getLabelConnectPoint(labelRect, side) {
    return {
      x: side === "left" ? labelRect.left : labelRect.right,
      y: labelRect.top + labelRect.height / 2,
    };
  }

  function resolveLength(token, span) {
    var raw = (token || "").trim();
    if (!raw) {
      return 0;
    }
    if (raw.endsWith("%")) {
      return (Number.parseFloat(raw) || 0) * span / 100;
    }
    if (raw.endsWith("px")) {
      return Number.parseFloat(raw) || 0;
    }
    return Number.parseFloat(raw) || 0;
  }

  function getAnchor(tab, rect) {
    var styles = window.getComputedStyle(tab);
    var anchorX = resolveLength(styles.getPropertyValue("--anchor-x"), rect.width);
    var anchorY = resolveLength(styles.getPropertyValue("--anchor-y"), rect.height);
    return { x: anchorX, y: anchorY };
  }

  function applyTagState(tab, state) {
    tab.style.setProperty("--drag-x", String(state.dx) + "px");
    tab.style.setProperty("--drag-y", String(state.dy) + "px");

    // Negative X keeps the string direction aligned with cursor drag in CSS coordinates.
    var angle = Math.atan2(-state.dx, state.dy) * 180 / Math.PI;
    var length = Math.max(8, Math.hypot(state.dx, state.dy));
    var targetTilt = Math.max(-88, Math.min(88, angle));
    var now = (window.performance && window.performance.now) ? window.performance.now() : Date.now();
    var dt = Math.min(0.05, Math.max(0.001, (now - state.lastTickAt) / 1000));
    state.lastTickAt = now;

    // Critically damped-ish spring gives organic swing without snapping to fixed angles.
    var tiltStiffness = state.dragging ? 34 : 22;
    var tiltDamping = state.dragging ? 9.5 : 7.2;
    var tiltAccel = (targetTilt - state.pullTilt) * tiltStiffness - state.pullTiltVelocity * tiltDamping;
    state.pullTiltVelocity += tiltAccel * dt;
    state.pullTilt += state.pullTiltVelocity * dt;

    if (!state.dragging && Math.abs(targetTilt - state.pullTilt) < 0.12 && Math.abs(state.pullTiltVelocity) < 0.1) {
      state.pullTilt = targetTilt;
      state.pullTiltVelocity = 0;
    }

    tab.style.setProperty("--string-angle", String(angle) + "deg");
    tab.style.setProperty("--string-len", String(length) + "px");
    tab.style.setProperty("--pull-tilt", String(state.pullTilt) + "deg");
  }

  function refreshAllAnchors() {
    tabs.forEach(function (tab) {
      var state = states.get(tab);
      if (!state || state.dragging) {
        return;
      }
      getAnchor(tab, tab.getBoundingClientRect());
      applyTagState(tab, state);
    });
  }

  function stopAnimation(state) {
    if (!state.raf) {
      return;
    }
    window.cancelAnimationFrame(state.raf);
    state.raf = 0;
  }

  function springBack(tab, state) {
    stopAnimation(state);

    function step() {
      // Tuned for a slower, more playful oscillation before settling.
      var stiffness = 0.13;
      var damping = 0.87;
      var tx = state.restX;
      var ty = state.restY;

      state.vx = (state.vx + (tx - state.dx) * stiffness) * damping;
      state.vy = (state.vy + (ty - state.dy) * stiffness) * damping;
      state.dx += state.vx;
      state.dy += state.vy;

      applyTagState(tab, state);

      if (
        Math.abs(tx - state.dx) < 0.2 &&
        Math.abs(ty - state.dy) < 0.2 &&
        Math.abs(state.vx) < 0.08 &&
        Math.abs(state.vy) < 0.08
      ) {
        state.dx = tx;
        state.dy = ty;
        state.vx = 0;
        state.vy = 0;
        applyTagState(tab, state);
        state.raf = 0;
        return;
      }

      state.raf = window.requestAnimationFrame(step);
    }

    state.raf = window.requestAnimationFrame(step);
  }

  function activateTab(tab) {
    var evt = new CustomEvent("tree-tag-activate", {
      bubbles: true,
      cancelable: true,
    });
    tab.dispatchEvent(evt);
  }

  tabs.forEach(function (tab) {
    var label = tab.querySelector(".hotspot-label");
    if (!label) {
      return;
    }

    var styles = window.getComputedStyle(tab);
    var restX = resolveLength(styles.getPropertyValue("--rest-x"), 1);
    var restY = resolveLength(styles.getPropertyValue("--rest-y"), 1);
    var state = {
      dx: restX,
      dy: restY,
      restX: restX,
      restY: restY,
      vx: 0,
      vy: 0,
      raf: 0,
      pointerId: null,
      dragging: false,
      moved: false,
      startX: 0,
      startY: 0,
      grabOffsetX: 0,
      grabOffsetY: 0,
      connectSide: getConnectSide(tab),
      pullTilt: 0,
      pullTiltVelocity: 0,
      lastTickAt: (window.performance && window.performance.now) ? window.performance.now() : Date.now(),
      lastTapAt: 0,
    };
    states.set(tab, state);
    getAnchor(tab, tab.getBoundingClientRect());
    applyTagState(tab, state);

    label.addEventListener("pointerdown", function (event) {
      if (event.button !== 0) {
        return;
      }
      stopAnimation(state);

      state.pointerId = event.pointerId;
      state.dragging = true;
      state.moved = false;
      state.startX = event.clientX;
      state.startY = event.clientY;
      var labelRect = label.getBoundingClientRect();
      var connectPoint = getLabelConnectPoint(labelRect, state.connectSide);
      state.grabOffsetX = event.clientX - connectPoint.x;
      state.grabOffsetY = event.clientY - connectPoint.y;

      if (label.setPointerCapture) {
        label.setPointerCapture(event.pointerId);
      }

      event.preventDefault();
      event.stopPropagation();
    });

    label.addEventListener("pointermove", function (event) {
      if (!state.dragging || state.pointerId !== event.pointerId) {
        return;
      }

      var rect = tab.getBoundingClientRect();
      var anchor = getAnchor(tab, rect);
      var localX = event.clientX - state.grabOffsetX - rect.left;
      var localY = event.clientY - state.grabOffsetY - rect.top;

      state.dx = localX - anchor.x;
      state.dy = localY - anchor.y;

      var clampX = rect.width * 1.15;
      var clampY = rect.height * 1.35;
      state.dx = Math.max(-clampX, Math.min(clampX, state.dx));
      state.dy = Math.max(6, Math.min(clampY, state.dy));

      if (!state.moved) {
        state.moved =
          Math.abs(event.clientX - state.startX) > 3 ||
          Math.abs(event.clientY - state.startY) > 3;
      }

      applyTagState(tab, state);
      event.preventDefault();
      event.stopPropagation();
    });

    function onPointerEnd(event) {
      if (state.pointerId !== event.pointerId) {
        return;
      }

      if (label.releasePointerCapture) {
        try {
          label.releasePointerCapture(event.pointerId);
        } catch (_err) {
          // no-op: safe to ignore stale capture release
        }
      }

      var dragged = state.moved;
      state.dragging = false;
      state.pointerId = null;
      state.moved = false;

      if (!dragged) {
        var now = Date.now();
        if (now - state.lastTapAt < 320) {
          state.lastTapAt = 0;
          activateTab(tab);
        } else {
          state.lastTapAt = now;
        }
      } else {
        state.lastTapAt = 0;
      }

      springBack(tab, state);
      event.preventDefault();
      event.stopPropagation();
    }

    label.addEventListener("pointerup", onPointerEnd);
    label.addEventListener("pointercancel", onPointerEnd);
  });

  // Re-sync anchors after layout settles; before this, absolute percentages can
  // be slightly off compared to the visible grid due to late sizing.
  window.addEventListener("resize", refreshAllAnchors);
  window.addEventListener("load", refreshAllAnchors);
  window.requestAnimationFrame(function () {
    window.requestAnimationFrame(refreshAllAnchors);
  });
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(refreshAllAnchors)["catch"](function () {
      // no-op
    });
  }
})();
