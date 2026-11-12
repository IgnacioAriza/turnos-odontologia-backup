/*
 * brand.js — single place to rename the product in local HTML previews.
 *
 * Renaming the product or clinic = edit BRAND_NAME here (and the logo asset).
 * No mockup needs to be edited.
 *
 * Usage in a preview:
 *   <span data-brand-name></span>                 -> text replaced with BRAND_NAME
 *   <html data-brand-title="Reservar turno">      -> document.title gets " — BRAND_NAME"
 */
(function () {
  "use strict";

  // (TBD) provisional — replace with the clinic's commercial name.
  var BRAND_NAME = "Turnos Odontología";

  function applyBrandName() {
    var nodes = document.querySelectorAll("[data-brand-name]");
    for (var i = 0; i < nodes.length; i += 1) {
      nodes[i].textContent = BRAND_NAME;
    }
  }

  function applyTitle() {
    var source = document.documentElement.getAttribute("data-brand-title");
    document.title = source ? source + " — " + BRAND_NAME : BRAND_NAME;
  }

  function init() {
    applyBrandName();
    applyTitle();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Exposed so other previews can reuse the same name without duplicating it.
  window.DESIGN_SYSTEM_BRAND = { name: BRAND_NAME };
})();
