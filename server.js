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


// Start the server if this file is run directly
if (require.main === module) {
    app.listen(port, () => {
        console.log(`Server listening on port ${port}`);
        console.log(`Visit http://localhost:${port} in your browser.`);
    });
}

module.exports = app; // export for testing
