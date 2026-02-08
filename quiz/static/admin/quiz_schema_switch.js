(function () {
  function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  onReady(function () {
    // Only run on ADD pages
    if (!window.location.pathname.endsWith("/add/")) return;
    
    const typeEl = document.getElementById("id_type");

    if (!typeEl) return;

    typeEl.addEventListener("change", function () {
      const url = new URL(window.location.href);

      url.searchParams.set("type", typeEl.value);

      window.location.href = url.toString();
    });
  });
})();
