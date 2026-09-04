(function () {
    "use strict";

    // ── Theme Toggle ──
    const themeToggle = document.getElementById("themeToggle");
    if (themeToggle) {
        themeToggle.addEventListener("click", function () {
            const current = document.documentElement.getAttribute("data-theme");
            const next = current === "dark" ? "light" : "dark";
            document.documentElement.setAttribute("data-theme", next);
            localStorage.setItem("theme", next);
        });
    }

    // ── Language Switcher ──
    const langBtn = document.getElementById("langBtn");
    const langDropdown = document.getElementById("langDropdown");
    if (langBtn && langDropdown) {
        langBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            langDropdown.classList.toggle("open");
        });
        document.addEventListener("click", function () {
            langDropdown.classList.remove("open");
        });
        langDropdown.querySelectorAll(".lang-option").forEach(function (opt) {
            opt.addEventListener("click", function () {
                const lang = this.getAttribute("data-lang");
                fetch("/set-lang/" + lang, { method: "POST" }).then(function () {
                    window.location.reload();
                });
            });
        });
    }

    // ── Mobile Menu ──
    const menuToggle = document.getElementById("menuToggle");
    const mainNav = document.getElementById("mainNav");
    if (menuToggle && mainNav) {
        menuToggle.addEventListener("click", function () {
            mainNav.classList.toggle("mobile-open");
        });
        // Close mobile nav when clicking a link
        mainNav.querySelectorAll(".nav-link").forEach(function (link) {
            link.addEventListener("click", function () {
                mainNav.classList.remove("mobile-open");
            });
        });
    }

    // ── Header shadow on scroll ──
    const header = document.getElementById("siteHeader");
    if (header) {
        let lastScroll = 0;
        window.addEventListener("scroll", function () {
            const scroll = window.scrollY;
            if (scroll > 10) {
                header.style.boxShadow = "var(--shadow-sm)";
            } else {
                header.style.boxShadow = "none";
            }
            lastScroll = scroll;
        }, { passive: true });
    }
})();
