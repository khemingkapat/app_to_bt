const express = require('express');
const multer = require('multer');
const cors = require('cors');
const path = require('path');
const { processPdf } = require('./src/pdf_processor/engine');

const app = express();
const port = process.env.PORT || 3000;

// Setup multer to use memory storage, keeping uploads stateless and off the disk
const storage = multer.memoryStorage();
const upload = multer({ storage: storage });

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Basic registry kept in memory for the POC API state
let inMemoryRegistry = {};

app.post('/api/process-pdf', upload.single('pdf'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No PDF file provided.' });
        }

        console.log(`Processing uploaded file: ${req.file.originalname} (${req.file.size} bytes)`);

        // Use the core engine to process the PDF buffer statelessly
        const { pdf_id, registry_dict, values_dict } = await processPdf(req.file.buffer, inMemoryRegistry);

        // Update the basic in-memory registry
        inMemoryRegistry = { ...inMemoryRegistry, ...registry_dict };

        res.json({
            success: true,
            pdf_id,
            fieldsExtracted: Object.keys(values_dict).length,
            values: values_dict,
            registry: registry_dict[pdf_id]
        });

    } catch (error) {
        console.error('Error processing PDF:', error);
        res.status(500).json({ error: 'Failed to process PDF', details: error.message });
    }
});

// GET endpoint to return the current in-memory registry
app.get('/api/registry', (req, res) => {
    // Optionally load from file if memory is empty for POC robustness
    const fs = require('fs');
    const path = require('path');
    const REGISTRY_PATH = path.join(__dirname, 'outputs', 'pdf_registry.json');

    if (Object.keys(inMemoryRegistry).length === 0 && fs.existsSync(REGISTRY_PATH)) {
        try {
            const fileData = fs.readFileSync(REGISTRY_PATH, 'utf-8');
            inMemoryRegistry = JSON.parse(fileData);
        } catch (e) {
            console.warn('Could not read existing registry on disk:', e.message);
        }
    }

    res.json(inMemoryRegistry);
});

// POST endpoint to handle linking product configuration to a PDF Template
app.post('/api/config', (req, res) => {
    try {
        const { pdf_id, filename, config_body } = req.body;

        if (!pdf_id || !filename || !config_body) {
            return res.status(400).json({ error: 'Missing required parameters: pdf_id, filename, or config_body' });
        }

        const fs = require('fs');
        const path = require('path');

        // 1. Add PDF ID to the JSON config
        config_body.pdf_id = pdf_id;

        // 2. Save JSON config file in CONFIG_DIR
        const configDir = path.join(__dirname, 'config');
        if (!fs.existsSync(configDir)){
            fs.mkdirSync(configDir, { recursive: true });
        }

        const configPath = path.join(configDir, filename);
        fs.writeFileSync(configPath, JSON.stringify(config_body, null, 4), 'utf-8');

        // 3. Save reference link in outputs/assignment_cache.json
        const cachePath = path.join(__dirname, 'outputs', 'assignment_cache.json');
        let globalCache = {};

        if (fs.existsSync(cachePath)) {
            try {
                const cacheData = fs.readFileSync(cachePath, 'utf-8');
                globalCache = JSON.parse(cacheData);
            } catch (e) {
                // Ignore parse errors for corrupt cache
            }
        }

        let entry = globalCache[pdf_id] || {};
        if (typeof entry !== 'object' || !entry.field_mappings) {
            const fieldMappings = typeof entry === 'object' ? entry : {};
            entry = {
                product_config: filename,
                field_mappings: fieldMappings
            };
        } else {
            entry.product_config = filename;
        }

        globalCache[pdf_id] = entry;

        // Ensure outputs directory exists
        const outputsDir = path.join(__dirname, 'outputs');
        if (!fs.existsSync(outputsDir)) {
            fs.mkdirSync(outputsDir, { recursive: true });
        }

        fs.writeFileSync(cachePath, JSON.stringify(globalCache, null, 4), 'utf-8');

        res.json({
            success: true,
            message: `Configuration saved to ${filename} and linked to PDF ID ${pdf_id}`
        });

    } catch (error) {
        console.error('Error saving config:', error);
        res.status(500).json({ error: 'Failed to save configuration', details: error.message });
    }
});


// POST endpoint to handle filling and downloading the BlueTable DOCX
app.post('/api/generate-docx', async (req, res) => {
    try {
        const data = req.body;
        if (!data || Object.keys(data).length === 0) {
            return res.status(400).json({ error: 'Missing form data' });
        }

        const fs = require('fs');
        const path = require('path');
        const { fillBlueTableDocx } = require('./src/blue_table_tools/docx_generator');

        const templatePath = path.join(__dirname, 'resources', 'BlueTable.docx');
        if (!fs.existsSync(templatePath)) {
            return res.status(404).json({ error: 'Template DOCX not found' });
        }

        const templateBuffer = fs.readFileSync(templatePath);
        const filledBuffer = fillBlueTableDocx(templateBuffer, data);

        res.setHeader('Content-Disposition', 'attachment; filename="bluetable_filled.docx"');
        res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
        res.send(filledBuffer);

    } catch (error) {
        console.error('Error generating DOCX:', error);
        res.status(500).json({ error: 'Failed to generate DOCX', details: error.message });
    }
});

// POST endpoint to handle generating the Pre-filled PDF using pdf-lib
app.post('/api/generate-pdf', async (req, res) => {
    try {
        const data = req.body;
        if (!data || Object.keys(data).length === 0) {
            return res.status(400).json({ error: 'Missing form data' });
        }

        const fs = require('fs');
        const path = require('path');
        const { fillAcroformPdf } = require('./src/pdf_processor/inverter');

        const templatePath = path.join(__dirname, 'resources', 'OriginalApplication.pdf');
        if (!fs.existsSync(templatePath)) {
            return res.status(404).json({ error: 'Template PDF not found' });
        }

        const templateBuffer = fs.readFileSync(templatePath);
        const filledBytes = await fillAcroformPdf(templateBuffer, data);

        res.setHeader('Content-Disposition', 'attachment; filename="PreFilled_Application.pdf"');
        res.setHeader('Content-Type', 'application/pdf');
        // Convert Uint8Array to Buffer for express.send
        res.send(Buffer.from(filledBytes));

    } catch (error) {
        console.error('Error generating PDF:', error);
        res.status(500).json({ error: 'Failed to generate PDF', details: error.message });
    }
});

// ---------------------------------------------------------
// SIGNATURE GATEWAY (SESSION VAULT API)
// ---------------------------------------------------------

const vault = require('./src/signature_gateway/vault');

app.post('/api/vault/create', upload.single('pdf'), async (req, res) => {
    try {
        if (!req.file) return res.status(400).json({ error: 'No PDF file provided.' });

        const crypto = require('crypto');

        // 1. Re-extract structure using engine
        const { pdf_id, registry_dict, values_dict } = await processPdf(req.file.buffer, inMemoryRegistry);

        // 2. Try to get cache mapping
        const cachePath = path.join(__dirname, 'outputs', 'assignment_cache.json');
        let cacheMapping = null;
        if (fs.existsSync(cachePath)) {
            const cache = JSON.parse(fs.readFileSync(cachePath, 'utf-8'));
            if (cache[pdf_id] && cache[pdf_id].field_mappings) {
                cacheMapping = cache[pdf_id].field_mappings;
            }
        }

        if (!cacheMapping) {
            return res.status(400).json({ error: 'Unknown PDF Template. Map it first.' });
        }

        const fields = registry_dict[pdf_id].fields || [];
        const btData = vault.extractBtData(fields, cacheMapping, values_dict);
        btData.pdf_id = pdf_id;

        const customerName = btData.name || '';
        const identityId = btData.id_card_no || '';

        if (!customerName || !identityId) {
            return res.status(400).json({ error: 'Missing customer name or identity ID in mapping' });
        }

        const token = crypto.randomBytes(16).toString('hex');

        vault.addEntry(
            token, pdf_id, customerName, identityId, btData,
            req.file.buffer, registry_dict, cacheMapping
        );

        res.json({ success: true, token, customerName });

    } catch (e) {
        console.error(e);
        res.status(500).json({ error: 'Failed to create vault entry', details: e.message });
    }
});

app.get('/api/vault/verify', (req, res) => {
    const { token } = req.query;
    const entry = vault.getEntry(token);
    if (!entry) return res.status(404).json({ error: 'Invalid or expired token' });

    res.json({
        success: true,
        status: entry.status,
        customerName: entry.customer_name
    });
});

app.post('/api/vault/sign', async (req, res) => {
    try {
        const { token, identityId, signatureImageBase64 } = req.body;

        if (!vault.verifyIdentity(token, identityId)) {
            return res.status(403).json({ error: 'Identity verification failed or token invalid' });
        }

        const entry = vault.getEntry(token);
        const { stampSignatureOnPdf } = require('./src/signature_gateway/pdf_stamping');
        const { fillAcroformPdf } = require('./src/pdf_processor/inverter');
        const { fillBlueTableDocx } = require('./src/blue_table_tools/docx_generator');

        // Extract base64 part
        const base64Data = signatureImageBase64.replace(/^data:image\/png;base64,/, "");
        const sigBuffer = Buffer.from(base64Data, 'base64');

        // 1. Fill AcroForm
        const filledPdfBytes = await fillAcroformPdf(entry.pdf_bytes, entry.bt_data);

        // 2. Stamp Signature
        const finalPdfBytes = await stampSignatureOnPdf(
            Buffer.from(filledPdfBytes),
            sigBuffer,
            entry.pdf_id,
            entry.registry_dict,
            entry.cache_mapping
        );

        // 3. Fill DOCX
        const templateDocxPath = path.join(__dirname, 'resources', 'BlueTable.docx');
        const templateDocxBuffer = fs.readFileSync(templateDocxPath);
        const finalDocxBytes = fillBlueTableDocx(templateDocxBuffer, entry.bt_data);

        vault.saveSignedDocuments(token, finalPdfBytes, finalDocxBytes);

        res.json({ success: true });
    } catch (e) {
        console.error(e);
        res.status(500).json({ error: 'Failed to sign document', details: e.message });
    }
});

app.get('/api/vault/status', (req, res) => {
    const { token } = req.query;
    const entry = vault.getEntry(token);

    if (!entry) return res.status(404).json({ error: 'Invalid or expired token' });

    const elapsed = (Date.now() - entry.created_at) / 1000;
    const remaining = Math.floor(entry.ttl_seconds - elapsed);

    res.json({
        success: true,
        status: entry.status,
        remaining_seconds: remaining,
        customerName: entry.customer_name
    });
});

app.get('/api/vault/download/:token/:type', (req, res) => {
    const { token, type } = req.params;
    const entry = vault.getEntry(token);

    if (!entry || entry.status !== 'signed') {
        return res.status(404).json({ error: 'Document not found or not signed' });
    }

    if (type === 'pdf') {
        res.setHeader('Content-Disposition', `attachment; filename="Signed_${entry.customer_name.replace(/ /g, '_')}.pdf"`);
        res.setHeader('Content-Type', 'application/pdf');
        res.send(Buffer.from(entry.signed_pdf_bytes));
    } else if (type === 'docx') {
        res.setHeader('Content-Disposition', `attachment; filename="BlueTable_${entry.customer_name.replace(/ /g, '_')}.docx"`);
        res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
        res.send(Buffer.from(entry.signed_docx_bytes));
    } else {
        res.status(400).json({ error: 'Invalid type' });
    }
});

app.post('/api/vault/clear', (req, res) => {
    const { token } = req.body;
    vault.removeEntry(token);
    res.json({ success: true });
});

// Start the server if this file is run directly
if (require.main === module) {
    app.listen(port, () => {
        console.log(`Server listening on port ${port}`);
        console.log(`Visit http://localhost:${port} in your browser.`);
    });
}

module.exports = app; // export for testing
