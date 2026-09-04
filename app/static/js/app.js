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
    const body = document.body;

    if (menuToggle && mainNav) {
        // فتح/إغلاق القائمة
        menuToggle.addEventListener("click", function (e) {
            e.stopPropagation();
            mainNav.classList.toggle("active");
            body.classList.toggle("menu-open");
            
            // تغيير شكل زر القائمة (burger ↔ close)
            const svg = menuToggle.querySelector("svg");
            if (mainNav.classList.contains("active")) {
                svg.innerHTML = `
                    <path d="M6 18L18 6M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                `;
            } else {
                svg.innerHTML = `
                    <path d="M3 12h18M3 6h18M3 18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                `;
            }
        });

        // إغلاق القائمة عند الضغط على أي رابط داخلها
        mainNav.querySelectorAll(".nav-link").forEach(function (link) {
            link.addEventListener("click", function () {
                mainNav.classList.remove("active");
                body.classList.remove("menu-open");
                // إعادة شكل زر القائمة
                const svg = menuToggle.querySelector("svg");
                svg.innerHTML = `
                    <path d="M3 12h18M3 6h18M3 18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                `;
            });
        });

        // إغلاق القائمة عند الضغط خارجها
        document.addEventListener("click", function (e) {
            if (!mainNav.contains(e.target) && !menuToggle.contains(e.target)) {
                mainNav.classList.remove("active");
                body.classList.remove("menu-open");
                const svg = menuToggle.querySelector("svg");
                svg.innerHTML = `
                    <path d="M3 12h18M3 6h18M3 18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                `;
            }
        });

        // إغلاق القائمة عند تغيير حجم النافذة إلى سطح المكتب
        window.addEventListener("resize", function () {
            if (window.innerWidth >= 1024) {
                mainNav.classList.remove("active");
                body.classList.remove("menu-open");
                const svg = menuToggle.querySelector("svg");
                svg.innerHTML = `
                    <path d="M3 12h18M3 6h18M3 18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                `;
            }
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

    // ── Close dropdowns when pressing Escape key ──
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            // إغلاق قائمة اللغة
            if (langDropdown) {
                langDropdown.classList.remove("open");
            }
            // إغلاق القائمة الجوالة
            if (mainNav && mainNav.classList.contains("active")) {
                mainNav.classList.remove("active");
                body.classList.remove("menu-open");
                const svg = menuToggle.querySelector("svg");
                svg.innerHTML = `
                    <path d="M3 12h18M3 6h18M3 18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                `;
            }
        }
    });

    // ── Prevent body scroll when menu is open (touch devices) ──
    if (body) {
        // منع التمرير عند فتح القائمة على أجهزة اللمس
        document.addEventListener("touchmove", function (e) {
            if (body.classList.contains("menu-open") && mainNav && mainNav.contains(e.target)) {
                e.preventDefault();
            }
        }, { passive: false });
    }

    // ── Fix for iOS Safari viewport height ──
    function setVH() {
        const vh = window.innerHeight * 0.01;
        document.documentElement.style.setProperty("--vh", vh + "px");
    }
    setVH();
    window.addEventListener("resize", setVH);

    // ── Handle RTL/LTR direction ──
    const dirToggle = document.getElementById("dirToggle");
    if (dirToggle) {
        dirToggle.addEventListener("click", function () {
            const html = document.documentElement;
            const currentDir = html.getAttribute("dir");
            const nextDir = currentDir === "rtl" ? "ltr" : "rtl";
            html.setAttribute("dir", nextDir);
            localStorage.setItem("dir", nextDir);
        });
    }

    // ── Restore direction from localStorage ──
    const savedDir = localStorage.getItem("dir");
    if (savedDir) {
        document.documentElement.setAttribute("dir", savedDir);
    }

    console.log("✅ Application initialized successfully");
})();
