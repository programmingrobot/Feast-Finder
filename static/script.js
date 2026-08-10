document.addEventListener("DOMContentLoaded", () => {

    const dayFilter = document.getElementById("dayFilter");
    const perPageSelect = document.getElementById("perPageSelect");
    const mealFilter = document.getElementById("mealFilter");
    const priceFilter = document.getElementById("priceFilter");
    const customPriceField = document.getElementById("customPriceField");
    const customPriceInput = document.getElementById("customPriceInput");
    const tagFilter = document.getElementById("tagFilter");
    const locationSettingsButton = document.getElementById("openLocationSettings");
    const locationDialog = document.getElementById("locationDialog");
    const closeLocationSettings = document.getElementById("closeLocationSettings");
    const locationEnableRadio = document.getElementById("locationEnableRadio");
    const locationDisableRadio = document.getElementById("locationDisableRadio");
    const geoStatus = document.getElementById("geoStatus");
    const mapDialog = document.getElementById("mapDialog");
    const mapDialogLocation = document.getElementById("mapDialogLocation");
    const mapDialogDistance = document.getElementById("mapDialogDistance");
    const mapDialogStatus = document.getElementById("mapDialogStatus");
    const mapFrame = document.getElementById("mapFrame");
    const openInGoogleMaps = document.getElementById("openInGoogleMaps");
    const openInGoogleMapsDistance = document.getElementById("openInGoogleMapsDistance");
    const closeMapDialog = document.getElementById("closeMapDialog");
    const dealDetailDialog = document.getElementById("dealDetailDialog");
    const detailType = document.getElementById("detailType");
    const detailDescription = document.getElementById("detailDescription");
    const detailCompany = document.getElementById("detailCompany");
    const detailPrice = document.getElementById("detailPrice");
    const detailDays = document.getElementById("detailDays");
    const detailUpdated = document.getElementById("detailUpdated");
    const detailLocation = document.getElementById("detailLocation");
    const detailDistance = document.getElementById("detailDistance");
    const detailMapFrame = document.getElementById("detailMapFrame");
    const detailFixButton = document.getElementById("detailFixButton");
    const closeDealDetail = document.getElementById("closeDealDetail");
    const dealSections = Array.from(document.querySelectorAll(".deal-section"));
    const dealSectionsContainer = document.getElementById("dealSectionsContainer");
    const geoPreferenceKey = "geoDealsEnabled";
    let currentDistances = {};

    const today = new Date().toLocaleDateString("en-US", { weekday: "long" });

    // Replace today's label with "Today" — DO NOT force select
    if (dayFilter) {
        Array.from(dayFilter.options).forEach(opt => {
            if (opt.value === today) {
                opt.textContent = "Today";
            }
        });
    }

    function applyFilters() {
        const url = new URL(window.location.href);
        if (dayFilter) url.searchParams.set("day", dayFilter.value);
        if (perPageSelect) url.searchParams.set("per_page", perPageSelect.value);
        if (mealFilter) url.searchParams.set("meal", mealFilter.value);
        if (priceFilter) url.searchParams.set("price", priceFilter.value);
        if (customPriceInput && priceFilter?.value === "custom" && customPriceInput.value) {
            url.searchParams.set("custom_price", customPriceInput.value);
        } else {
            url.searchParams.delete("custom_price");
        }
        if (tagFilter) url.searchParams.set("tag", tagFilter.value);
        url.searchParams.set("page", 1);
        window.location.href = url.toString();
    }

    function syncCustomPriceField() {
        if (!customPriceField || !priceFilter) return;
        const showCustomPrice = priceFilter.value === "custom";
        customPriceField.hidden = !showCustomPrice;
        if (customPriceInput) {
            customPriceInput.disabled = !showCustomPrice;
        }
    }

    function setGeoButtonState(enabled) {
        if (locationSettingsButton) {
            locationSettingsButton.setAttribute("aria-pressed", enabled ? "true" : "false");
            locationSettingsButton.classList.toggle("is-on", enabled);
            locationSettingsButton.title = enabled ? "Location sorting is enabled" : "Location settings";
        }
        if (locationEnableRadio) {
            locationEnableRadio.checked = enabled;
        }
        if (locationDisableRadio) {
            locationDisableRadio.checked = !enabled;
        }
    }

    function setGeoStatus(message) {
        if (geoStatus) {
            geoStatus.textContent = message || "";
        }
    }

    function formatDistance(distanceKm) {
        if (distanceKm == null || Number.isNaN(distanceKm)) {
            return "";
        }

        const roundedMeters = Math.max(100, Math.round((distanceKm * 1000) / 100) * 100);
        if (roundedMeters >= 1000) {
            return `${(roundedMeters / 1000).toFixed(1)} km away`;
        }
        return `${roundedMeters} m away`;
    }

    function openMapDialog(location) {
        if (!location || !mapDialog || !mapDialogLocation || !mapDialogStatus || !mapFrame || !openInGoogleMaps) {
            return;
        }

        const mapQuery = encodeURIComponent(location);
        const distanceText = formatDistance(currentDistances[location]);

        mapDialogLocation.textContent = location;
        if (mapDialogDistance) {
            mapDialogDistance.hidden = !distanceText;
            mapDialogDistance.textContent = distanceText;
        }
        mapDialogStatus.textContent = "";
        mapFrame.src = `https://www.google.com/maps?q=${mapQuery}&z=15&output=embed`;
        openInGoogleMaps.href = `https://www.google.com/maps/search/?api=1&query=${mapQuery}`;
        openInGoogleMaps.removeAttribute("aria-disabled");
        if (openInGoogleMapsDistance) {
            openInGoogleMapsDistance.hidden = !distanceText;
            openInGoogleMapsDistance.textContent = distanceText;
        }
        mapDialog.showModal();
    }

    function openCorrectionDialog(dealData) {
        if (correctionDealId) correctionDealId.value = dealData.id || "";
        if (correctionDealText) correctionDealText.value = dealData.description || "";
        if (correctionCompany) correctionCompany.value = dealData.company || "";
        if (correctionLocation) correctionLocation.value = dealData.location || "";
        if (correctionMessage) correctionMessage.value = "";
        if (correctionStatus) {
            correctionStatus.textContent = "";
            correctionStatus.className = "status-text";
        }
        correctionDialog?.showModal();
    }

    function getDealDataFromCard(card) {
        return {
            id: card.dataset.id || "",
            company: card.dataset.company || "",
            description: card.dataset.description || "",
            location: card.dataset.location || "",
            type: card.dataset.type || "Deal",
            days: card.dataset.days || "",
            price: card.dataset.price || "Not listed",
            updated: card.dataset.updated || "Current listing"
        };
    }

    function openDealDetail(card) {
        if (!dealDetailDialog) return;

        const dealData = getDealDataFromCard(card);
        const distanceText = formatDistance(currentDistances[dealData.location]);

        if (detailType) detailType.textContent = dealData.type;
        if (detailDescription) detailDescription.textContent = dealData.description;
        if (detailCompany) detailCompany.textContent = dealData.company;
        if (detailPrice) detailPrice.textContent = dealData.price || "Not listed";
        if (detailDays) detailDays.textContent = dealData.days || "Not listed";
        if (detailUpdated) {
            detailUpdated.textContent = dealData.updated === "Current listing" ? dealData.updated : `Updated ${dealData.updated}`;
        }
        if (detailLocation) detailLocation.textContent = dealData.location || "No location listed";
        if (detailDistance) {
            detailDistance.hidden = !distanceText;
            detailDistance.textContent = distanceText;
        }
        if (detailMapFrame) {
            if (dealData.location) {
                detailMapFrame.hidden = false;
                detailMapFrame.src = `https://www.google.com/maps?q=${encodeURIComponent(dealData.location)}&z=15&output=embed`;
            } else {
                detailMapFrame.hidden = true;
                detailMapFrame.removeAttribute("src");
            }
        }

        if (detailFixButton) {
            detailFixButton.onclick = () => {
                dealDetailDialog.close();
                openCorrectionDialog(dealData);
            };
        }

        dealDetailDialog.showModal();
    }

    function restoreDefaultDealOrder() {
        currentDistances = {};

        if (dealSectionsContainer) {
            dealSections
                .slice()
                .sort((first, second) => Number(first.dataset.originalIndex) - Number(second.dataset.originalIndex))
                .forEach(section => {
                    dealSectionsContainer.appendChild(section);
                });
        }

        dealSections.forEach(section => {
            const dealList = section.querySelector(".deal-list");
            if (!dealList) return;

            const entries = Array.from(dealList.querySelectorAll(".deal-entry"));
            entries
                .sort((first, second) => Number(first.dataset.originalIndex) - Number(second.dataset.originalIndex))
                .forEach(entry => {
                    dealList.appendChild(entry);
                        const distanceLabel = entry.querySelector(".deal-distance");
                        if (distanceLabel) {
                            distanceLabel.hidden = true;
                            distanceLabel.textContent = "";
                        }
                    });
        });

        if (mapDialogDistance) {
            mapDialogDistance.hidden = true;
            mapDialogDistance.textContent = "";
        }
        if (openInGoogleMapsDistance) {
            openInGoogleMapsDistance.hidden = true;
            openInGoogleMapsDistance.textContent = "";
        }
    }

    async function enableNearMeMode() {
        if (!navigator.geolocation) {
            setGeoStatus("Geolocation is not supported on this device.");
            localStorage.setItem(geoPreferenceKey, "off");
            setGeoButtonState(false);
            return;
        }

        setGeoStatus("Getting your location...");

        let position;
        try {
            position = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, {
                    enableHighAccuracy: true,
                    maximumAge: 300000,
                    timeout: 10000
                });
            });
        } catch (error) {
            setGeoStatus("Location access is unavailable.");
            localStorage.setItem(geoPreferenceKey, "off");
            setGeoButtonState(false);
            restoreDefaultDealOrder();
            return;
        }

        const locations = Array.from(
            new Set(
                Array.from(document.querySelectorAll(".deal-entry[data-location]"))
                    .map(entry => (entry.dataset.location || "").trim())
                    .filter(Boolean)
            )
        );

        if (locations.length === 0) {
            setGeoStatus("No locations are available on this page.");
            return;
        }

        setGeoStatus("Finding the closest deals...");

        try {
            const response = await fetch("/distance_lookup", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    locations
                })
            });

            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || "Distance lookup failed");
            }

            currentDistances = data.distances || {};

            dealSections.forEach(section => {
                const dealList = section.querySelector(".deal-list");
                if (!dealList) return;

                const entries = Array.from(dealList.querySelectorAll(".deal-entry"));
                entries
                    .sort((first, second) => {
                        const firstLocation = (first.dataset.location || "").trim();
                        const secondLocation = (second.dataset.location || "").trim();
                        const firstDistance = data.distances[firstLocation];
                        const secondDistance = data.distances[secondLocation];

                        if (firstDistance == null && secondDistance == null) {
                            return Number(first.dataset.originalIndex) - Number(second.dataset.originalIndex);
                        }
                        if (firstDistance == null) return 1;
                        if (secondDistance == null) return -1;
                        return firstDistance - secondDistance;
                    })
                    .forEach(entry => {
                        dealList.appendChild(entry);
                        const distanceLabel = entry.querySelector(".deal-distance");
                        const location = (entry.dataset.location || "").trim();
                        const distance = data.distances[location];
                        if (distanceLabel) {
                            if (distance == null) {
                                distanceLabel.hidden = true;
                                distanceLabel.textContent = "";
                            } else {
                                distanceLabel.hidden = false;
                                distanceLabel.textContent = formatDistance(distance);
                            }
                        }
                    });
            });

            dealSections
                .slice()
                .sort((first, second) => {
                    const firstDistances = Array.from(first.querySelectorAll(".deal-entry"))
                        .map(entry => currentDistances[(entry.dataset.location || "").trim()])
                        .filter(distance => distance != null);
                    const secondDistances = Array.from(second.querySelectorAll(".deal-entry"))
                        .map(entry => currentDistances[(entry.dataset.location || "").trim()])
                        .filter(distance => distance != null);

                    const firstNearest = firstDistances.length ? Math.min(...firstDistances) : null;
                    const secondNearest = secondDistances.length ? Math.min(...secondDistances) : null;

                    if (firstNearest == null && secondNearest == null) {
                        return Number(first.dataset.originalIndex) - Number(second.dataset.originalIndex);
                    }
                    if (firstNearest == null) return 1;
                    if (secondNearest == null) return -1;
                    if (firstNearest !== secondNearest) return firstNearest - secondNearest;
                    return Number(first.dataset.originalIndex) - Number(second.dataset.originalIndex);
                })
                .forEach(section => {
                    dealSectionsContainer?.appendChild(section);
                });

            setGeoStatus("Showing deals closest to you.");
        } catch (error) {
            restoreDefaultDealOrder();
            setGeoStatus(error.message || "Distance lookup failed");
            localStorage.setItem(geoPreferenceKey, "off");
            setGeoButtonState(false);
        }
    }

    async function setNearMeMode(enabled) {
        localStorage.setItem(geoPreferenceKey, enabled ? "on" : "off");
        setGeoButtonState(enabled);

        if (!enabled) {
            restoreDefaultDealOrder();
            setGeoStatus("");
            return;
        }

        await enableNearMeMode();
    }

    // Day filter change → reload page
    dayFilter?.addEventListener("change", applyFilters);

    // Page size change → reload page
    perPageSelect?.addEventListener("change", applyFilters);
    mealFilter?.addEventListener("change", applyFilters);
    priceFilter?.addEventListener("change", () => {
        syncCustomPriceField();
        if (priceFilter.value !== "custom") {
            applyFilters();
        } else {
            customPriceInput?.focus();
        }
    });
    customPriceInput?.addEventListener("change", applyFilters);
    tagFilter?.addEventListener("change", applyFilters);
    syncCustomPriceField();

    locationSettingsButton?.addEventListener("click", () => {
        const enabled = localStorage.getItem(geoPreferenceKey) === "on";
        setGeoButtonState(enabled);
        locationDialog?.showModal();
    });

    closeLocationSettings?.addEventListener("click", () => {
        locationDialog?.close();
    });

    locationEnableRadio?.addEventListener("change", async () => {
        if (locationEnableRadio.checked) {
            await setNearMeMode(true);
        }
    });

    locationDisableRadio?.addEventListener("change", async () => {
        if (locationDisableRadio.checked) {
            await setNearMeMode(false);
        }
    });

    document.querySelectorAll(".map-open-btn").forEach(button => {
        button.addEventListener("click", (event) => {
            event.stopPropagation();
            const location = button.dataset.location || "";
            openMapDialog(location);
        });
    });

    closeMapDialog?.addEventListener("click", () => {
        mapDialog?.close();
        if (mapFrame) {
            mapFrame.removeAttribute("src");
        }
        if (mapDialogDistance) {
            mapDialogDistance.hidden = true;
            mapDialogDistance.textContent = "";
        }
        if (openInGoogleMapsDistance) {
            openInGoogleMapsDistance.hidden = true;
            openInGoogleMapsDistance.textContent = "";
        }
    });

    document.querySelectorAll(".deal-card").forEach(card => {
        card.addEventListener("click", () => {
            openDealDetail(card);
        });

        card.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openDealDetail(card);
            }
        });
    });

    closeDealDetail?.addEventListener("click", () => {
        dealDetailDialog?.close();
    });

    dealDetailDialog?.addEventListener("close", () => {
        detailMapFrame?.removeAttribute("src");
    });

    // --------------------------
    // DEAL SUBMISSION MODAL
    // --------------------------
    const openButtons = [
        document.getElementById("openDealModal"),
        document.getElementById("openDealModalBottom")
    ].filter(Boolean);
    const dialog = document.getElementById("dealDialog");
    const form = document.getElementById("dealForm");
    const cancelBtn = document.getElementById("cancelDealBtn");
    const dealStatus = document.getElementById("dealStatus");

    openButtons.forEach(button => {
        button.addEventListener("click", () => {
            dialog?.showModal();
            form?.reset();
            if (dealStatus) {
                dealStatus.textContent = "";
                dealStatus.className = "status-text";
            }
        });
    });

    cancelBtn?.addEventListener("click", () => {
        dialog?.close();
    });

    form?.addEventListener("submit", async (e) => {
        e.preventDefault();

        const name = document.getElementById("businessName").value;
        const address = document.getElementById("businessAddress").value;
        const email = document.getElementById("businessEmail").value;
        const deals = document.getElementById("businessDeals").value;

        if (dealStatus) {
            dealStatus.textContent = "Sending your deal...";
            dealStatus.className = "status-text";
        }

        try {
            const response = await fetch("/submit_deal", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name,
                    address,
                    email,
                    deals
                })
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || "Submission failed");
            }
            if (dealStatus) {
                dealStatus.textContent = "Thanks. Your deal was sent for review.";
                dealStatus.classList.add("success-text");
            }
            form.reset();
        } catch (err) {
            console.error("Submission failed:", err);
            if (dealStatus) {
                dealStatus.textContent = err.message || "Submission failed. Please try again.";
                dealStatus.classList.add("error");
            }
        }
    });

    const correctionDialog = document.getElementById("correctionDialog");
    const correctionForm = document.getElementById("correctionForm");
    const correctionDealId = document.getElementById("correctionDealId");
    const correctionDealText = document.getElementById("correctionDealText");
    const correctionCompany = document.getElementById("correctionCompany");
    const correctionLocation = document.getElementById("correctionLocation");
    const correctionMessage = document.getElementById("correctionMessage");
    const correctionStatus = document.getElementById("correctionStatus");
    const cancelCorrectionBtn = document.getElementById("cancelCorrectionBtn");

    document.querySelectorAll(".correction-btn").forEach(button => {
        button.addEventListener("click", (event) => {
            event.stopPropagation();
            openCorrectionDialog({
                id: button.dataset.id || "",
                description: button.dataset.description || "",
                company: button.dataset.company || "",
                location: button.dataset.location || ""
            });
        });
    });

    cancelCorrectionBtn?.addEventListener("click", () => {
        correctionDialog?.close();
    });

    correctionForm?.addEventListener("submit", async (event) => {
        event.preventDefault();

        if (correctionStatus) {
            correctionStatus.textContent = "Sending your report...";
            correctionStatus.className = "status-text";
        }

        try {
            const response = await fetch("/suggest_correction", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    deal_id: correctionDealId?.value || "",
                    deal_text: correctionDealText?.value || "",
                    company: correctionCompany?.value || "",
                    location: correctionLocation?.value || "",
                    message: correctionMessage?.value || ""
                })
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || "Could not send the report");
            }
            if (correctionStatus) {
                correctionStatus.textContent = "Thanks. We will check it.";
                correctionStatus.classList.add("success-text");
            }
            correctionForm.reset();
        } catch (error) {
            if (correctionStatus) {
                correctionStatus.textContent = error.message || "Could not send the report.";
                correctionStatus.classList.add("error");
            }
        }
    });

    const initialGeoEnabled = localStorage.getItem(geoPreferenceKey) === "on";
    setGeoButtonState(initialGeoEnabled);
    if (initialGeoEnabled) {
        void enableNearMeMode();
    } else {
        restoreDefaultDealOrder();
    }
});
