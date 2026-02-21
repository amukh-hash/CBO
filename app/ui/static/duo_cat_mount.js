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
  var DUO_PACK_VERSION = "cat-tree-41";
  var DEFAULT_META_URL = "/static/sprites/cats/cats_duo_pack.json?v=" + DUO_PACK_VERSION;

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
    if (meta.clips.snuggle_idle) {
      return "snuggle_idle";
    }
    if (meta.clips.duo_snuggle) {
      return "duo_snuggle";
    }
    var keys = Object.keys(meta.clips);
    return keys.length > 0 ? keys[0] : "";
  }

  function clipFrameCount(clip) {
    if (!clip) {
      return 0;
    }
    if (Array.isArray(clip.timeline) && clip.timeline.length > 0) {
      return clip.timeline.length;
    }
    if (typeof clip.frame_count === "number" && clip.frame_count > 0) {
      return clip.frame_count;
    }
    if (Array.isArray(clip.frames)) {
      return clip.frames.length;
    }
    return 0;
  }

  function rectFromCell(meta, cellIndex) {
    var col = cellIndex % meta.cols;
    var row = Math.floor(cellIndex / meta.cols);
    return {
      id: cellIndex,
      x: col * meta.frameW,
      y: row * meta.frameH,
      w: meta.frameW,
      h: meta.frameH,
    };
  }

  function useSpriteAnimator(meta, clipName, paused, speed, onDone, playNonce) {
    var clip = meta && meta.clips ? meta.clips[clipName] : null;
    var frameCount = clipFrameCount(clip);

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

    var _a = React.useState(0);
    var frameIndex = _a[0];
    var setFrameIndex = _a[1];

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
        setFrameIndex(0);
      },
      [clipName, meta, playNonce]
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
              setFrameIndex(nextIdx);
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
      [clip, clipName, frameCount, frameDurationMs, onDone, paused, playNonce]
    );

    return React.useMemo(
      function () {
        if (!clip || !meta || frameCount <= 0) {
          return {
            frameId: null,
            frameIndex: 0,
            rect: null,
            imagePath: null,
            pageIndex: null,
            cellIndex: null,
          };
        }

        var resolvedIndex = Math.max(0, Math.min(frameIndex, frameCount - 1));
        var fallbackImagePath = clip && clip.imagePath ? clip.imagePath : meta.imagePath || null;

        if (Array.isArray(clip.timeline) && clip.timeline.length > 0) {
          var entry = clip.timeline[resolvedIndex];
          var pageIndex = Array.isArray(entry) && typeof entry[0] === "number" ? entry[0] : -1;
          var cellIndex = Array.isArray(entry) && typeof entry[1] === "number" ? entry[1] : -1;
          var rect = null;
          if (cellIndex >= 0) {
            rect = rectFromCell(meta, cellIndex);
          }
          var pagePath = null;
          if (pageIndex >= 0 && Array.isArray(clip.pages) && clip.pages[pageIndex]) {
            pagePath = clip.pages[pageIndex].imagePath || null;
          }
          return {
            frameId: null,
            frameIndex: resolvedIndex,
            rect: rect,
            imagePath: pagePath || fallbackImagePath,
            pageIndex: pageIndex >= 0 ? pageIndex : null,
            cellIndex: cellIndex >= 0 ? cellIndex : null,
          };
        }

        var frameIds = clip && Array.isArray(clip.frames) ? clip.frames : [];
        var frameId = frameIds[resolvedIndex];
        var legacyRect = null;
        if (typeof frameId === "number") {
          legacyRect = frameById[frameId] || null;
          if (!legacyRect && Number.isFinite(meta.frameW) && Number.isFinite(meta.frameH) && Number.isFinite(meta.cols)) {
            legacyRect = rectFromCell(meta, frameId);
          }
        }
        return {
          frameId: typeof frameId === "number" ? frameId : null,
          frameIndex: resolvedIndex,
          rect: legacyRect,
          imagePath: fallbackImagePath,
          pageIndex: null,
          cellIndex: typeof frameId === "number" ? frameId : null,
        };
      },
      [clip, frameById, frameCount, frameIndex, meta]
    );
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
          if (!clip || clip.loop || clipFrameCount(clip) <= 1) {
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

    var isBusy = React.useCallback(function () {
      return inQueueRef.current || resolveRef.current !== null;
    }, []);

    return {
      clipName: clipName,
      playNonce: playNonce,
      onDone: onDone,
      setIdle: setIdle,
      playOnce: playOnce,
      queue: queue,
      isBusy: isBusy,
    };
  }

  function clampMs(value, fallback) {
    var safeFallback = typeof fallback === "number" && Number.isFinite(fallback) ? Math.max(0, Math.floor(fallback)) : 0;
    if (typeof value !== "number" || !Number.isFinite(value)) {
      return safeFallback;
    }
    return Math.max(0, Math.floor(value));
  }

  function randomRange(range, fallback) {
    var safeFallback = clampMs(fallback, 0);
    if (!Array.isArray(range) || range.length !== 2) {
      return safeFallback;
    }
    var min = clampMs(range[0], safeFallback);
    var max = clampMs(range[1], safeFallback);
    if (max <= min) {
      return min;
    }
    return min + Math.floor(Math.random() * (max - min + 1));
  }

  function weightedPick(pool) {
    if (!Array.isArray(pool) || pool.length === 0) {
      return null;
    }
    var total = 0;
    for (var i = 0; i < pool.length; i += 1) {
      var pair = pool[i];
      if (!Array.isArray(pair) || pair.length !== 2) {
        continue;
      }
      var weight = pair[1];
      if (typeof weight === "number" && Number.isFinite(weight) && weight > 0) {
        total += weight;
      }
    }
    if (total <= 0) {
      return null;
    }

    var cursor = Math.random() * total;
    for (var j = 0; j < pool.length; j += 1) {
      var entry = pool[j];
      if (!Array.isArray(entry) || entry.length !== 2) {
        continue;
      }
      var clip = entry[0];
      var w = entry[1];
      if (typeof w !== "number" || !Number.isFinite(w) || w <= 0) {
        continue;
      }
      cursor -= w;
      if (cursor <= 0) {
        return clip;
      }
    }
    var last = pool[pool.length - 1];
    return Array.isArray(last) && typeof last[0] === "string" ? last[0] : null;
  }

  function waitMs(ms, cancelledRef) {
    var duration = Math.max(0, Math.floor(ms));
    if (duration <= 0) {
      return Promise.resolve();
    }
    return new Promise(function (resolve) {
      var timer = window.setTimeout(resolve, duration);
      if (cancelledRef.current) {
        window.clearTimeout(timer);
        resolve();
      }
    });
  }

  function useDuoCatPlaylist(meta, controller, playlistName, enabled) {
    var nextPickAtRef = React.useRef(0);
    var phaseRef = React.useRef("enter_idle");
    var sequenceIndexRef = React.useRef(0);

    var playlist = React.useMemo(
      function () {
        if (!meta || !meta.library || !meta.library.playlists || !playlistName) {
          return null;
        }
        return meta.library.playlists[playlistName] || null;
      },
      [meta, playlistName]
    );

    React.useEffect(
      function () {
        if (!enabled || !meta || !playlist || !meta.clips) {
          return undefined;
        }

        var debug = isDebugLoggingEnabled();
        var cancelledRef = { current: false };
        var foundation = meta.library && meta.library.foundation ? meta.library.foundation : null;
        var idleClip = playlist.idle_clip || foundation || meta.default_clip || "snuggle_idle";
        nextPickAtRef.current = 0;
        phaseRef.current = "enter_idle";
        sequenceIndexRef.current = 0;

        function isBusy() {
          if (!controller || typeof controller.isBusy !== "function") {
            return false;
          }
          try {
            return !!controller.isBusy();
          } catch (_err) {
            return false;
          }
        }

        function readIdleHoldMs() {
          if (playlist.mode === "sequence") {
            return clampMs(playlist.idle_hold_ms, 0);
          }
          return randomRange(playlist.idle_hold_ms_range, 0);
        }

        function readBetweenHoldMs() {
          if (playlist.mode === "sequence") {
            return clampMs(playlist.between_hold_ms, 0);
          }
          return randomRange(playlist.between_hold_ms_range, 0);
        }

        function pickNextClip() {
          if (playlist.mode === "sequence") {
            if (Array.isArray(playlist.clips) && playlist.clips.length > 0) {
              var sequenceClip = playlist.clips[sequenceIndexRef.current % playlist.clips.length] || null;
              sequenceIndexRef.current += 1;
              return sequenceClip;
            }
            return null;
          }
          if (playlist.mode === "weighted_random") {
            return weightedPick(playlist.pool);
          }
          return null;
        }

        function setNextPickDelay(delayMs) {
          nextPickAtRef.current = Date.now() + clampMs(delayMs, 0);
        }

        if (debug) {
          console.log(
            "[DuoCats][playlist]",
            "start",
            "playlist=" + String(playlistName || ""),
            "mode=" + String(playlist.mode),
            "idleClip=" + String(idleClip),
            "phase=" + String(phaseRef.current)
          );
        }

        function run() {
          if (cancelledRef.current) {
            return;
          }

          var now = Date.now();
          var busy = isBusy();
          var delayUntilPick = Math.max(0, nextPickAtRef.current - now);

          if (debug) {
            console.log(
              "[DuoCats][playlist]",
              "tick",
              "playlist=" + String(playlistName || ""),
              "mode=" + String(playlist.mode),
              "idleClip=" + String(idleClip),
              "phase=" + String(phaseRef.current),
              "busy=" + String(busy),
              "waitMs=" + String(delayUntilPick)
            );
          }

          if (busy) {
            waitMs(120, cancelledRef).then(function () {
              if (!cancelledRef.current) {
                run();
              }
            });
            return;
          }

          if (delayUntilPick > 0) {
            waitMs(Math.min(delayUntilPick, 250), cancelledRef).then(function () {
              if (!cancelledRef.current) {
                run();
              }
            });
            return;
          }

          if (phaseRef.current === "enter_idle") {
            var idlePromise;
            if (meta.clips[idleClip]) {
              idlePromise = controller.playOnce(idleClip);
            } else {
              controller.setIdle();
              idlePromise = Promise.resolve();
            }

            idlePromise
              .catch(function () {
                return undefined;
              })
              .then(function () {
                if (cancelledRef.current) {
                  return;
                }
                phaseRef.current = "pick_clip";
                setNextPickDelay(readIdleHoldMs());
              })
              .then(function () {
                if (!cancelledRef.current) {
                  run();
                }
              });
            return;
          }

          var nextClip = pickNextClip();
          if (debug) {
            console.log(
              "[DuoCats][playlist]",
              "next",
              "playlist=" + String(playlistName || ""),
              "clip=" + String(nextClip || "")
            );
          }

          var playPromise = Promise.resolve();
          if (nextClip && meta.clips[nextClip]) {
            playPromise = controller.playOnce(nextClip).then(function () {
              if (cancelledRef.current) {
                return undefined;
              }
              var holdLast = clampMs(meta.clips[nextClip].hold_last_ms, 0);
              if (holdLast > 0) {
                return waitMs(holdLast, cancelledRef);
              }
              return undefined;
            });
          }

          playPromise
            .catch(function () {
              return undefined;
            })
            .then(function () {
              if (cancelledRef.current) {
                return;
              }
              phaseRef.current = "enter_idle";
              setNextPickDelay(readBetweenHoldMs());
            })
            .then(function () {
              if (!cancelledRef.current) {
                run();
              }
            });
        }

        run();
        return function () {
          cancelledRef.current = true;
          nextPickAtRef.current = 0;
          if (debug) {
            console.log("[DuoCats][playlist]", "stop", "playlist=" + String(playlistName || ""));
          }
        };
      },
      [controller.isBusy, controller.playOnce, controller.setIdle, enabled, meta, playlist, playlistName]
    );
  }

  function DuoCatSprite(props) {
    var _a = React.useState(props.meta || metaCache);
    var meta = _a[0];
    var setMeta = _a[1];
    var _b = React.useState(false);
    var playlistSuspended = _b[0];
    var setPlaylistSuspended = _b[1];

    var hoverPlayedRef = React.useRef(false);
    var initialClipAppliedRef = React.useRef(false);
    var activeUserActionsRef = React.useRef(0);
    var mountLoggedRef = React.useRef(false);
    var wrapperNodeRef = React.useRef(null);
    var frameNodeRef = React.useRef(null);
    var metaShapeWarnedRef = React.useRef(false);
    var motionProbeActiveRef = React.useRef(false);
    var motionProbeTimerRef = React.useRef(null);
    var motionProbeRectsRef = React.useRef(Object.create(null));
    var motionProbeFailureRef = React.useRef(Object.create(null));

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

        fetchMeta(props.metadataUrl || DEFAULT_META_URL)
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
    var playlistName = props.playlist || "ambient_random";
    var playlistEnabled = props.playlistEnabled !== false;
    var playlistRunnerEnabled = playlistEnabled && !playlistSuspended;
    useDuoCatPlaylist(
      meta,
      { playOnce: ctrl.playOnce, setIdle: ctrl.setIdle, isBusy: ctrl.isBusy },
      playlistName,
      playlistRunnerEnabled
    );

    var baseClip = props.clip || (meta && meta.default_clip) || "snuggle_idle";
    var baseClipExists = !!(meta && meta.clips && baseClip && meta.clips[baseClip]);
    var hoverClip = props.hoverClip || "nose_boop";
    var hoverClipExists = !!(meta && meta.clips && hoverClip && meta.clips[hoverClip]);
    var switchClipOnHover = props.switchClipOnHover !== false;
    var idleProbeClip = baseClipExists ? baseClip : resolveDefaultClip(meta);

    React.useEffect(
      function () {
        if (!isDebugLoggingEnabled() || !meta || !meta.clips) {
          return;
        }
        if (mountLoggedRef.current) {
          return;
        }
        mountLoggedRef.current = true;
        console.log(
          "[DuoCats][mount]",
          "playlist=" + String(playlistName),
          "playlistEnabled=" + String(playlistEnabled),
          "default_clip=" + String(meta.default_clip || "snuggle_idle"),
          "clip=" + String(baseClip),
          "hoverClip=" + String(hoverClip)
        );
      },
      [baseClip, hoverClip, meta, playlistEnabled, playlistName]
    );

    React.useEffect(
      function () {
        if (!isDebugLoggingEnabled() || !meta || metaShapeWarnedRef.current) {
          return;
        }
        if (meta.frameW === 512 && meta.frameH === 256 && meta.cols === 3 && meta.rows === 2) {
          return;
        }
        metaShapeWarnedRef.current = true;
        console.error(
          "[DuoCats] Unexpected atlas grid metadata.",
          "frameW=" + String(meta.frameW),
          "frameH=" + String(meta.frameH),
          "cols=" + String(meta.cols),
          "rows=" + String(meta.rows)
        );
      },
      [meta]
    );

    React.useEffect(
      function () {
        if (playlistEnabled) {
          return;
        }
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
      [baseClip, baseClipExists, ctrl.playOnce, ctrl.setIdle, meta, playlistEnabled]
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
    var clipImagePath = anim && anim.imagePath ? anim.imagePath : meta && meta.imagePath ? meta.imagePath : "";
    var showRuntimeOverlay = window.__DUO_CATS_DEBUG_OVERLAY__ === true;
    var metaMismatchReason = "";
    if (meta && meta.clips) {
      if (meta.default_clip !== "snuggle_idle") {
        metaMismatchReason = "expected default_clip=snuggle_idle, got " + String(meta.default_clip);
      } else {
        var snuggleMeta = meta.clips.snuggle_idle;
        var expectedImg = "/static/sprites/cats/duo_cats/snuggle_idle_p0.png?v=" + DUO_PACK_VERSION;
        if (!snuggleMeta || !snuggleMeta.imagePath) {
          metaMismatchReason = "missing clips.snuggle_idle.imagePath";
        } else if (snuggleMeta.imagePath.indexOf(expectedImg) !== 0) {
          metaMismatchReason = "unexpected snuggle_idle imagePath: " + String(snuggleMeta.imagePath);
        }
      }
    }
    var debugText =
      "clip=" +
      String(ctrl.clipName) +
      " logical=" +
      String(anim.frameIndex) +
      " page=" +
      String(anim.pageIndex) +
      " cell=" +
      String(anim.cellIndex) +
      " img=" +
      String(clipImagePath);

    React.useEffect(
      function () {
        if (!isDebugLoggingEnabled() || !meta || !meta.clips) {
          return undefined;
        }
        if (paused || speed <= 0) {
          return undefined;
        }
        if (!idleProbeClip || ctrl.clipName !== idleProbeClip) {
          return undefined;
        }
        var clipCfg = meta.clips[ctrl.clipName];
        if (!clipCfg || clipCfg.loop !== true) {
          return undefined;
        }

        motionProbeActiveRef.current = true;
        motionProbeRectsRef.current = Object.create(null);
        if (anim.rect) {
          motionProbeRectsRef.current[String(anim.rect.x) + "," + String(anim.rect.y)] = true;
        }

        if (motionProbeTimerRef.current !== null) {
          clearTimeout(motionProbeTimerRef.current);
          motionProbeTimerRef.current = null;
        }

        var probeKey = String(ctrl.clipName) + "|" + String(clipImagePath);
        motionProbeTimerRef.current = window.setTimeout(function () {
          motionProbeTimerRef.current = null;
          if (!motionProbeActiveRef.current) {
            return;
          }
          var distinctRectCount = Object.keys(motionProbeRectsRef.current).length;
          if (distinctRectCount >= 2) {
            return;
          }
          if (motionProbeFailureRef.current[probeKey]) {
            return;
          }
          motionProbeFailureRef.current[probeKey] = true;
          console.error(
            "[DuoCats] Idle motion self-check failed.",
            "clip=" + String(ctrl.clipName),
            "imagePath=" + String(clipImagePath),
            "fps=" + String(clipCfg.fps),
            "loop=" + String(clipCfg.loop),
            "paused=" + String(paused),
            "speed=" + String(speed)
          );
        }, 1100);

        return function () {
          motionProbeActiveRef.current = false;
          if (motionProbeTimerRef.current !== null) {
            clearTimeout(motionProbeTimerRef.current);
            motionProbeTimerRef.current = null;
          }
        };
      },
      [clipImagePath, ctrl.clipName, idleProbeClip, meta, paused, speed]
    );

    React.useEffect(
      function () {
        if (!motionProbeActiveRef.current || !anim.rect) {
          return;
        }
        motionProbeRectsRef.current[String(anim.rect.x) + "," + String(anim.rect.y)] = true;
      },
      [anim.frameIndex, anim.rect]
    );

    React.useEffect(
      function () {
        if (!isDebugLoggingEnabled() || !anim.rect || !meta || !meta.clips) {
          return;
        }
        var debugClip = meta.clips[ctrl.clipName];
        var debugImagePath = anim.imagePath || (debugClip && debugClip.imagePath ? debugClip.imagePath : meta.imagePath);
        var debugScale = Number.isFinite(props.scale) && props.scale > 0 ? props.scale : 0.25;
        var debugAtlasW = (Number.isFinite(meta.frameW) ? meta.frameW : 0) * (Number.isFinite(meta.cols) ? meta.cols : 0);
        var debugAtlasH = (Number.isFinite(meta.frameH) ? meta.frameH : 0) * (Number.isFinite(meta.rows) ? meta.rows : 0);
        var debugBgPos = String(-anim.rect.x * debugScale) + "px " + String(-anim.rect.y * debugScale) + "px";
        var debugBgSize = String(debugAtlasW * debugScale) + "px " + String(debugAtlasH * debugScale) + "px";
        var computedBgPos = "";
        var computedMismatch = false;
        if (frameNodeRef.current && window.getComputedStyle) {
          var computed = window.getComputedStyle(frameNodeRef.current);
          computedBgPos = computed.backgroundPosition || "";
          var parts = computedBgPos.split(/\s+/);
          if (parts.length >= 2) {
            var compX = parseFloat(parts[0]);
            var compY = parseFloat(parts[1]);
            var expectedX = -anim.rect.x * debugScale;
            var expectedY = -anim.rect.y * debugScale;
            if (Number.isFinite(compX) && Number.isFinite(compY)) {
              computedMismatch = Math.abs(compX - expectedX) > 0.75 || Math.abs(compY - expectedY) > 0.75;
            }
          }
        }
        debugFrameCounterRef.current += 1;
        if (debugFrameCounterRef.current % 5 === 0) {
          console.log(
            "[DuoCats][frame]",
            "clip=" + String(ctrl.clipName),
            "logicalFrameIndex=" + String(anim.frameIndex),
            "pageIndex=" + String(anim.pageIndex),
            "cellIndex=" + String(anim.cellIndex),
            "x=" + String(anim.rect.x),
            "y=" + String(anim.rect.y),
            "bgPos=" + debugBgPos,
            "bgSize=" + debugBgSize,
            "imagePath=" + String(debugImagePath),
            "computedBgPos=" + String(computedBgPos),
            "fps=" + String(debugClip && debugClip.fps),
            "loop=" + String(debugClip && debugClip.loop)
          );
          if (computedMismatch) {
            console.warn(
              "[DuoCats] Computed background-position mismatch.",
              "expected=" + debugBgPos,
              "computed=" + computedBgPos
            );
          }
        }
      },
      [anim.frameIndex, anim.pageIndex, anim.cellIndex, anim.rect, anim.imagePath, ctrl.clipName, meta, props.scale]
    );

    React.useEffect(
      function () {
        if (!wrapperNodeRef.current) {
          return;
        }
        var node = wrapperNodeRef.current;
        node.setAttribute("data-duo-mounted", DUO_PACK_VERSION);
        node.setAttribute("data-duo-active-img", String(clipImagePath || ""));
        node.setAttribute("data-duo-clip", String(ctrl.clipName || ""));
        node.setAttribute("data-duo-frame", String(anim.frameIndex));
      },
      [anim.frameIndex, clipImagePath, ctrl.clipName]
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
      position: "relative",
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
    var overlayStyle = {
      position: "absolute",
      left: "0px",
      top: "0px",
      fontSize: "10px",
      lineHeight: "12px",
      padding: "2px 4px",
      background: "rgba(0,0,0,0.6)",
      color: "#fff",
      zIndex: 5,
      pointerEvents: "none",
      maxWidth: "100%",
      whiteSpace: "nowrap",
      overflow: "hidden",
      textOverflow: "ellipsis",
    };
    var metaErrorStyle = {
      position: "absolute",
      left: "0px",
      right: "0px",
      top: "0px",
      background: "rgba(180,0,0,0.92)",
      color: "#fff",
      fontSize: "11px",
      lineHeight: "13px",
      padding: "4px 6px",
      zIndex: 6,
      pointerEvents: "none",
    };

    var className = props.className || "duo-cat-sprite";
    var spriteClassName = props.spriteClassName || "duo-cat-sprite-frame";
    var defaultClickQueue = ["mutual_groom", "paw_batting", "snuggle_curl"];
    var requestedClickQueue = Array.isArray(props.clickQueue) && props.clickQueue.length > 0 ? props.clickQueue : defaultClickQueue;
    var validClickQueue = requestedClickQueue.filter(function (name) {
      return !!(meta && meta.clips && meta.clips[name]);
    });
    var canClickBurst = validClickQueue.length > 0;

    var runUserAction = function (runner) {
      var debug = isDebugLoggingEnabled();
      activeUserActionsRef.current += 1;
      setPlaylistSuspended(true);
      if (debug) {
        console.log("[DuoCats][playlist]", "pause", "activeUserActions=" + String(activeUserActionsRef.current));
      }
      return Promise.resolve()
        .then(function () {
          return runner();
        })
        .catch(function () {
          return undefined;
        })
        .then(function () {
          activeUserActionsRef.current -= 1;
          if (activeUserActionsRef.current <= 0) {
            activeUserActionsRef.current = 0;
            ctrl.setIdle();
            setPlaylistSuspended(false);
            if (debug) {
              console.log("[DuoCats][playlist]", "resume");
            }
          }
        });
    };

    var handleHoverStart = function () {
      if (!switchClipOnHover || !hoverClipExists) {
        return;
      }
      if (hoverPlayedRef.current) {
        return;
      }
      hoverPlayedRef.current = true;
      runUserAction(function () {
        return ctrl.playOnce(hoverClip);
      });
    };
    var handleHoverEnd = function () {
      hoverPlayedRef.current = false;
      if (!playlistEnabled) {
        ctrl.setIdle();
      }
    };
    var handleClickBurst = function () {
      if (!canClickBurst) {
        return;
      }
      runUserAction(function () {
        return ctrl.queue(validClickQueue);
      });
    };
    var handleKeyDown = function (event) {
      var key = event && event.key ? event.key : "";
      if (key !== "Enter" && key !== " " && key !== "Spacebar") {
        return;
      }
      if (event && typeof event.preventDefault === "function") {
        event.preventDefault();
      }
      handleClickBurst();
    };

    if (motion) {
      return h(
        motion.div,
        {
          className: className,
          style: wrapperStyle,
          ref: wrapperNodeRef,
          initial: { opacity: 0.8 },
          animate: { opacity: 1 },
          whileHover: { scale: 1.02 },
          transition: { duration: 0.2, ease: "easeOut" },
          onHoverStart: handleHoverStart,
          onHoverEnd: handleHoverEnd,
          onClick: handleClickBurst,
          onKeyDown: handleKeyDown,
          role: canClickBurst ? "button" : undefined,
          tabIndex: canClickBurst ? 0 : undefined,
          "aria-label": canClickBurst ? "Play interaction burst" : undefined,
        },
        h("div", { className: spriteClassName, style: frameStyle, ref: frameNodeRef }),
        showRuntimeOverlay ? h("div", { style: overlayStyle }, debugText) : null,
        showRuntimeOverlay && metaMismatchReason ? h("div", { style: metaErrorStyle }, "[DuoCats meta mismatch] " + metaMismatchReason) : null
      );
    }

    return h(
      "div",
      {
        className: className,
        style: wrapperStyle,
        ref: wrapperNodeRef,
        onMouseEnter: handleHoverStart,
        onMouseLeave: handleHoverEnd,
        onClick: handleClickBurst,
        onKeyDown: handleKeyDown,
        role: canClickBurst ? "button" : undefined,
        tabIndex: canClickBurst ? 0 : undefined,
        "aria-label": canClickBurst ? "Play interaction burst" : undefined,
      },
      h("div", { className: spriteClassName, style: frameStyle, ref: frameNodeRef }),
      showRuntimeOverlay ? h("div", { style: overlayStyle }, debugText) : null,
      showRuntimeOverlay && metaMismatchReason ? h("div", { style: metaErrorStyle }, "[DuoCats meta mismatch] " + metaMismatchReason) : null
    );
  }

  function readBoolean(value, defaultValue) {
    if (typeof value !== "string") {
      return defaultValue;
    }
    var normalized = value.trim().toLowerCase();
    if (normalized === "false") {
      return false;
    }
    if (normalized === "true") {
      return true;
    }
    return defaultValue;
  }

  function readCsvList(value, fallback) {
    if (typeof value !== "string") {
      return fallback.slice();
    }
    var parsed = value
      .split(",")
      .map(function (item) {
        return item.trim();
      })
      .filter(function (item) {
        return item.length > 0;
      });
    if (parsed.length > 0) {
      return parsed;
    }
    return fallback.slice();
  }

  function readProps(node) {
    return {
      clip: node.dataset.clip || "snuggle_idle",
      hoverClip: node.dataset.hoverClip || "nose_boop",
      switchClipOnHover: node.dataset.hoverSwitch !== "false",
      scale: Number.parseFloat(node.dataset.scale || "0.25") || 0.25,
      paused: node.dataset.pause === "true",
      speed: Number.parseFloat(node.dataset.speed || "1") || 1,
      metadataUrl: node.dataset.metadataUrl || DEFAULT_META_URL,
      playlist: node.dataset.playlist || "ambient_random",
      playlistEnabled: readBoolean(node.dataset.playlistEnabled, true),
      clickQueue: readCsvList(node.dataset.clickQueue, ["mutual_groom", "paw_batting", "snuggle_curl"]),
    };
  }

  function mountOne(node) {
    if (mounted.has(node)) {
      return;
    }
    node.setAttribute("data-duo-mounted", DUO_PACK_VERSION);
    var props = readProps(node);
    if (isDebugLoggingEnabled()) {
      console.log(
        "[DuoCats][mount-props]",
        "playlist=" + String(props.playlist),
        "playlistEnabled=" + String(props.playlistEnabled),
        "clip=" + String(props.clip),
        "hoverClip=" + String(props.hoverClip),
        "clickQueue=" + String((props.clickQueue || []).join(","))
      );
    }
    var root = window.ReactDOM.createRoot(node);
    root.render(h(DuoCatSprite, props));
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
