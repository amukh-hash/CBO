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

  function resolveDefaultClip(meta) {
    if (!meta || !meta.clips) {
      return "";
    }
    if (meta.default_clip && meta.clips[meta.default_clip]) {
      return meta.default_clip;
    }
    if (meta.clips.duo_snuggle) {
      return "duo_snuggle";
    }
    if (meta.clips.snuggle_idle) {
      return "snuggle_idle";
    }
    var keys = Object.keys(meta.clips);
    return keys.length > 0 ? keys[0] : "";
  }

  function useSpriteAnimator(meta, clipName, paused, speed, onDone, playNonce) {
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
    var doneRef = React.useRef(false);
    var doneNonceRef = React.useRef(null);

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
        doneRef.current = false;
        doneNonceRef.current = playNonce;
        setFrameId(firstFrameId);
      },
      [firstFrameId, clipName, meta, playNonce]
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
          if (!clip.loop && !doneRef.current && typeof onDone === "function" && doneNonceRef.current === playNonce) {
            doneRef.current = true;
            onDone(clipName);
          }
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
      [clip, clipName, frameCount, frameDurationMs, frameIds, onDone, paused, playNonce]
    );

    var rect = null;
    if (frameId !== null) {
      rect = frameById[frameId] || null;
      // Fallback for numeric frame IDs if metadata frame rect lookup is missing.
      if (!rect && meta && Number.isFinite(meta.frameW) && Number.isFinite(meta.frameH) && Number.isFinite(meta.cols)) {
        var idx = typeof frameId === "number" ? frameId : parseInt(frameId, 10);
        if (Number.isFinite(idx)) {
          var col = idx % meta.cols;
          var row = Math.floor(idx / meta.cols);
          rect = {
            x: col * meta.frameW,
            y: row * meta.frameH,
            w: meta.frameW,
            h: meta.frameH,
          };
        }
      }
    }
    return {
      frameId: frameId,
      rect: rect,
    };
  }

  function useDuoCatClipController(meta) {
    var defaultClip = React.useMemo(
      function () {
        return resolveDefaultClip(meta);
      },
      [meta]
    );

    var _a = React.useState(defaultClip);
    var clipName = _a[0];
    var setClipName = _a[1];

    var _b = React.useState(0);
    var playNonce = _b[0];
    var setPlayNonce = _b[1];

    var pendingRef = React.useRef(Promise.resolve());
    var inQueueRef = React.useRef(false);
    var resolveRef = React.useRef(null);

    React.useEffect(
      function () {
        if (!meta || !meta.clips || !meta.clips[clipName]) {
          setClipName(defaultClip);
          setPlayNonce(function (prev) {
            return prev + 1;
          });
        }
      },
      [clipName, defaultClip, meta]
    );

    var setIdle = React.useCallback(function () {
      if (!defaultClip) {
        return;
      }
      setClipName(defaultClip);
      setPlayNonce(function (prev) {
        return prev + 1;
      });
    }, [defaultClip]);

    var playOnce = React.useCallback(
      function (name) {
        return new Promise(function (resolve) {
          if (!meta || !meta.clips || !meta.clips[name]) {
            if (resolveRef.current) {
              resolveRef.current();
              resolveRef.current = null;
            }
            resolve();
            return;
          }

          if (resolveRef.current) {
            resolveRef.current();
          }
          resolveRef.current = function () {
            resolveRef.current = null;
            resolve();
          };

          setClipName(name);
          setPlayNonce(function (prev) {
            return prev + 1;
          });

          var clip = meta.clips[name];
          if (!clip || clip.loop || !Array.isArray(clip.frames) || clip.frames.length <= 1) {
            if (resolveRef.current) {
              resolveRef.current();
            }
          }
        });
      },
      [meta]
    );

    var queue = React.useCallback(
      function (names) {
        var safeNames = Array.isArray(names) ? names.slice() : [];
        pendingRef.current = pendingRef.current.then(function () {
          inQueueRef.current = true;
          var chain = Promise.resolve();
          safeNames.forEach(function (name) {
            chain = chain.then(function () {
              return playOnce(name);
            });
          });
          return chain
            .catch(function () {
              return undefined;
            })
            .then(function () {
              inQueueRef.current = false;
              setIdle();
            });
        });
        return pendingRef.current;
      },
      [playOnce, setIdle]
    );

    var onDone = React.useCallback(
      function (doneClipName) {
        if (resolveRef.current) {
          resolveRef.current();
        }
        if (inQueueRef.current) {
          return;
        }
        var doneClip = meta && meta.clips ? meta.clips[doneClipName] : null;
        var returnTo = doneClip && doneClip.return_to && meta.clips[doneClip.return_to] ? doneClip.return_to : defaultClip;
        if (!returnTo) {
          return;
        }
        setClipName(returnTo);
        setPlayNonce(function (prev) {
          return prev + 1;
        });
      },
      [defaultClip, meta]
    );

    return {
      clipName: clipName,
      playNonce: playNonce,
      onDone: onDone,
      setIdle: setIdle,
      playOnce: playOnce,
      queue: queue,
    };
  }

  function DuoCatSprite(props) {
    var _a = React.useState(props.meta || metaCache);
    var meta = _a[0];
    var setMeta = _a[1];

    var hoverPlayedRef = React.useRef(false);
    var initialClipAppliedRef = React.useRef(false);

    React.useEffect(
      function () {
        initialClipAppliedRef.current = false;
      },
      [meta]
    );

    React.useEffect(
      function () {
        var cancelled = false;

        if (props.meta) {
          metaCache = props.meta;
          setMeta(props.meta);
          return undefined;
        }

        fetchMeta(props.metadataUrl || "/static/sprites/cats/cats_duo_pack.json")
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

    var ctrl = useDuoCatClipController(meta);
    var baseClip = props.clip || "";
    var baseClipExists = !!(meta && meta.clips && baseClip && meta.clips[baseClip]);
    var hoverClip = props.hoverClip || "nose_boop";
    var hoverClipExists = !!(meta && meta.clips && hoverClip && meta.clips[hoverClip]);
    var switchClipOnHover = props.switchClipOnHover !== false;

    React.useEffect(
      function () {
        if (!meta || !meta.clips) {
          return;
        }
        if (initialClipAppliedRef.current) {
          return;
        }
        initialClipAppliedRef.current = true;
        if (baseClipExists) {
          var baseCfg = meta.clips[baseClip];
          ctrl.playOnce(baseClip).then(function () {
            if (!baseCfg || !baseCfg.loop) {
              ctrl.setIdle();
            }
          });
          return;
        }
        ctrl.setIdle();
      },
      [baseClip, baseClipExists, ctrl.playOnce, ctrl.setIdle, meta]
    );

    React.useEffect(
      function () {
        if (!meta || !meta.clips || typeof props.onController !== "function") {
          return;
        }
        props.onController({
          playOnce: ctrl.playOnce,
          queue: ctrl.queue,
          setIdle: ctrl.setIdle,
        });
      },
      [ctrl.playOnce, ctrl.queue, ctrl.setIdle, meta, props.onController]
    );

    var paused = props.paused === true;
    var speed = Number.isFinite(props.speed) && props.speed > 0 ? props.speed : 1;

    var anim = useSpriteAnimator(meta, ctrl.clipName, paused, speed, ctrl.onDone, ctrl.playNonce);
    var debugFrameCounterRef = React.useRef(0);

    React.useEffect(
      function () {
        if (!isDebugLoggingEnabled() || !anim.rect || anim.frameId === null || !meta || !meta.clips) {
          return;
        }
        var debugClip = meta.clips[ctrl.clipName];
        var debugImagePath = debugClip && debugClip.imagePath ? debugClip.imagePath : meta.imagePath;
        var debugScale = Number.isFinite(props.scale) && props.scale > 0 ? props.scale : 0.25;
        var debugAtlasW = (Number.isFinite(meta.frameW) ? meta.frameW : 0) * (Number.isFinite(meta.cols) ? meta.cols : 0);
        var debugAtlasH = (Number.isFinite(meta.frameH) ? meta.frameH : 0) * (Number.isFinite(meta.rows) ? meta.rows : 0);
        var debugBgPos = String(-anim.rect.x * debugScale) + "px " + String(-anim.rect.y * debugScale) + "px";
        var debugBgSize = String(debugAtlasW * debugScale) + "px " + String(debugAtlasH * debugScale) + "px";
        debugFrameCounterRef.current += 1;
        if (debugFrameCounterRef.current % 5 === 0) {
          console.log(
            "[DuoCats][frame]",
            "clip=" + String(ctrl.clipName),
            "frameId=" + String(anim.frameId),
            "x=" + String(anim.rect.x),
            "y=" + String(anim.rect.y),
            "bgPos=" + debugBgPos,
            "bgSize=" + debugBgSize,
            "img=" + String(debugImagePath),
            "fps=" + String(debugClip && debugClip.fps),
            "loop=" + String(debugClip && debugClip.loop)
          );
        }
      },
      [anim.frameId, anim.rect, ctrl.clipName, meta, props.scale]
    );

    if (!meta || !anim.rect || !meta.clips || !meta.clips[ctrl.clipName]) {
      return null;
    }

    var scale = Number.isFinite(props.scale) && props.scale > 0 ? props.scale : 0.25;
    var frameW = Number.isFinite(meta.frameW) ? meta.frameW : 0;
    var frameH = Number.isFinite(meta.frameH) ? meta.frameH : 0;
    var cols = Number.isFinite(meta.cols) ? meta.cols : 0;
    var rows = Number.isFinite(meta.rows) ? meta.rows : 0;
    var atlasW = frameW * cols;
    var atlasH = frameH * rows;
    var activeClip = meta.clips[ctrl.clipName];
    var clipImagePath = activeClip && activeClip.imagePath ? activeClip.imagePath : meta.imagePath;
    if (!clipImagePath || frameW <= 0 || frameH <= 0 || cols <= 0 || rows <= 0 || atlasW <= 0 || atlasH <= 0) {
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
      backgroundImage: "url(" + String(clipImagePath) + ")",
      backgroundRepeat: "no-repeat",
      backgroundSize: String(scaledAtlasW) + "px " + String(scaledAtlasH) + "px",
      // Atlas rects are sheet-space pixel offsets; negative x/y selects that frame cell.
      backgroundPosition: String(scaledBgX) + "px " + String(scaledBgY) + "px",
      imageRendering: "pixelated",
      willChange: "background-position",
    };

    var className = props.className || "duo-cat-sprite";
    var spriteClassName = props.spriteClassName || "duo-cat-sprite-frame";
    var handleHoverStart = function () {
      if (!switchClipOnHover || !hoverClipExists) {
        return;
      }
      if (hoverPlayedRef.current) {
        return;
      }
      hoverPlayedRef.current = true;
      ctrl.playOnce(hoverClip);
    };
    var handleHoverEnd = function () {
      hoverPlayedRef.current = false;
      ctrl.setIdle();
    };

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
          onHoverStart: handleHoverStart,
          onHoverEnd: handleHoverEnd,
        },
        h("div", { className: spriteClassName, style: frameStyle })
      );
    }

    return h(
      "div",
      {
        className: className,
        style: wrapperStyle,
        onMouseEnter: handleHoverStart,
        onMouseLeave: handleHoverEnd,
      },
      h("div", { className: spriteClassName, style: frameStyle })
    );
  }

  function readProps(node) {
    return {
      clip: node.dataset.clip || "snuggle_idle",
      hoverClip: node.dataset.hoverClip || "nose_boop",
      switchClipOnHover: node.dataset.hoverSwitch !== "false",
      scale: Number.parseFloat(node.dataset.scale || "0.25") || 0.25,
      paused: node.dataset.pause === "true",
      speed: Number.parseFloat(node.dataset.speed || "1") || 1,
      metadataUrl: node.dataset.metadataUrl || "/static/sprites/cats/cats_duo_pack.json",
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
