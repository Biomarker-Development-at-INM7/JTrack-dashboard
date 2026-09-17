(function () {
  "use strict";

  const supportedLanguages = ["en", "de"];
  const devPrefix = "dev";

  /**
   * Build the target URL when switching language.
   *
   * Supported canonical URLs:
   *
   * Development:
   *   /dev/en/login/
   *   /dev/de/login/
   *
   * Production:
   *   /en/login/
   *   /de/login/
   *
   * Dev pages keep /dev before the language when switching languages.
   */
  function buildLanguageSwitchPath(targetLanguage, currentHref) {
    if (!supportedLanguages.includes(targetLanguage)) {
      console.warn(
        "Unsupported language:",
        targetLanguage
      );

      return currentHref || window.location.href;
    }

    const url = new URL(
      currentHref || window.location.href,
      window.location.origin
    );

    const segments = url.pathname
      .split("/")
      .filter(Boolean);

    const hasTrailingSlash =
      url.pathname.endsWith("/") &&
      segments.length > 0;

    const nextSegments = buildLanguageSegments(
      segments,
      targetLanguage
    );

    let path = `/${nextSegments.join("/")}`;

    if (
      hasTrailingSlash &&
      path !== "/"
    ) {
      path += "/";
    }

    return `${path}${url.search}${url.hash}`;
  }


  /**
   * Replace/insert the language component while preserving the dev
   * prefix:
   *
   *   /dev/en/login/
   */
  function buildLanguageSegments(
    segments,
    targetLanguage
  ) {
    const normalized = splitLeadingLanguageAndDev(segments);

    if (normalized.usesDevPrefix) {
      return [
        devPrefix,
        targetLanguage,
        ...normalized.pageSegments,
      ];
    }

    return [
      targetLanguage,
      ...normalized.pageSegments,
    ];
  }


  /**
   * Treat only the leading language/dev tokens as routing prefixes while
   * preserving whether this is a dev-prefixed URL.
   */
  function splitLeadingLanguageAndDev(segments) {
    const pageSegments = [...segments];
    let usesDevPrefix = false;

    while (
      pageSegments.length > 0 &&
      (
        pageSegments[0] === devPrefix ||
        supportedLanguages.includes(pageSegments[0])
      )
    ) {
      if (pageSegments[0] === devPrefix) {
        usesDevPrefix = true;
      }

      pageSegments.shift();
    }

    return {
      usesDevPrefix,
      pageSegments,
    };
  }


  /**
   * Populate language-switcher target URLs.
   */
  function updateLanguageTargets() {
    document
      .querySelectorAll(".language-next")
      .forEach((input) => {
        const language =
          input.dataset.language;

        if (
          supportedLanguages.includes(language)
        ) {
          input.value =
            buildLanguageSwitchPath(language);
        }
      });


    document
      .querySelectorAll(".language-link")
      .forEach((link) => {
        const language =
          link.dataset.language;

        if (
          supportedLanguages.includes(language)
        ) {
          link.href =
            buildLanguageSwitchPath(language);
        }
      });
  }


  /**
   * Expose for browser testing.
   *
   * Example:
   *
   * buildLanguageSwitchPath(
   *     "en",
   *     "https://jdash.inm7.de/dev/de/login/"
   * )
   *
   * Result:
   *
   * /dev/en/login/
   */
  window.buildLanguageSwitchPath =
    buildLanguageSwitchPath;


  if (
    document.readyState === "loading"
  ) {
    document.addEventListener(
      "DOMContentLoaded",
      updateLanguageTargets
    );
  } else {
    updateLanguageTargets();
  }
})();
