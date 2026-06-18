const PizZip = require('pizzip');
const Docxtemplater = require('docxtemplater');
const fs = require('fs');
const path = require('path');

function calculateAge(dobStr) {
    if (!dobStr) return "";

    // Try DD/MM/YYYY or DD-MM-YYYY
    let parts = dobStr.split(/[\/\-]/);
    let day, month, year;

    if (parts.length === 3) {
        if (parts[0].length === 4) {
            // YYYY/MM/DD
            year = parseInt(parts[0]); month = parseInt(parts[1]); day = parseInt(parts[2]);
        } else if (parts[2].length === 4) {
            // DD/MM/YYYY
            day = parseInt(parts[0]); month = parseInt(parts[1]); year = parseInt(parts[2]);
        }
    }

    if (!year || isNaN(year)) {
        const match = dobStr.match(/\b(19\d\d|20\d\d)\b/);
        if (match) {
            year = parseInt(match[1]);
            const currentYear = new Date().getFullYear();
            return (currentYear - year).toString();
        }
        return "";
    }

    const today = new Date();
    let age = today.getFullYear() - year;
    if (today.getMonth() + 1 < month || (today.getMonth() + 1 === month && today.getDate() < day)) {
        age--;
    }
    return age.toString();
}

function applyAcceptanceRules(data) {
    const updated = { ...data };
    const blocks = [
        ["name", "exclusions", "acceptance_conditions"],
        ["sp_name", "sp_exclusions", "sp_acceptance_conditions"],
        ["c1_name", "c1_exclusions", "c1_acceptance_conditions"],
        ["c2_name", "c2_exclusions", "c2_acceptance_conditions"],
        ["c3_name", "c3_exclusions", "c3_acceptance_conditions"]
    ];

    const cleanIndicators = new Set([
        "", "none", "none.", "n/a", "na", "no", "no exclusion",
        "no exclusions", "-", "clean", "nil", "no pre-existing conditions"
    ]);

    for (const [nameKey, exclKey, statusKey] of blocks) {
        const nameVal = (updated[nameKey] || "").toString().trim();
        if (nameVal) {
            const exclVal = (updated[exclKey] || "").toString().trim();
            const checkVal = exclVal.toLowerCase().replace(/\.$/, "");
            if (!checkVal || cleanIndicators.has(checkVal)) {
                updated[statusKey] = "Accepted";
            } else {
                updated[statusKey] = "Accepted with exclusion";
            }
        } else {
            updated[statusKey] = "";
        }
    }
    return updated;
}

function resolvePlanCombination(data) {
    const updated = { ...data };
    const planVal = (updated.plan || "").toString().trim();
    const dedVal = (updated.deductible || "").toString().trim();

    if (!updated.product_name && planVal) {
        if (planVal.toUpperCase().includes("ESSENTIAL") || planVal.toUpperCase().includes("SMARTCARE")) {
            updated.product_name = "ESSENTIAL";
        } else if (planVal.toUpperCase().includes("VISA") || planVal.toUpperCase().includes("EASYCARE")) {
            updated.product_name = "EASYCARE";
        }
    }

    if (!planVal) return updated;

    let planTier = "";
    let optionalBenefit = "";
    let opdChoice = "";
    let isVisa = false;

    if (planVal.includes("VISA")) {
        isVisa = true;
        let match = planVal.match(/VISA\s*(?:Plan)?\s*(\d+)/i);
        if (match) planTier = match[1];
        else {
            match = planVal.match(/Plan\s*(\d+)/i);
            if (match) planTier = match[1];
        }
    } else {
        let matchEss = planVal.match(/ESSENTIAL\s*(\d+)/i);
        if (matchEss) planTier = matchEss[1];
        else {
            let matchPlan = planVal.match(/Plan\s*(\d+)/i);
            if (matchPlan) planTier = matchPlan[1];
        }

        if (planVal.includes("IPD+OPD+WELLNESS")) optionalBenefit = "IPD+OPD+WELLNESS";
        else if (planVal.includes("IPD+OPD")) optionalBenefit = "IPD+OPD";
        else if (planVal.includes("IPD")) optionalBenefit = "IPD";

        let matchOpd = planVal.match(/\(([^)]+)\)/);
        if (matchOpd) opdChoice = matchOpd[1].trim();
        else {
            const parts = planVal.split("-").map(p => p.trim());
            for (const p of parts) {
                if (p === "3k * 30 times / year" || p === "50k per year") {
                    opdChoice = p;
                }
            }
        }
    }

    let deductibleAmount = dedVal.replace(/k/gi, ",000");
    if (deductibleAmount === "0,000") deductibleAmount = "0";

    if (planTier) {
        let comboKey = "";
        if (isVisa) {
            comboKey = `VISA${planTier} DD ${deductibleAmount}`;
        } else if (optionalBenefit) {
            if (optionalBenefit === "IPD") comboKey = `ESSENTIAL${planTier}-IPD DD ${deductibleAmount}`;
            else comboKey = `ESSENTIAL${planTier}-${optionalBenefit}(${opdChoice}) DD ${deductibleAmount}`;
        } else {
            return updated;
        }

        try {
            // Load config
            const pdfId = data.pdf_id;
            const cachePath = path.join(__dirname, '../../outputs', 'assignment_cache.json');
            let configName = 'health_and_accident_insurance.json';

            if (fs.existsSync(cachePath)) {
                const cache = JSON.parse(fs.readFileSync(cachePath, 'utf-8'));
                if (cache[pdfId] && cache[pdfId].product_config) {
                    configName = cache[pdfId].product_config;
                }
            }

            const configPath = path.join(__dirname, '../../config', configName);
            if (fs.existsSync(configPath)) {
                const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
                const comboMap = config.combinations_map || {};
                const planCode = comboMap[comboKey];

                if (planCode) {
                    updated.plan = `${comboKey} (${planCode})`;
                    updated.deductible = deductibleAmount;
                }
            }
        } catch (e) {
            console.error("Error resolving plan config:", e);
        }
    }

    return updated;
}

function fillBlueTableDocx(templateBuffer, data) {
    data = resolvePlanCombination(data);
    data = applyAcceptanceRules(data);

    // Prepare variables for docxtemplater based on Python mappings
    const tData = {};

    tData.age = data.age || calculateAge(data.dob);
    tData.sp_age = data.sp_age || calculateAge(data.sp_dob);
    tData.c1_age = data.c1_age || calculateAge(data.c1_dob);
    tData.c2_age = data.c2_age || calculateAge(data.c2_dob);
    tData.c3_age = data.c3_age || calculateAge(data.c3_dob);

    const policyVer = (data.policy_version || "").toLowerCase();
    if (policyVer === "thai" || policyVer === "th") tData.policy_version = "TH";
    else if (policyVer === "english" || policyVer === "en") tData.policy_version = "EN";
    else tData.policy_version = data.policy_version || "";

    // General conditions logic
    let resolvedProdName = "SmartCare Essential";
    let genCondText = "General Conditions:\nSmartCare Essential\n";
    const prodName = (data.product_name || "").toUpperCase();

    if (prodName.includes("EASYCARE") || prodName.includes("VISA")) {
        resolvedProdName = "EasyCare Visa";
        genCondText = "General Conditions:\nEasyCare Visa\n";
    }

    tData.general_conditions = genCondText;

    try {
        const pdfId = data.pdf_id;
        const cachePath = path.join(__dirname, '../../outputs', 'assignment_cache.json');
        let configName = 'health_and_accident_insurance.json';

        if (fs.existsSync(cachePath)) {
            const cache = JSON.parse(fs.readFileSync(cachePath, 'utf-8'));
            if (cache[pdfId] && cache[pdfId].product_config) {
                configName = cache[pdfId].product_config;
            }
        }

        const configPath = path.join(__dirname, '../../config', configName);
        if (fs.existsSync(configPath)) {
            const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
            const genConds = config.general_conditions || {};
            const prodRules = genConds[resolvedProdName] || {};

            let targetLang = "Both";
            if (policyVer === "thai" || policyVer === "th") targetLang = "Thai";
            else if (policyVer === "english" || policyVer === "en") targetLang = "English";

            let resolvedMsg = prodRules[targetLang];
            if (!resolvedMsg) {
                for (const fallback of [targetLang, "Both", "Thai", "English"]) {
                    const key = Object.keys(prodRules).find(k => k.toLowerCase() === fallback.toLowerCase());
                    if (key) {
                        resolvedMsg = prodRules[key];
                        break;
                    }
                }
            }
            if (!resolvedMsg && Object.keys(prodRules).length > 0) {
                resolvedMsg = Object.values(prodRules)[0];
            }
            if (resolvedMsg) {
                tData.general_conditions += resolvedMsg;
            }
        }
    } catch (e) {
        console.warn("Could not load general conditions:", e);
    }

    // Map all the standard fields directly into docxtemplater variables
    const varsToMap = [
        "name", "dob", "id_card_no", "nationality", "beneficiary", "bene_relation",
        "occupation", "agent", "product_name", "plan", "deductible", "premium",
        "effective_date", "present_address", "tel", "email", "payor_name",
        "payor_address", "tax_id", "acceptance_conditions", "exclusions",
        "sp_name", "sp_dob", "sp_id_card_no", "sp_nationality", "sp_beneficiary", "sp_bene_relation", "sp_occupation", "sp_acceptance_conditions", "sp_exclusions",
        "c1_name", "c1_dob", "c1_id_card_no", "c1_nationality", "c1_beneficiary", "c1_bene_relation", "c1_occupation", "c1_acceptance_conditions", "c1_exclusions",
        "c2_name", "c2_dob", "c2_id_card_no", "c2_nationality", "c2_beneficiary", "c2_bene_relation", "c2_occupation", "c2_acceptance_conditions", "c2_exclusions",
        "c3_name", "c3_dob", "c3_id_card_no", "c3_nationality", "c3_bene_relation", "c3_occupation", "c3_acceptance_conditions", "c3_exclusions"
    ];

    for (const v of varsToMap) {
        tData[v] = data[v] || "";
    }

    const zip = new PizZip(templateBuffer);
    const doc = new Docxtemplater(zip, {
        paragraphLoop: true,
        linebreaks: true,
    });

    doc.render(tData);

    return doc.getZip().generate({
        type: 'nodebuffer',
        compression: 'DEFLATE',
    });
}

module.exports = {
    fillBlueTableDocx,
    calculateAge,
    resolvePlanCombination,
    applyAcceptanceRules
};
