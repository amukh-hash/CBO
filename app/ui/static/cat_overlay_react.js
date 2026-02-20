(function () {
  "use strict";

  var mountNode = document.getElementById("cat-overlay-root");
  if (!mountNode) {
    return;
  }

  var TAB_SELECTOR = ".tree-tab[data-state]";
  var CAT_WIDTH = 126;
  var CAT_HEIGHT = 86;
  var JUMP_DURATION_MS = 500;
  var LAND_DURATION_MS = 150;
  var TOTAL_MOVE_MS = JUMP_DURATION_MS + LAND_DURATION_MS;
  var CAT_ASSET_BASE = mountNode.dataset.catsBase || "/static/assets/cats/";
  var CAT_ASSET_VERSION = mountNode.dataset.catsVersion || "";

  var CAT_GIFS = [
    "idle_nap.gif",
    "wake_up.gif",
    "sit_stare.gif",
    "meow.gif",
    "clean.gif",
    "knead.gif",
    "jump_up_left.gif",
    "jump_up_right.gif",
    "jump_down_left.gif",
    "jump_down_right.gif",
  ];

  var catVariants = {
    jumping: {
      y: -25,
      scaleX: 0.95,
      scaleY: 1.05,
      transition: { duration: 0.5, ease: "easeInOut" },
    },
    landing: {
      y: 0,
      scaleX: 1.1,
      scaleY: 0.9,
      transition: { duration: 0.15, ease: "easeOut" },
    },
    idle: {
      y: 0,
      scaleX: 1,
      scaleY: 1,
      transition: { duration: 0.2, ease: "easeInOut" },
    },
  };

  function listTabs() {
    return Array.prototype.slice.call(document.querySelectorAll(TAB_SELECTOR));
  }

  function assetSrc(filename) {
    if (!filename) {
      return CAT_ASSET_BASE + "idle_nap.gif" + CAT_ASSET_VERSION;
    }
    if (/^(https?:)?\//.test(filename)) {
      return filename;
    }
    return CAT_ASSET_BASE + filename + CAT_ASSET_VERSION;
  }

  function wait(ms) {
    return new Promise(function (resolve) {
      window.setTimeout(resolve, ms);
    });
  }

  function parseBodyState(defaultState) {
    var match = document.body.className.match(/\bcat-state-(\d+)\b/);
    if (!match) {
      return defaultState;
    }
    var parsed = Number.parseInt(match[1], 10);
    return Number.isFinite(parsed) ? parsed : defaultState;
  }

  function setBodyState(nextState) {
    document.body.className = document.body.className.replace(/\bcat-state-\d+\b/g, "").trim();
    document.body.classList.add("cat-state-" + String(nextState));
  }

  function setActiveTabClasses(tabs, activeTab) {
    tabs.forEach(function (tab) {
      tab.classList.remove("active", "active-click");
    });
    if (activeTab) {
      activeTab.classList.add("active", "active-click");
    }
  }

  function findTabByState(stateIndex) {
    var tabs = listTabs();
    var selected = tabs.find(function (tab) {
      return Number.parseInt(tab.getAttribute("data-state") || "0", 10) === stateIndex;
    });
    return selected || tabs[0] || null;
  }

  function findActiveTab(defaultState) {
    var tabs = listTabs();
    var active = tabs.find(function (tab) {
      return tab.classList.contains("active");
    });
    if (active) {
      return active;
    }
    return findTabByState(defaultState);
  }

  function computePosition(activeTabElement, tabsContainerElement) {
    if (!activeTabElement || !tabsContainerElement) {
      return { top: 90, left: 36, width: CAT_WIDTH };
    }

    var containerRect = tabsContainerElement.getBoundingClientRect();
    var activeRect = activeTabElement.getBoundingClientRect();
    var left = activeRect.left - containerRect.left + activeRect.width / 2 - CAT_WIDTH / 2;
    var top = activeRect.top - containerRect.top - CAT_HEIGHT + 10;
    return {
      left: Math.round(left),
      top: Math.round(top),
      width: CAT_WIDTH,
    };
  }

  // eslint-disable-next-line no-unused-vars
  const getJumpDirectionGif = (currentTabElement, targetTabElement) => {
    // Fallback if refs aren't ready
    if (!currentTabElement || !targetTabElement) return "jump_up_right.gif";
    const currentRect = currentTabElement.getBoundingClientRect();
    const targetRect = targetTabElement.getBoundingClientRect();

    // Calculate center points for accurate delta
    const currentX = currentRect.left + (currentRect.width / 2);
    const currentY = currentRect.top + (currentRect.height / 2);
    const targetX = targetRect.left + (targetRect.width / 2);
    const targetY = targetRect.top + (targetRect.height / 2);

    const deltaX = targetX - currentX;
    // Threshold of 2px to account for sub-pixel rendering differences
    const deltaY = targetY - currentY;
    const isMovingLeft = deltaX < 0;
    const isMovingUp = deltaY <= 2; // Treat horizontal as "up" for a hop

    if (isMovingLeft && isMovingUp) return "jump_up_left.gif";
    if (!isMovingLeft && isMovingUp) return "jump_up_right.gif";
    if (isMovingLeft && !isMovingUp) return "jump_down_left.gif";
    return "jump_down_right.gif";
  };

  // eslint-disable-next-line no-unused-vars
  const useIdleCatBehavior = (isJumping, setCatGif) => {
    React.useEffect(() => {
      if (isJumping) return undefined; // Pause idle engine during movement

      var timeoutIds = [];
      const idleTimer = setInterval(() => {
        const roll = Math.random() * 100;
        if (roll < 70) {
          // 70% chance to just keep sleeping
          setCatGif("idle_nap.gif");
        } else if (roll < 80) {
          // 10% chance to clean
          setCatGif("clean.gif");
          timeoutIds.push(setTimeout(() => setCatGif("idle_nap.gif"), 2000));
        } else if (roll < 90) {
          // 10% chance to knead biscuits
          setCatGif("knead.gif");
          timeoutIds.push(setTimeout(() => setCatGif("idle_nap.gif"), 3000));
        } else {
          // 10% chance to wake up and stare
          setCatGif("wake_up.gif");
          timeoutIds.push(
            setTimeout(() => {
              setCatGif("sit_stare.gif");
              timeoutIds.push(setTimeout(() => setCatGif("idle_nap.gif"), 2500));
            }, 600)
          ); // wake_up.gif is approx 600ms
        }
      }, 10000); // Check every 10 seconds

      return () => {
        clearInterval(idleTimer);
        timeoutIds.forEach(function (timerId) {
          clearTimeout(timerId);
        });
      };
    }, [isJumping, setCatGif]);
  };

  function fallbackStatic() {
    mountNode.textContent = "";
    var image = document.createElement("img");
    image.src = assetSrc("idle_nap.gif");
    image.alt = "";
    image.width = CAT_WIDTH;
    image.height = CAT_HEIGHT;
    image.className = "cat-tab-image is-idle-nap";

    var container = document.createElement("div");
    container.className = "cat-tab-indicator";
    container.style.left = "36px";
    container.style.top = "90px";
    container.style.opacity = "1";
    container.appendChild(image);
    mountNode.appendChild(container);
  }

  if (!window.React || !window.ReactDOM || !window.React.createElement) {
    fallbackStatic();
    return;
  }

  var Motion = window.Motion;
  if (!Motion || !Motion.motion) {
    fallbackStatic();
    return;
  }

  var h = window.React.createElement;
  var useEffect = window.React.useEffect;
  var useRef = window.React.useRef;
  var useState = window.React.useState;
  var motion = Motion.motion;

  function CatTabIndicator(props) {
    var _a = useState("idle_nap.gif");
    var currentGif = _a[0];
    var setCurrentGif = _a[1];

    var _b = useState(false);
    var isJumping = _b[0];
    var setIsJumping = _b[1];

    var _c = useState({
      top: 90,
      left: 36,
      width: CAT_WIDTH,
    });
    var position = _c[0];
    var setPosition = _c[1];

    var _d = useState("idle");
    var motionState = _d[0];
    var setMotionState = _d[1];

    var _e = useState(false);
    var isReady = _e[0];
    var setIsReady = _e[1];

    var sequenceRef = useRef(0);

    useEffect(function () {
      CAT_GIFS.forEach(function (name) {
        var preloader = new Image();
        preloader.src = assetSrc(name);
      });
    }, []);

    useIdleCatBehavior(isJumping, setCurrentGif);

    useEffect(
      function () {
        var activeTabElement = props.activeTabRef.current;
        var tabsContainerElement = props.tabsContainerRef.current;
        var previousTabElement = props.prevTabRef.current;
        if (!activeTabElement || !tabsContainerElement) {
          return undefined;
        }

        var targetPos = computePosition(activeTabElement, tabsContainerElement);
        setPosition(targetPos);
        setIsReady(true);

        var hasPrevious = previousTabElement && previousTabElement !== activeTabElement;
        if (!hasPrevious) {
          setMotionState("idle");
          setCurrentGif("idle_nap.gif");
          setIsJumping(false);
          props.prevTabRef.current = activeTabElement;
          return undefined;
        }

        sequenceRef.current += 1;
        var sequenceId = sequenceRef.current;
        var jumpGif = getJumpDirectionGif(previousTabElement, activeTabElement);

        setIsJumping(true);
        setCurrentGif(jumpGif);
        setMotionState("jumping");

        var landingTimer = window.setTimeout(function () {
          if (sequenceRef.current !== sequenceId) {
            return;
          }
          setMotionState("landing");
        }, JUMP_DURATION_MS);

        var finishTimer = window.setTimeout(function () {
          if (sequenceRef.current !== sequenceId) {
            return;
          }
          setMotionState("idle");
          setCurrentGif("idle_nap.gif");
          setIsJumping(false);
          props.prevTabRef.current = activeTabElement;
        }, JUMP_DURATION_MS + LAND_DURATION_MS);

        return function () {
          clearTimeout(landingTimer);
          clearTimeout(finishTimer);
        };
      },
      [props.activeTabVersion, props.activeTabRef, props.prevTabRef, props.tabsContainerRef]
    );

    useEffect(
      function () {
        function onResize() {
          var activeTabElement = props.activeTabRef.current;
          var tabsContainerElement = props.tabsContainerRef.current;
          if (!activeTabElement || !tabsContainerElement) {
            return;
          }
          setPosition(computePosition(activeTabElement, tabsContainerElement));
        }
        window.addEventListener("resize", onResize);
        return function () {
          window.removeEventListener("resize", onResize);
        };
      },
      [props.activeTabRef, props.tabsContainerRef]
    );

    var indicatorTransition = {
      duration: isJumping ? 0.5 : 0.2,
      ease: [0.175, 0.885, 0.32, 1.2],
    };

    var imageClassName = "cat-tab-image";
    if (!isJumping && currentGif === "idle_nap.gif") {
      imageClassName += " is-idle-nap";
    }

    return h(
      motion.div,
      {
        className: "cat-tab-indicator",
        animate: {
          top: position.top,
          left: position.left,
          width: position.width,
          opacity: isReady ? 1 : 0,
        },
        initial: false,
        transition: indicatorTransition,
      },
      h(motion.img, {
        className: imageClassName,
        src: assetSrc(currentGif),
        alt: "",
        draggable: false,
        width: CAT_WIDTH,
        height: CAT_HEIGHT,
        variants: catVariants,
        animate: motionState,
        initial: false,
      })
    );
  }

  function CatOverlayHost(props) {
    var _a = useState(props.initialState);
    var activeState = _a[0];
    var setActiveState = _a[1];

    var _b = useState(0);
    var activeTabVersion = _b[0];
    var setActiveTabVersion = _b[1];

    var activeTabRef = useRef(findActiveTab(props.initialState));
    var prevTabRef = useRef(activeTabRef.current);
    var tabsContainerRef = useRef(document.querySelector(".tree-nav"));
    var navTimeoutRef = useRef(null);

    useEffect(function () {
      tabsContainerRef.current = document.querySelector(".tree-nav");
      if (!activeTabRef.current) {
        activeTabRef.current = findActiveTab(activeState);
      }
      prevTabRef.current = activeTabRef.current;
    }, [activeState]);

    useEffect(function () {
      var tabs = listTabs();
      var listeners = tabs.map(function (tab) {
        function onTabClick(event) {
          if (
            event.defaultPrevented ||
            event.button !== 0 ||
            event.metaKey ||
            event.ctrlKey ||
            event.shiftKey ||
            event.altKey
          ) {
            return;
          }

          var href = tab.getAttribute("href");
          if (!href) {
            return;
          }

          var nextState = Number.parseInt(tab.getAttribute("data-state") || "0", 10);
          if (!Number.isFinite(nextState)) {
            return;
          }

          event.preventDefault();
          if (navTimeoutRef.current) {
            clearTimeout(navTimeoutRef.current);
          }

          prevTabRef.current = activeTabRef.current;
          activeTabRef.current = tab;

          setBodyState(nextState);
          setActiveState(nextState);
          setActiveTabClasses(tabs, tab);
          setActiveTabVersion(function (version) {
            return version + 1;
          });

          navTimeoutRef.current = window.setTimeout(function () {
            window.location.assign(href);
          }, TOTAL_MOVE_MS);
        }

        tab.addEventListener("click", onTabClick);
        return { tab: tab, handler: onTabClick };
      });

      return function () {
        listeners.forEach(function (entry) {
          entry.tab.removeEventListener("click", entry.handler);
        });
        if (navTimeoutRef.current) {
          clearTimeout(navTimeoutRef.current);
          navTimeoutRef.current = null;
        }
      };
    }, []);

    return h(CatTabIndicator, {
      activeTabRef: activeTabRef,
      prevTabRef: prevTabRef,
      tabsContainerRef: tabsContainerRef,
      activeTabVersion: activeTabVersion,
    });
  }

  window.CatTabIndicator = CatTabIndicator;
  window.getJumpDirectionGif = getJumpDirectionGif;
  window.useIdleCatBehavior = useIdleCatBehavior;

  var initialState = Number.parseInt(mountNode.dataset.initialState || "0", 10);
  if (!Number.isFinite(initialState)) {
    initialState = parseBodyState(0);
  }

  var rootElement = h(CatOverlayHost, { initialState: initialState });

  if (window.ReactDOM.createRoot) {
    window.ReactDOM.createRoot(mountNode).render(rootElement);
    return;
  }
  if (window.ReactDOM.render) {
    window.ReactDOM.render(rootElement, mountNode);
    return;
  }

  fallbackStatic();
})();
