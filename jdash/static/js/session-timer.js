(function () {
  const configElement = document.getElementById("session-timer-config");
  if (!configElement) {
    return;
  }

  const timeoutSeconds = Number(configElement.dataset.timeoutSeconds || 1200);
  const modalThresholdSeconds = Number(configElement.dataset.modalThresholdSeconds || 60);
  const checkIntervalMs = Number(configElement.dataset.checkIntervalMs || 30000);
  const keepAliveThrottleMs = Number(configElement.dataset.keepaliveThrottleMs || 60000);
  const logoutUrl = configElement.dataset.logoutUrl || "";
  const sessionCheckUrl = configElement.dataset.sessionCheckUrl || "";
  const timeoutMs = timeoutSeconds * 1000;
  const modalThresholdMs = modalThresholdSeconds * 1000;
  const activityStorageKey = "jdashLastActivityAt";
  const timerDisplay = document.getElementById("logout-timer");
  const sessionModalElement = document.getElementById("sessionModal");

  let logoutTriggered = false;
  let fallbackLastActivityAt = Date.now();
  let lastServerRefreshAt = 0;
  let keepAliveInFlight = false;

  function getSessionModal() {
    if (!sessionModalElement) {
      return null;
    }

    if (window.bootstrap && window.bootstrap.Modal) {
      const modalClass = window.bootstrap.Modal;
      if (typeof modalClass.getOrCreateInstance === "function") {
        return modalClass.getOrCreateInstance(sessionModalElement);
      }
      if (typeof modalClass.getInstance === "function") {
        return modalClass.getInstance(sessionModalElement) || new modalClass(sessionModalElement);
      }
      try {
        return new modalClass(sessionModalElement);
      } catch (error) {
        // Fall through to jQuery modal support.
      }
    }

    if (window.jQuery) {
      const modalElement = window.jQuery(sessionModalElement);
      return {
        show() { modalElement.modal("show"); },
        hide() { modalElement.modal("hide"); }
      };
    }

    return null;
  }

  function readLastActivityAt() {
    try {
      const rawValue = window.sessionStorage.getItem(activityStorageKey);
      const parsedValue = Number(rawValue);
      if (Number.isFinite(parsedValue) && parsedValue > 0) {
        fallbackLastActivityAt = parsedValue;
        return parsedValue;
      }
    } catch (error) {
      // Storage may be unavailable in some browsers; keep using memory.
    }
    return fallbackLastActivityAt;
  }

  function writeLastActivityAt(timestamp) {
    fallbackLastActivityAt = timestamp;
    try {
      window.sessionStorage.setItem(activityStorageKey, String(timestamp));
    } catch (error) {
      // Storage may be unavailable in some browsers; keep using memory.
    }
  }

  function clearLastActivityAt() {
    try {
      window.sessionStorage.removeItem(activityStorageKey);
    } catch (error) {
      // Ignore storage failures.
    }
  }

  function ensureLastActivityAt() {
    const timestamp = readLastActivityAt();
    if (!timestamp) {
      const now = Date.now();
      writeLastActivityAt(now);
      return now;
    }
    return timestamp;
  }

  function logoutNow() {
    if (logoutTriggered || !logoutUrl) {
      return;
    }
    logoutTriggered = true;
    clearLastActivityAt();
    window.location.assign(logoutUrl);
  }

  function handleSessionCheckResponse(response) {
    if (response.status === 401 || response.redirected) {
      logoutNow();
      return false;
    }
    return response.ok;
  }

  function refreshServerSession(force) {
    if (logoutTriggered || keepAliveInFlight || !sessionCheckUrl) {
      return;
    }

    const now = Date.now();
    if (!force && now - lastServerRefreshAt < keepAliveThrottleMs) {
      return;
    }

    keepAliveInFlight = true;
    fetch(`${sessionCheckUrl}?refresh=1`, {
      method: "GET",
      credentials: "same-origin"
    })
      .then((response) => {
        if (handleSessionCheckResponse(response)) {
          lastServerRefreshAt = Date.now();
        }
      })
      .catch(() => {
        // Transient network issues should not force an immediate logout.
      })
      .finally(() => {
        keepAliveInFlight = false;
      });
  }

  function updateTimer() {
    const elapsedMs = Date.now() - ensureLastActivityAt();
    const remainingMs = Math.max(0, timeoutMs - elapsedMs);
    const remainingSeconds = Math.ceil(remainingMs / 1000);
    const minutes = Math.floor(remainingSeconds / 60);
    const seconds = remainingSeconds % 60;

    if (timerDisplay) {
      timerDisplay.textContent = `${minutes}:${String(seconds).padStart(2, "0")}`;
    }

    const sessionModal = getSessionModal();
    if (sessionModal) {
      if (remainingMs > 0 && remainingMs <= modalThresholdMs) {
        sessionModal.show();
      } else {
        sessionModal.hide();
      }
    }

    if (remainingMs <= 0) {
      logoutNow();
    }
  }

  function markActivity() {
    writeLastActivityAt(Date.now());
    refreshServerSession(false);
    const sessionModal = getSessionModal();
    if (sessionModal) {
      sessionModal.hide();
    }
    updateTimer();
  }

  ensureLastActivityAt();
  refreshServerSession(true);

  ["keydown", "click", "scroll", "touchstart"].forEach((eventName) => {
    document.addEventListener(eventName, markActivity, { passive: true });
  });

  window.addEventListener("focus", updateTimer);
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) {
      updateTimer();
    }
  });

  setInterval(function () {
    if (!sessionCheckUrl) {
      return;
    }
    fetch(sessionCheckUrl, {
      method: "GET",
      credentials: "same-origin"
    })
      .then(handleSessionCheckResponse)
      .catch(function () {
        // Ignore transient network failures; a later successful check will resync.
      });
  }, checkIntervalMs);

  updateTimer();
  setInterval(updateTimer, 1000);
})();

