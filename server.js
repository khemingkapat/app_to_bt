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

// Start the server if this file is run directly
if (require.main === module) {
    app.listen(port, () => {
        console.log(`Server listening on port ${port}`);
        console.log(`Visit http://localhost:${port} in your browser.`);
    });
}

module.exports = app; // export for testing
