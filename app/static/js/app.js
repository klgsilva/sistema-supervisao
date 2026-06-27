document.addEventListener("DOMContentLoaded", () => {
    const currentUrl = new URL(window.location.href);
    const scrollKey = "supervisao:restore-scroll";
    const navEntry = performance.getEntriesByType("navigation")[0];
    const isReload = navEntry && navEntry.type === "reload";
    const savedScroll = sessionStorage.getItem(scrollKey);

    if (isReload) {
        sessionStorage.removeItem(scrollKey);
    }

    const saveScrollPosition = () => {
        sessionStorage.setItem(scrollKey, JSON.stringify({
            path: window.location.pathname,
            y: window.scrollY,
        }));
    };

    const nativeFormSubmit = HTMLFormElement.prototype.submit;
    HTMLFormElement.prototype.submit = function submitWithScrollRestore() {
        saveScrollPosition();
        nativeFormSubmit.call(this);
    };

    document.querySelectorAll("form").forEach((form) => {
        form.addEventListener("submit", saveScrollPosition);
    });

    if (currentUrl.searchParams.has("corredor_loja_id") || currentUrl.searchParams.has("balanco_loja_id")) {
        currentUrl.searchParams.delete("corredor_loja_id");
        currentUrl.searchParams.delete("balanco_loja_id");
        window.history.replaceState({}, "", `${currentUrl.pathname}${currentUrl.search}${currentUrl.hash}`);
    }
    if (currentUrl.pathname.endsWith("/manutencoes") && currentUrl.searchParams.has("loja_id")) {
        currentUrl.searchParams.delete("loja_id");
        window.history.replaceState({}, "", `${currentUrl.pathname}${currentUrl.search}${currentUrl.hash}`);
    }
    const scrollTarget = currentUrl.searchParams.get("scroll_to");
    if (scrollTarget) {
        currentUrl.searchParams.delete("scroll_to");
        window.history.replaceState({}, "", `${currentUrl.pathname}${currentUrl.search}${currentUrl.hash}`);
        const target = document.getElementById(scrollTarget);
        if (target) {
            target.scrollIntoView({ block: "start" });
        }
    }
    if (!isReload && savedScroll) {
        try {
            const scrollData = JSON.parse(savedScroll);
            if (scrollData.path === window.location.pathname && Number.isFinite(scrollData.y)) {
                window.scrollTo({ top: scrollData.y, left: 0 });
            }
        } catch (error) {
            sessionStorage.removeItem(scrollKey);
        }
        sessionStorage.removeItem(scrollKey);
    }

    const toggle = document.querySelector("[data-menu-toggle]");
    const menu = document.querySelector("[data-menu]");
    const menuBackdrop = document.querySelector("[data-menu-backdrop]");
    const appShell = document.querySelector("[data-app-shell]");
    const sidebarCollapse = document.querySelector("[data-sidebar-collapse]");
    const sidebarCollapsedKey = "supervisao:sidebar-collapsed";
    if (appShell && localStorage.getItem(sidebarCollapsedKey) === "1") {
        appShell.classList.add("sidebar-collapsed");
    }
    if (sidebarCollapse && appShell) {
        sidebarCollapse.addEventListener("click", (event) => {
            event.stopPropagation();
            appShell.classList.toggle("sidebar-collapsed");
            localStorage.setItem(sidebarCollapsedKey, appShell.classList.contains("sidebar-collapsed") ? "1" : "0");
        });
    }
    if (toggle && menu) {
        const closeMenu = () => {
            menu.classList.remove("open");
            if (menuBackdrop) {
                menuBackdrop.classList.remove("open");
            }
        };
        const openMenu = () => {
            menu.classList.add("open");
            if (menuBackdrop) {
                menuBackdrop.classList.add("open");
            }
        };
        toggle.addEventListener("click", (event) => {
            event.stopPropagation();
            if (menu.classList.contains("open")) {
                closeMenu();
            } else {
                openMenu();
            }
            toggle.blur();
        });
        menu.querySelectorAll("a").forEach((link) => {
            link.addEventListener("click", closeMenu);
        });
        menu.addEventListener("click", (event) => event.stopPropagation());
        if (menuBackdrop) {
            menuBackdrop.addEventListener("click", closeMenu);
        }
        document.addEventListener("click", closeMenu);
    }

    const lojaSelect = document.querySelector("[data-loja-select]");
    const visitDetails = document.querySelector("[data-visit-details]");
    if (lojaSelect && visitDetails) {
        const refreshVisitDetails = () => {
            visitDetails.classList.toggle("hidden", !lojaSelect.value);
            const pendingBlocks = document.querySelectorAll("[data-pending-store]");
            const noPendingAlert = document.querySelector("[data-no-pending-alert]");
            let hasPending = false;
            pendingBlocks.forEach((block) => {
                const shouldShow = lojaSelect.value && block.dataset.pendingStore === lojaSelect.value;
                block.classList.toggle("hidden", !shouldShow);
                hasPending = hasPending || shouldShow;
            });
            if (noPendingAlert) {
                noPendingAlert.classList.toggle("hidden", !lojaSelect.value || hasPending);
            }
        };
        lojaSelect.addEventListener("change", refreshVisitDetails);
        refreshVisitDetails();
    }

    const periodoSelect = document.querySelector("[data-periodo-select]");
    const monthFilter = document.querySelector("[data-month-filter]");
    const dayFilter = document.querySelector("[data-day-filter]");
    const rangeStartFilter = document.querySelector("[data-range-start-filter]");
    const rangeEndFilter = document.querySelector("[data-range-end-filter]");
    if (periodoSelect && monthFilter && dayFilter && rangeStartFilter && rangeEndFilter) {
        const refreshPeriodFilters = () => {
            const isDay = periodoSelect.value === "dia";
            const isRange = periodoSelect.value === "intervalo";
            monthFilter.closest("label").classList.toggle("hidden", isDay || isRange);
            dayFilter.closest("label").classList.toggle("hidden", !isDay);
            rangeStartFilter.closest("label").classList.toggle("hidden", !isRange);
            rangeEndFilter.closest("label").classList.toggle("hidden", !isRange);
        };
        periodoSelect.addEventListener("change", refreshPeriodFilters);
        refreshPeriodFilters();
    }

    const reportSectionSelect = document.querySelector("[data-report-section-select]");
    const reportSections = document.querySelectorAll("[data-report-section]");
    if (reportSectionSelect && reportSections.length) {
        const refreshReportSection = () => {
            reportSections.forEach((section) => {
                section.classList.toggle("hidden", section.dataset.reportSection !== reportSectionSelect.value);
            });
        };
        reportSectionSelect.addEventListener("change", refreshReportSection);
        refreshReportSection();
    }

    document.querySelectorAll("[data-money]").forEach((input) => {
        input.addEventListener("blur", () => {
            const raw = input.value.replace(/[^\d,.-]/g, "").replace(/\./g, "").replace(",", ".");
            if (!raw) {
                input.value = "";
                return;
            }
            const value = Number(raw);
            if (!Number.isNaN(value)) {
                input.value = value.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            }
        });
    });

    document.querySelectorAll(".evidence-photo").forEach((photoBlock) => {
        const status = photoBlock.querySelector("[data-photo-status]");
        const inputs = photoBlock.querySelectorAll('input[type="file"]');
        inputs.forEach((input) => {
            input.addEventListener("change", () => {
                if (!status) {
                    return;
                }
                const file = input.files && input.files[0];
                if (!file) {
                    status.textContent = "Nenhuma foto adicionada";
                    status.classList.remove("selected");
                    return;
                }
                status.textContent = input.name.includes("galeria")
                    ? `Arquivo selecionado: ${file.name}`
                    : "Foto pronta para envio";
                status.classList.add("selected");
            });
        });
    });

    const parseMoneyValue = (value) => {
        const raw = String(value || "").replace(/[^\d,.-]/g, "").replace(/\./g, "").replace(",", ".");
        const parsed = Number(raw);
        return Number.isNaN(parsed) ? 0 : parsed;
    };

    const parseSavedMoneyValue = (value) => {
        const parsed = Number(String(value || "0").replace(",", "."));
        return Number.isNaN(parsed) ? 0 : parsed;
    };

    const formatMoneyValue = (value) => value.toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL",
    });

    document.querySelectorAll("[data-balance-store]").forEach((store) => {
        const total = store.querySelector("[data-store-total]");
        const fixedTotal = store.querySelector("[data-fixed-total]");
        const inputs = store.querySelectorAll("[data-balance-value]");
        const savedValues = store.querySelectorAll("[data-balance-saved]");
        const refreshTotal = () => {
            const inputSum = Array.from(inputs).reduce((acc, input) => acc + parseMoneyValue(input.value), 0);
            const savedSum = Array.from(savedValues).reduce((acc, item) => acc + parseSavedMoneyValue(item.dataset.value), 0);
            const fixedInputSum = Array.from(inputs)
                .filter((input) => input.hasAttribute("data-balance-fixed"))
                .reduce((acc, input) => acc + parseMoneyValue(input.value), 0);
            const fixedSavedSum = Array.from(savedValues)
                .filter((item) => item.hasAttribute("data-balance-fixed"))
                .reduce((acc, item) => acc + parseSavedMoneyValue(item.dataset.value), 0);
            if (total) {
                total.textContent = formatMoneyValue(inputSum + savedSum);
            }
            if (fixedTotal) {
                fixedTotal.textContent = formatMoneyValue(fixedInputSum + fixedSavedSum);
            }
        };
        inputs.forEach((input) => input.addEventListener("input", refreshTotal));
        if (inputs.length) {
            refreshTotal();
        }
    });

    document.querySelectorAll(".check-item").forEach((item) => {
        const comment = item.querySelector("[data-comment]");
        const nokExtra = item.querySelector("[data-nok-extra]");
        const photoLabel = item.querySelector("[data-photo-label]");
        const radios = item.querySelectorAll("[data-status]");
        const refresh = () => {
            const selected = item.querySelector("[data-status]:checked");
            const isNok = selected && selected.value === "NOK";
            if (comment) {
                comment.required = isNok;
            }
            if (nokExtra) {
                nokExtra.classList.toggle("hidden", !isNok);
            }
            if (photoLabel) {
                photoLabel.textContent = isNok ? "Foto NOK (opcional)" : "Foto OK (opcional)";
            }
        };
        radios.forEach((radio) => radio.addEventListener("change", refresh));
        refresh();
    });

    document.querySelectorAll("[data-avaria-trigger]").forEach((radio) => {
        const refreshAvariaDetail = () => {
            const group = radio.dataset.avariaTrigger;
            const selected = document.querySelector(`[data-avaria-trigger="${group}"]:checked`);
            const detail = document.querySelector(`[data-avaria-detail="${group}"]`);
            const comment = detail ? detail.querySelector("[data-avaria-comment]") : null;
            const shouldShow = selected && selected.value === "NOK";
            if (detail) {
                detail.classList.toggle("hidden", !shouldShow);
            }
            if (comment) {
                comment.required = shouldShow;
                if (!shouldShow) {
                    comment.value = "";
                }
            }
        };
        radio.addEventListener("change", refreshAvariaDetail);
        refreshAvariaDetail();
    });
});
