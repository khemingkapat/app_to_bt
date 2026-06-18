const crypto = require('crypto');

// Global memory vault simulating Python thread-safe dictionary
// In Node.js this is inherently synchronous across synchronous ticks
const _vault = new Map();

function normalizeId(idVal) {
    if (!idVal) return "";
    return idVal.replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
}

function purgeExpired() {
    const now = Date.now();
    const expiredTokens = [];

    for (const [token, entry] of _vault.entries()) {
        const createdAt = entry.created_at;
        const ttl = entry.ttl_seconds * 1000;
        if (now - createdAt > ttl) {
            expiredTokens.push(token);
        }
    }

    for (const token of expiredTokens) {
        _vault.delete(token);
    }
}

function addEntry(token, pdfId, customerName, identityId, btData, pdfBytes, registryDict, cacheMapping, ttlSeconds = 900) {
    purgeExpired();
    _vault.set(token, {
        secure_token: token,
        pdf_id: pdfId,
        customer_name: customerName,
        identity_id: identityId, // Raw truth ID for gate check
        bt_data: btData,
        status: "pending",
        created_at: Date.now(),
        ttl_seconds: ttlSeconds,
        pdf_bytes: pdfBytes,
        registry_dict: registryDict,
        cache_mapping: cacheMapping,
        signed_pdf_bytes: null,
        signed_docx_bytes: null,
        signed_at: null,
    });
}

function getEntry(token) {
    purgeExpired();
    return _vault.get(token);
}

function verifyIdentity(token, rawIdInput) {
    purgeExpired();
    const entry = _vault.get(token);

    if (!entry || entry.status !== "pending") return false;

    const truthId = entry.identity_id;
    if (!truthId) return false;

    if (normalizeId(rawIdInput) === normalizeId(truthId)) {
        // Compliance requirement: Discard raw ID number on verification success
        entry.identity_id = null;
        return true;
    }
    return false;
}

function saveSignedDocuments(token, pdfBytes, docxBytes) {
    purgeExpired();
    const entry = _vault.get(token);
    if (entry) {
        entry.signed_pdf_bytes = pdfBytes;
        entry.signed_docx_bytes = docxBytes;
        entry.status = "signed";
        entry.signed_at = Date.now();
    }
}

function removeEntry(token) {
    _vault.delete(token);
}

function extractBtData(allFields, fieldMapping, valuesMap) {
    const btData = {};

    // 1. Determine product_name first
    const productNameVals = [];
    for (const field of allFields) {
        const fname = field.name;
        if (!fname) continue;

        const mapping = fieldMapping[fname];
        if (!mapping) continue;

        const targetKey = typeof mapping === 'object' ? mapping.bt_key : mapping;
        if (targetKey === "product_name") {
            const srcVal = valuesMap[fname] || "";
            let val = "";
            if (typeof mapping === 'object') {
                val = (mapping.choices_map || {})[srcVal] || "";
            } else {
                val = srcVal && !srcVal.startsWith("/") ? srcVal : "";
            }
            if (val) productNameVals.push(val);
        }
    }

    const productSelection = productNameVals.join(" ");
    btData.product_name = productSelection;

    let selectedProductLine = "SmartCare Essential";
    if (productSelection.includes("EASYCARE")) {
        selectedProductLine = "EasyCare Visa";
    }

    // 2. Rebuild all unique keys
    const uniqueKeys = new Set();
    for (const [fname, entry] of Object.entries(fieldMapping)) {
        if (entry !== "SKIPPED") {
            const btKey = typeof entry === 'object' ? entry.bt_key : entry;
            uniqueKeys.add(btKey);
        }
    }

    for (const btKey of uniqueKeys) {
        const parts = [];
        for (const field of allFields) {
            const fname = field.name;
            if (!fname) continue;

            const mapping = fieldMapping[fname];
            if (!mapping) continue;

            const targetKey = typeof mapping === 'object' ? mapping.bt_key : mapping;
            if (targetKey !== btKey) continue;

            let fieldProdLine = "Both";
            if (typeof mapping === 'object') {
                const choicesMap = mapping.choices_map || {};
                const values = new Set(Object.values(choicesMap));
                const essentialUnique = new Set(["ESSENTIAL1", "ESSENTIAL2", "ESSENTIAL3", "ESSENTIAL4", "IPD", "IPD+OPD", "IPD+OPD+WELLNESS", "3k * 30 times / year", "50k per year", "0", "20k", "40k"]);
                const visaUnique = new Set(["VISA1", "VISA2", "300k"]);

                const hasEssential = [...values].some(v => essentialUnique.has(v));
                const hasVisa = [...values].some(v => visaUnique.has(v));

                if (hasEssential) fieldProdLine = "SmartCare Essential";
                else if (hasVisa) fieldProdLine = "EasyCare Visa";
            }

            if (fieldProdLine !== "Both" && fieldProdLine !== selectedProductLine) continue;

            const srcVal = valuesMap[fname] || "";
            let val = "";
            if (typeof mapping === 'object') {
                val = (mapping.choices_map || {})[srcVal] || "";
            } else {
                val = srcVal && !srcVal.startsWith("/") ? srcVal : "";
            }

            if (val && !parts.includes(val)) {
                parts.push(val);
            }
        }
        btData[btKey] = parts.join(" ");
    }

    return btData;
}

module.exports = {
    addEntry,
    getEntry,
    verifyIdentity,
    saveSignedDocuments,
    removeEntry,
    extractBtData,
    _vault // Exported for testing only
};