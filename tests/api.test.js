const request = require('supertest');
const path = require('path');
const fs = require('fs');
const app = require('../server'); // Fix path

describe('POST /api/process-pdf', () => {

    it('should return 400 if no file is uploaded', async () => {
        const response = await request(app).post('/api/process-pdf');
        expect(response.status).toBe(400);
        expect(response.body.error).toBe('No PDF file provided.');
    });

    it('should process a valid PDF statelessly', async () => {
        const pdfPath = path.join(__dirname, '../resources/FilledApplication.pdf');

        // Skip test if test PDF doesn't exist locally
        if (!fs.existsSync(pdfPath)) {
            console.warn(`Test skipped, ${pdfPath} not found`);
            return;
        }

        const response = await request(app)
            .post('/api/process-pdf')
            .attach('pdf', pdfPath);

        expect(response.status).toBe(200);
        expect(response.body.success).toBe(true);
        expect(response.body).toHaveProperty('pdf_id');
        expect(response.body.fieldsExtracted).toBeGreaterThan(0);
        expect(Object.keys(response.body.values).length).toBeGreaterThan(0);
        expect(response.body).toHaveProperty('registry');
    });
});

describe('Config Manager API Endpoints', () => {
    let mockPdfId = 'test_pdf_123';

    it('GET /api/registry should return the in-memory registry or fallback empty object', async () => {
        const response = await request(app).get('/api/registry');
        expect(response.status).toBe(200);
        expect(typeof response.body).toBe('object');
    });

    it('POST /api/config should fail without required params', async () => {
        const response = await request(app)
            .post('/api/config')
            .send({ pdf_id: mockPdfId });
        expect(response.status).toBe(400);
        expect(response.body.error).toBe('Missing required parameters: pdf_id, filename, or config_body');
    });

    it('POST /api/config should save config and update cache', async () => {
        const configBody = { product_name: "Test Insurance", pricing: { factor: 1.5 } };
        const response = await request(app)
            .post('/api/config')
            .send({
                pdf_id: mockPdfId,
                filename: 'test_insurance.json',
                config_body: configBody
            });

        expect(response.status).toBe(200);
        expect(response.body.success).toBe(true);

        // Verify files were actually created
        const configPath = path.join(__dirname, '../config', 'test_insurance.json');
        const cachePath = path.join(__dirname, '../outputs', 'assignment_cache.json');

        expect(fs.existsSync(configPath)).toBe(true);
        expect(fs.existsSync(cachePath)).toBe(true);

        const savedConfig = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
        expect(savedConfig.pdf_id).toBe(mockPdfId);
        expect(savedConfig.product_name).toBe("Test Insurance");

        const cache = JSON.parse(fs.readFileSync(cachePath, 'utf-8'));
        expect(cache[mockPdfId].product_config).toBe('test_insurance.json');
        expect(typeof cache[mockPdfId].field_mappings).toBe('object');

        // Clean up mock files created during test
        fs.unlinkSync(configPath);
    });
});

describe('Document Generation API Endpoints', () => {
    const mockData = {
        name: "John Doe",
        dob: "10/05/1990",
        id_card_no: "1234567890123",
        product_name: "ESSENTIAL",
        plan: "ESSENTIAL2-IPD",
        deductible: "100k",
        cover_spouse: "yes",
        sp_name: "Jane Doe"
    };

    it('POST /api/generate-docx should return a DOCX buffer', async () => {
        const response = await request(app)
            .post('/api/generate-docx')
            .send(mockData)
            .responseType('blob'); // Ensure supertest handles binary data

        expect(response.status).toBe(200);
        expect(response.headers['content-type']).toBe('application/vnd.openxmlformats-officedocument.wordprocessingml.document');
        expect(response.headers['content-disposition']).toBe('attachment; filename="bluetable_filled.docx"');
        expect(response.body).toBeInstanceOf(Buffer);
        expect(response.body.length).toBeGreaterThan(100);
    });

    it('POST /api/generate-pdf should return a PDF buffer', async () => {
        const response = await request(app)
            .post('/api/generate-pdf')
            .send(mockData)
            .responseType('blob'); // Ensure supertest handles binary data

        expect(response.status).toBe(200);
        expect(response.headers['content-type']).toBe('application/pdf');
        expect(response.headers['content-disposition']).toBe('attachment; filename="PreFilled_Application.pdf"');
        expect(response.body).toBeInstanceOf(Buffer);
        expect(response.body.length).toBeGreaterThan(100);
    });

    it('POST endpoints should handle missing data', async () => {
        const resDocx = await request(app).post('/api/generate-docx').send({});
        expect(resDocx.status).toBe(400);

        const resPdf = await request(app).post('/api/generate-pdf').send({});
        expect(resPdf.status).toBe(400);
    });
});

describe('Signature Gateway Vault API Endpoints', () => {
    let mockToken = null;
    let mockIdentityId = "1234567890123";

    it('POST /api/vault/create should fail without PDF', async () => {
        const response = await request(app).post('/api/vault/create');
        expect(response.status).toBe(400);
    });

    // Mock PDF creation is difficult without setting up the entire registry and cache context
    // We will test the vault module directly instead of the Express wrapper

    const vault = require('../src/signature_gateway/vault');

    it('Vault module should add, get, verify, and remove entries', () => {
        const token = "mock_token_123";

        vault.addEntry(
            token, "pdf_id_123", "John Doe", "A1B2C3D4", { name: "John" },
            Buffer.from("fake_pdf"), {}, {}, 900
        );

        const entry = vault.getEntry(token);
        expect(entry).toBeDefined();
        expect(entry.customer_name).toBe("John Doe");
        expect(entry.status).toBe("pending");

        // Fails with wrong ID
        expect(vault.verifyIdentity(token, "wrong_id")).toBe(false);

        // Succeeds with correct ID, case insensitive and alphanumeric only
        expect(vault.verifyIdentity(token, "a 1-b-2 c3d4!")).toBe(true);

        // Verify ID is wiped after success
        expect(vault.getEntry(token).identity_id).toBeNull();

        vault.saveSignedDocuments(token, Buffer.from("signed_pdf"), Buffer.from("signed_docx"));

        const signedEntry = vault.getEntry(token);
        expect(signedEntry.status).toBe("signed");
        expect(signedEntry.signed_pdf_bytes.toString()).toBe("signed_pdf");

        vault.removeEntry(token);
        expect(vault.getEntry(token)).toBeUndefined();
    });
});
