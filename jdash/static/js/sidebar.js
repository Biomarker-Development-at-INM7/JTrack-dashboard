(function () {
  "use strict";

  const body = document.body;
  const sidebar = document.getElementById("dashboardSidebar");
  const collapseButton = document.getElementById("dashboardSidebarCollapse");
  const mobileButton = document.getElementById("dashboardSidebarMobileToggle");
  const backdrop = document.getElementById("dashboardSidebarBackdrop");
  const settingsMenu = sidebar && sidebar.querySelector(".dashboard-sidebar-settings");

  if (!sidebar || !collapseButton || !mobileButton || !backdrop) return;

  const storageKey = "jdash-sidebar-collapsed";
  const desktopMedia = window.matchMedia("(min-width: 992px)");

  function setDesktopCollapsed(collapsed) {
    body.classList.toggle("dashboard-sidebar-collapsed", collapsed);
    collapseButton.setAttribute("aria-expanded", collapsed ? "false" : "true");
    collapseButton.setAttribute(
      "aria-label",
      collapsed ? "Expand navigation" : "Collapse navigation"
    );
  }

  function closeMobileSidebar() {
    body.classList.remove("dashboard-sidebar-open");
    mobileButton.setAttribute("aria-expanded", "false");
  }

  if (desktopMedia.matches) {
    setDesktopCollapsed(window.localStorage.getItem(storageKey) === "true");
  }

  collapseButton.addEventListener("click", function () {
    if (!desktopMedia.matches) {
      closeMobileSidebar();
      return;
    }
    const collapsed = !body.classList.contains("dashboard-sidebar-collapsed");
    setDesktopCollapsed(collapsed);
    window.localStorage.setItem(storageKey, String(collapsed));
  });

  mobileButton.addEventListener("click", function () {
    const open = body.classList.toggle("dashboard-sidebar-open");
    mobileButton.setAttribute("aria-expanded", open ? "true" : "false");
  });

  backdrop.addEventListener("click", closeMobileSidebar);
  sidebar.querySelectorAll("a").forEach(function (link) {
    link.addEventListener("click", closeMobileSidebar);
  });

  document.addEventListener("click", function (event) {
    if (settingsMenu && settingsMenu.open && !settingsMenu.contains(event.target)) {
      settingsMenu.removeAttribute("open");
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && settingsMenu && settingsMenu.open) {
      settingsMenu.removeAttribute("open");
      const summary = settingsMenu.querySelector("summary");
      if (summary) summary.focus();
    }
  });

  desktopMedia.addEventListener("change", function (event) {
    closeMobileSidebar();
    if (event.matches) {
      setDesktopCollapsed(window.localStorage.getItem(storageKey) === "true");
    } else {
      body.classList.remove("dashboard-sidebar-collapsed");
    }
  });
})();
