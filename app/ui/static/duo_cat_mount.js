(function () {
  "use strict";

  if (!window.React || !window.ReactDOM || !window.ReactDOM.createRoot) {
    return;
  }

  var React = window.React;
  var motion = window.Motion && window.Motion.motion ? window.Motion.motion : null;
  var h = React.createElement;
  var mounted = new Map();
  var metaCache = null;
  var metaPromise = null;
  var invalidMetaWarned = false;

  function isDebugLoggingEnabled() {
    if (typeof window === "undefined") {
      return false;
    }
    if (window.__DUO_CATS_DEBUG__ === true) {
      return true;
    }
    var host = window.location && window.location.hostname ? window.location.hostname : "";
    return host === "localhost" || host === "127.0.0.1";
  }

  function fetchMeta(url) {
    if (metaCache) {
      return Promise.resolve(metaCache);
    }
    if (!metaPromise) {
      metaPromise = fetch(url, { credentials: "same-origin" })
        .then(function (res) {
          return res.json();
        })
        .then(function (data) {
          metaCache = data;
          return data;
        });
    }
    return metaPromise;
  }

  function useSpriteAnimator(meta, clipName, paused, speed) {
    var clip = meta && meta.clips ? meta.clips[clipName] : null;
    var frameIds = clip && Array.isArray(clip.frames) ? clip.frames : [];
    var frameCount = frameIds.length;

    var frameById = React.useMemo(function () {
      var map = Object.create(null);
      if (!meta || !Array.isArray(meta.frames)) {
        return map;
      }
      for (var i = 0; i < meta.frames.length; i += 1) {
        var frame = meta.frames[i];
        map[frame.id] = frame;
      }
      return map;
    }, [meta]);

    var rafRef = React.useRef(null);
    var lastTsRef = React.useRef(null);
    var accMsRef = React.useRef(0);
    var frameIdxRef = React.useRef(0);

    var firstFrameId = frameCount > 0 ? frameIds[0] : null;
    var _a = React.useState(firstFrameId);
    var frameId = _a[0];
    var setFrameId = _a[1];

    var frameDurationMs = React.useMemo(function () {
      if (!clip || !clip.fps || speed <= 0) {
        return Number.POSITIVE_INFINITY;
      }
      return 1000 / (clip.fps * speed);
    }, [clip, speed]);

    React.useEffect(
      function () {
        frameIdxRef.current = 0;
        lastTsRef.current = null;
        accMsRef.current = 0;
        setFrameId(firstFrameId);
      },
      [firstFrameId, clipName, meta]
    );

    React.useEffect(
      function () {
        if (!clip || frameCount === 0 || paused || !Number.isFinite(frameDurationMs)) {
          if (rafRef.current !== null) {
            cancelAnimationFrame(rafRef.current);
            rafRef.current = null;
          }
          return undefined;
        }

        if (frameCount <= 1) {
          return undefined;
        }

        function tick(ts) {
          if (lastTsRef.current === null) {
            lastTsRef.current = ts;
          }

          var dt = ts - lastTsRef.current;
          lastTsRef.current = ts;
          accMsRef.current += Math.max(0, dt);

          var steps = Math.floor(accMsRef.current / frameDurationMs);
          if (steps > 0) {
            accMsRef.current -= steps * frameDurationMs;
            var prevIdx = frameIdxRef.current;
            var nextIdx = prevIdx;
            if (clip.loop) {
              nextIdx = (prevIdx + steps) % frameCount;
            } else {
              nextIdx = Math.min(prevIdx + steps, frameCount - 1);
            }

            frameIdxRef.current = nextIdx;
            if (nextIdx !== prevIdx) {
              setFrameId(frameIds[nextIdx]);
            }
          }

          rafRef.current = requestAnimationFrame(tick);
        }

        rafRef.current = requestAnimationFrame(tick);
        return function () {
          if (rafRef.current !== null) {
            cancelAnimationFrame(rafRef.current);
          }
          rafRef.current = null;
          lastTsRef.current = null;
          accMsRef.current = 0;
        };
      },
      [clip, frameCount, frameDurationMs, frameIds, paused]
    );

    var rect = frameId === null ? null : frameById[frameId] || null;
    return {
      frameId: frameId,
      rect: rect,
    };
  }

  function DuoCatSprite(props) {
    var _a = React.useState(props.meta || metaCache);
    var meta = _a[0];
    var setMeta = _a[1];

    var _b = React.useState(false);
    var isHovered = _b[0];
    var setIsHovered = _b[1];

    React.useEffect(
      function () {
        var cancelled = false;

        if (props.meta) {
          metaCache = props.meta;
          setMeta(props.meta);
          return undefined;
        }

        fetchMeta(props.metadataUrl || "/static/sprites/cats/cats_duo_atlas.json")
          .then(function (loaded) {
            if (!cancelled) {
              setMeta(loaded);
            }
          })
          .catch(function () {
            if (!cancelled) {
              setMeta(null);
            }
          });

        return function () {
          cancelled = true;
        };
      },
      [props.meta, props.metadataUrl]
    );

    var baseClip = props.clip || "duo_snuggle";
    var hoverClip = props.hoverClip || "duo_groom";
    var switchClipOnHover = props.switchClipOnHover !== false;
    var activeClipName =
      isHovered && switchClipOnHover && meta && meta.clips && meta.clips[hoverClip] ? hoverClip : baseClip;

    var paused = props.paused === true;
    var speed = Number.isFinite(props.speed) && props.speed > 0 ? props.speed : 1;

    var anim = useSpriteAnimator(meta, activeClipName, paused, speed);
    var debugFrameCounterRef = React.useRef(0);

    React.useEffect(
      function () {
        if (!isDebugLoggingEnabled() || !anim.rect || anim.frameId === null) {
          return;
        }
        debugFrameCounterRef.current += 1;
        if (debugFrameCounterRef.current % 30 === 0) {
          console.log(
            "[DuoCats]",
            "clip=" + String(activeClipName),
            "frameId=" + String(anim.frameId),
            "x=" + String(anim.rect.x),
            "y=" + String(anim.rect.y)
          );
        }
      },
      [activeClipName, anim.frameId, anim.rect]
    );

    if (!meta || !anim.rect) {
      return null;
    }

    var scale = Number.isFinite(props.scale) && props.scale > 0 ? props.scale : 0.25;
    var frameW = Number.isFinite(meta.frameW) ? meta.frameW : 0;
    var frameH = Number.isFinite(meta.frameH) ? meta.frameH : 0;
    var cols = Number.isFinite(meta.cols) ? meta.cols : 0;
    var rows = Number.isFinite(meta.rows) ? meta.rows : 0;
    var atlasW = frameW * cols;
    var atlasH = frameH * rows;
    if (!meta.imagePath || frameW <= 0 || frameH <= 0 || cols <= 0 || rows <= 0 || atlasW <= 0 || atlasH <= 0) {
      if (!invalidMetaWarned) {
        invalidMetaWarned = true;
        console.warn("[DuoCats] Invalid atlas metadata; sprite will not render.");
      }
      return null;
    }

    var scaledW = frameW * scale;
    var scaledH = frameH * scale;
    var scaledAtlasW = atlasW * scale;
    var scaledAtlasH = atlasH * scale;
    var scaledBgX = -anim.rect.x * scale;
    var scaledBgY = -anim.rect.y * scale;

    var wrapperStyle = {
      width: String(scaledW) + "px",
      height: String(scaledH) + "px",
      overflow: "hidden",
      transformOrigin: "center bottom",
    };

    var frameStyle = {
      width: "100%",
      height: "100%",
      backgroundImage: "url(" + String(meta.imagePath) + ")",
      backgroundRepeat: "no-repeat",
      backgroundSize: String(scaledAtlasW) + "px " + String(scaledAtlasH) + "px",
      // Atlas rects are sheet-space pixel offsets; negative x/y selects that frame cell.
      backgroundPosition: String(scaledBgX) + "px " + String(scaledBgY) + "px",
      imageRendering: "pixelated",
      willChange: "background-position",
    };

    var className = props.className || "duo-cat-sprite";
    var spriteClassName = props.spriteClassName || "duo-cat-sprite-frame";

    if (motion) {
      return h(
        motion.div,
        {
          className: className,
          style: wrapperStyle,
          initial: { opacity: 0.8 },
          animate: { opacity: 1 },
          whileHover: { scale: 1.02 },
          transition: { duration: 0.2, ease: "easeOut" },
          onHoverStart: function () {
            setIsHovered(true);
          },
          onHoverEnd: function () {
            setIsHovered(false);
          },
        },
        h("div", { className: spriteClassName, style: frameStyle })
      );
    }

    return h(
      "div",
      {
        className: className,
        style: wrapperStyle,
        onMouseEnter: function () {
          setIsHovered(true);
        },
        onMouseLeave: function () {
          setIsHovered(false);
        },
      },
      h("div", { className: spriteClassName, style: frameStyle })
    );
  }

  function readProps(node) {
    return {
      clip: node.dataset.clip || "duo_snuggle",
      hoverClip: node.dataset.hoverClip || "duo_groom",
      switchClipOnHover: node.dataset.hoverSwitch !== "false",
      scale: Number.parseFloat(node.dataset.scale || "0.25") || 0.25,
      paused: node.dataset.pause === "true",
      speed: Number.parseFloat(node.dataset.speed || "1") || 1,
      metadataUrl: node.dataset.metadataUrl || "/static/sprites/cats/cats_duo_atlas.json",
    };
  }

  function mountOne(node) {
    if (mounted.has(node)) {
      return;
    }
    var root = window.ReactDOM.createRoot(node);
    root.render(h(DuoCatSprite, readProps(node)));
    mounted.set(node, root);
  }

  function unmountOne(node) {
    var root = mounted.get(node);
    if (!root) {
      return;
    }
    root.unmount();
    mounted.delete(node);
  }

  function scan(scope) {
    var safeScope = scope || document;
    var nodes = Array.prototype.slice.call(safeScope.querySelectorAll("[data-duo-cat]"));
    if (safeScope.nodeType === 1 && safeScope.matches && safeScope.matches("[data-duo-cat]")) {
      nodes.unshift(safeScope);
    }
    return nodes;
  }

  function mountDuoCats(scope) {
    scan(scope).forEach(mountOne);
  }

  function unmountDuoCats(scope) {
    scan(scope).forEach(unmountOne);
  }

  function refreshOne(node) {
    unmountOne(node);
    mountOne(node);
  }

  window.DuoCats = {
    mount: mountDuoCats,
    unmount: unmountDuoCats,
    refresh: refreshOne,
  };

  document.addEventListener("DOMContentLoaded", function () {
    mountDuoCats(document);
  });

  if (document.body) {
    document.body.addEventListener("htmx:beforeSwap", function (event) {
      var target = event && event.detail && event.detail.target;
      if (target) {
        unmountDuoCats(target);
      }
    });

    document.body.addEventListener("htmx:afterSwap", function (event) {
      var target = event && event.detail && event.detail.target;
      if (target) {
        mountDuoCats(target);
      }
    });
  }
})();
