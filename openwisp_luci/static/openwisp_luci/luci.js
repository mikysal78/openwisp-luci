"use strict";
// Sposta il pulsante «LuCI» dagli strumenti in alto alla barra delle schede
// del device, subito dopo «Netconsole» se c'e'. La barra la costruisce tabs.js
// di openwisp-controller al ready di jQuery e lega il click (preventDefault) ai
// link presenti in quel momento: spostandolo al load il link resta un link
// normale che apre LuCI in una nuova scheda. Senza barra resta dov'e'.
// OpenWISP copia gli strumenti in alto in #title-wrapper e nasconde
// l'originale: le copie rimaste si tolgono.
(function () {
  window.addEventListener("load", function () {
    var items = document.querySelectorAll(".object-tools li.luci-tool"),
      bar = document.querySelector("#tabs-container ul.tabs");
    if (!items.length || !bar) {
      return;
    }
    var item = items[0];
    for (var i = 1; i < items.length; i++) {
      items[i].parentNode.removeChild(items[i]);
    }
    var link = item.querySelector("a.luci-link"),
      after = bar.querySelector("li.netconsole");
    link.classList.add("button");
    if (after && after.nextSibling) {
      bar.insertBefore(item, after.nextSibling);
    } else {
      bar.appendChild(item);
    }
  });
})();
