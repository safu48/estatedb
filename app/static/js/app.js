/* EstateDB -- progressive enhancement only.
   The site works with JavaScript disabled; this file just adds polish. */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {

    /* Confirm destructive actions. Any form with data-confirm="..." asks first. */
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        if (!window.confirm(form.getAttribute("data-confirm"))) {
          event.preventDefault();
        }
      });
    });

    /* Gallery: click a thumbnail to swap the main image. */
    var main = document.querySelector("[data-gallery-main]");
    if (main) {
      document.querySelectorAll("[data-gallery-thumb]").forEach(function (thumb) {
        thumb.addEventListener("click", function (event) {
          event.preventDefault();
          main.src = thumb.getAttribute("data-gallery-thumb");
        });
      });
    }

    /* Re-submit the filter form as soon as a drop-down changes. */
    document.querySelectorAll("form[data-autosubmit] select").forEach(function (el) {
      el.addEventListener("change", function () { el.form.submit(); });
    });

    /* Add another image-URL box on the listing form. */
    var addImage = document.querySelector("[data-add-image]");
    if (addImage) {
      addImage.addEventListener("click", function () {
        var list = document.querySelector("[data-image-list]");
        var row = document.createElement("div");
        row.className = "mb1";
        row.innerHTML = '<input type="url" name="image_url" ' +
                        'placeholder="/static/img/prop-03.svg">';
        list.appendChild(row);
        row.querySelector("input").focus();
      });
    }

    /* Dismiss the notice / error banner. */
    document.querySelectorAll("[data-dismiss]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var box = btn.closest(".alert");
        if (box) { box.remove(); }
      });
    });

    /* Star rating: clicking a star fills the radio buttons visually. */
    document.querySelectorAll("[data-rating]").forEach(function (group) {
      var paint = function () {
        var picked = group.querySelector("input:checked");
        var value = picked ? parseInt(picked.value, 10) : 0;
        group.querySelectorAll("[data-star]").forEach(function (star) {
          var n = parseInt(star.getAttribute("data-star"), 10);
          star.textContent = n <= value ? "★" : "☆";
        });
      };
      group.addEventListener("change", paint);
      paint();
    });
  });
})();
