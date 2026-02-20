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

  function useSpriteAnimator(clip, pause, speedMultiplier) {
    var _a = React.useState(0);
    var frameIndex = _a[0];
    var setFrameIndex = _a[1];

    var rafRef = React.useRef(null);
    var lastTsRef = React.useRef(null);
    var accumulatorRef = React.useRef(0);

    var stepMs = React.useMemo(function () {
      if (!clip || !clip.fps || speedMultiplier <= 0) {
        return Number.POSITIVE_INFINITY;
      }
      return 1000 / (clip.fps * speedMultiplier);
    }, [clip, speedMultiplier]);

    React.useEffect(function () {
      setFrameIndex(0);
      lastTsRef.current = null;
      accumulatorRef.current = 0;
    }, [clip]);

    React.useEffect(function () {
      if (!clip || pause || !Number.isFinite(stepMs) || clip.frames.length <= 1) {
        if (rafRef.current !== null) {
          cancelAnimationFrame(rafRef.current);
          rafRef.current = null;
        }
        return undefined;
      }

      function tick(ts) {
        if (lastTsRef.current === null) {
          lastTsRef.current = ts;
        }
        var dt = ts - lastTsRef.current;
        lastTsRef.current = ts;
        accumulatorRef.current += dt;

        var steps = 0;
        while (accumulatorRef.current >= stepMs) {
          accumulatorRef.current -= stepMs;
          steps += 1;
        }

        if (steps > 0) {
          setFrameIndex(function (prev) {
            var next = prev + steps;
            if (clip.loop) {
              return next % clip.frames.length;
            }
            return Math.min(next, clip.frames.length - 1);
          });
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
        accumulatorRef.current = 0;
      };
    }, [clip, pause, stepMs]);

    if (!clip || clip.frames.length === 0) {
      return { frameId: 0, frameIndex: 0 };
    }

    return {
      frameIndex: frameIndex,
      frameId: clip.frames[Math.min(frameIndex, clip.frames.length - 1)],
    };
  }

  function DuoCatSprite(props) {
    var _a = React.useState(props.meta || metaCache);
    var meta = _a[0];
    var setMeta = _a[1];

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

    if (!meta) {
      return null;
    }
    var clip = meta.clips[props.clip];
    if (!clip) {
      return null;
    }
    var anim = useSpriteAnimator(clip, !!props.pause, props.speedMultiplier || 1);
    var frame = meta.frames.find(function (item) {
      return item.id === anim.frameId;
    });
    if (!frame) {
      return null;
    }

    var scale = props.scale || 0.25;
    var style = {
      width: String(meta.frameW * scale) + "px",
      height: String(meta.frameH * scale) + "px",
      backgroundImage: "url(" + String(meta.imagePath) + ")",
      backgroundRepeat: "no-repeat",
      backgroundSize: String(meta.cols * meta.frameW * scale) + "px " + String(meta.rows * meta.frameH * scale) + "px",
      backgroundPosition: String(-frame.x * scale) + "px " + String(-frame.y * scale) + "px",
      imageRendering: "pixelated",
    };

    var className = props.className || "duo-cat-sprite";
    if (motion) {
      return h(
        motion.div,
        {
          className: className,
          style: style,
          initial: { opacity: 0.85 },
          animate: { opacity: 1 },
          whileHover: { scale: 1.02 },
          transition: { duration: 0.2, ease: "easeOut" },
        },
        null
      );
    }
    return h("div", { className: className, style: style });
  }

  function readProps(node) {
    return {
      clip: node.dataset.clip || "duo_snuggle",
      scale: Number.parseFloat(node.dataset.scale || "0.25") || 0.25,
      pause: node.dataset.pause === "true",
      speedMultiplier: Number.parseFloat(node.dataset.speed || "1") || 1,
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
    return Array.prototype.slice.call((scope || document).querySelectorAll("[data-duo-cat]"));
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
