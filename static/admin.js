let currentSupplier = null;
let currentDealRow = null;

/* ---------------- MODAL HELPERS ---------------- */
document.querySelectorAll(".cancel").forEach(btn => {
    btn.onclick = () => btn.closest("dialog").close();
});

/* ---------------- COMPANY ---------------- */
document.getElementById("openCompanyModal").onclick = () =>
    document.getElementById("companyModal").showModal();

document.getElementById("addCompanyBtn").onclick = async () => {
    const name = companyName.value.trim();
    const location = companyLocation.value.trim();

    if (!name || !location) {
        alert("Company name and location are required.");
        return;
    }

    try {
        const res = await fetch("/admin/add_company", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ supplier: name, location })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to add company");

        window.location.reload();
    } catch (err) {
        alert(err.message);
    }
};

document.querySelectorAll(".edit-company-btn").forEach(btn => {
    btn.onclick = () => {
        editCompanyName.value = btn.dataset.supplier;
        editCompanyLocation.value = btn.dataset.location;
        currentSupplier = btn.dataset.supplier;
        editCompanyModal.showModal();
    };
});

document.getElementById("saveCompanyEdit").onclick = async () => {
    const newName = editCompanyName.value.trim();
    const newLocation = editCompanyLocation.value.trim();

    if (!newName || !newLocation) {
        alert("Company name and location are required.");
        return;
    }

    try {
        const res = await fetch("/admin/edit_company", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                old_supplier: currentSupplier,
                new_supplier: newName,
                location: newLocation
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to edit company");

        window.location.reload();
    } catch (err) {
        alert(err.message);
    }
};

document.querySelectorAll(".delete-company-btn").forEach(btn => {
    btn.onclick = async () => {
        if (!confirm("Delete company and all deals?")) return;

        try {
            const res = await fetch("/admin/delete_company", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ supplier: btn.dataset.supplier })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Failed to delete company");

            window.location.reload();
        } catch (err) {
            alert(err.message);
        }
    };
});

/* ---------------- DEALS ---------------- */
document.querySelectorAll(".add-deal-btn").forEach(btn => {
    btn.onclick = () => {
        currentSupplier = btn.dataset.supplier;
        dealModal.showModal();
    };
});

document.getElementById("addDealBtn").onclick = async () => {
    const deal = dealText.value.trim();
    const type = dealType.value;
    const days = [...addDealDays.querySelectorAll("input:checked")].map(cb => cb.value);

    if (!deal || !type || days.length === 0) {
        alert("Deal description, meal type, and at least one day are required.");
        return;
    }

    try {
        const res = await fetch("/admin/add_deal", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                supplier: currentSupplier,
                deal,
                type,
                days
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to add deal");

        window.location.reload();
    } catch (err) {
        alert(err.message);
    }
};

document.querySelectorAll(".edit-deal-btn").forEach(btn => {
    btn.onclick = () => {
        currentDealRow = btn.closest(".deal-row");

        editDealText.value = currentDealRow.dataset.deal || "";
        editDealType.value = currentDealRow.dataset.type || "";

        const daysArray = JSON.parse(currentDealRow.dataset.days || "[]");
        editDealDays.querySelectorAll("input").forEach(cb => {
            cb.checked = daysArray.includes(cb.value);
        });

        editDealModal.showModal();
    };
});

document.getElementById("saveDealEdit").onclick = async () => {
    if (!currentDealRow) return;

    const dealId = currentDealRow.dataset.id;
    const deal = editDealText.value.trim();
    const type = editDealType.value;
    const days = [...editDealDays.querySelectorAll("input:checked")].map(cb => cb.value);

    if (!dealId || !deal || !type || days.length === 0) {
        alert("All fields are required.");
        return;
    }

    try {
        const res = await fetch("/admin/edit_deal", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                supplier: currentDealRow.dataset.supplier,
                deal_id: dealId,
                new_deal: deal,
                type,
                days
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to edit deal");

        window.location.reload();
    } catch (err) {
        alert(err.message);
    }
};

document.querySelectorAll(".delete-deal-btn").forEach(btn => {
    btn.onclick = async () => {
        if (!confirm("Delete this deal?")) return;
        const row = btn.closest(".deal-row");

        try {
            const res = await fetch("/admin/delete_deal", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    supplier: row.dataset.supplier,
                    deal_id: row.dataset.id
                })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Failed to delete deal");

            window.location.reload();
        } catch (err) {
            alert(err.message);
        }
    };
});

/* ---------------- MESSAGES ---------------- */
document.querySelectorAll(".delete-message-btn").forEach(btn => {
    btn.onclick = async () => {
        try {
            const res = await fetch("/admin/delete_message", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id: btn.dataset.id })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Failed to delete message");

            window.location.reload();
        } catch (err) {
            alert(err.message);
        }
    };
});
