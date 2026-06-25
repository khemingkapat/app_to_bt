package handlers

import (
	"bytes"
	"encoding/json"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	"gateway/client"
	"gateway/proto/document"

	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

func TestSignatureIdentityVerificationE2E(t *testing.T) {
	e := echo.New()
	mockClient := new(MockDocumentServiceClient)
	h := &HandlerContext{
		DocClient: &client.DocumentClient{Client: mockClient},
	}

	// 1. Setup a vault entry
	token := GenerateSecureToken()
	pdfId := "test-pdf-id"
	identityID := "ABC123456"
	customerName := "John Doe"

	mapping := map[string]interface{}{
		"field1": "name",
		"field2": "id_card_no",
	}
	mappingJSON, _ := json.Marshal(mapping)

	GlobalVault.AddEntry(&VaultEntry{
		Token:            token,
		PdfId:            pdfId,
		CustomerName:     customerName,
		IdentityID:       identityID,
		Status:           "pending",
		CreatedAt:        time.Now(),
		TTLSeconds:       900,
		RegistryJSON:     "{}",
		CacheMappingJSON: string(mappingJSON),
		FormData:         map[string]string{"field1": customerName, "field2": identityID},
		PdfBytes:         []byte("%PDF-template"),
	})

	// 2. Test POST /api/vault/verify-identity - Invalid ID
	verifyReqBody, _ := json.Marshal(map[string]string{
		"token":      token,
		"identityId": "WRONG_ID",
	})
	req := httptest.NewRequest(http.MethodPost, "/api/vault/verify-identity", strings.NewReader(string(verifyReqBody)))
	req.Header.Set(echo.HeaderContentType, echo.MIMEApplicationJSON)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	if assert.NoError(t, h.VaultVerifyIdentityHandler(c)) {
		assert.Equal(t, http.StatusForbidden, rec.Code)
		assert.Contains(t, rec.Body.String(), "Identity verification failed")
	}

	// 3. Test POST /api/vault/verify-identity - Valid ID
	verifyReqBody, _ = json.Marshal(map[string]string{
		"token":      token,
		"identityId": identityID,
	})
	req = httptest.NewRequest(http.MethodPost, "/api/vault/verify-identity", strings.NewReader(string(verifyReqBody)))
	req.Header.Set(echo.HeaderContentType, echo.MIMEApplicationJSON)
	rec = httptest.NewRecorder()
	c = e.NewContext(req, rec)

	if assert.NoError(t, h.VaultVerifyIdentityHandler(c)) {
		assert.Equal(t, http.StatusOK, rec.Code)
		var resp map[string]interface{}
		json.Unmarshal(rec.Body.Bytes(), &resp)
		assert.Equal(t, customerName, resp["customerName"])
		assert.NotNil(t, resp["planDetails"])
	}

	// 4. Test POST /api/stamp-signature - Unauthorized (missing/invalid token)
	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	pdfPart, _ := writer.CreateFormFile("pdf", "test.pdf")
	pdfPart.Write([]byte("%PDF-content"))
	sigPart, _ := writer.CreateFormFile("signature", "sig.png")
	sigPart.Write([]byte("\x89PNG\r\n\x1a\n"))
	writer.WriteField("token", "invalid-token")
	writer.WriteField("identity_id", identityID)
	writer.WriteField("pdf_id", pdfId)
	writer.Close()

	req = httptest.NewRequest(http.MethodPost, "/api/stamp-signature", body)
	req.Header.Set(echo.HeaderContentType, writer.FormDataContentType())
	rec = httptest.NewRecorder()
	c = e.NewContext(req, rec)

	h.StampSignatureHandler(c)
	assert.Equal(t, http.StatusUnauthorized, rec.Code)

	// 5. Test POST /api/stamp-signature - Authorized
	body = &bytes.Buffer{}
	writer = multipart.NewWriter(body)
	pdfPart, _ = writer.CreateFormFile("pdf", "test.pdf")
	pdfPart.Write([]byte("%PDF-content"))
	sigPart, _ = writer.CreateFormFile("signature", "sig.png")
	sigPart.Write([]byte("\x89PNG\r\n\x1a\n"))
	writer.WriteField("token", token)
	writer.WriteField("identity_id", identityID)
	writer.WriteField("pdf_id", pdfId)
	writer.WriteField("registry_json", "{}")
	writer.WriteField("cache_mapping_json", "{}")
	writer.Close()

	req = httptest.NewRequest(http.MethodPost, "/api/stamp-signature", body)
	req.Header.Set(echo.HeaderContentType, writer.FormDataContentType())
	rec = httptest.NewRecorder()
	c = e.NewContext(req, rec)

	mockClient.On("StampSignature", mock.Anything, mock.Anything).Return(&document.StampSignatureResponse{
		PdfBytes: []byte("stamped-pdf"),
	}, nil)

	if assert.NoError(t, h.StampSignatureHandler(c)) {
		assert.Equal(t, http.StatusOK, rec.Code)
		assert.Equal(t, "application/pdf", rec.Header().Get(echo.HeaderContentType))
	}

	// 6. Test POST /api/vault/sign - Full Success
	signReqBody, _ := json.Marshal(map[string]string{
		"token":                token,
		"identityId":           identityID,
		"signatureImageBase64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
	})
	req = httptest.NewRequest(http.MethodPost, "/api/vault/sign", strings.NewReader(string(signReqBody)))
	req.Header.Set(echo.HeaderContentType, echo.MIMEApplicationJSON)
	rec = httptest.NewRecorder()
	c = e.NewContext(req, rec)

	// Mock required gRPC calls for vault sign
	mockClient.On("GeneratePdf", mock.Anything, mock.Anything).Return(&document.GeneratePdfResponse{
		PdfBytes: []byte("prefilled-pdf"),
	}, nil)
	// mockClient.On("StampSignature", ...) already mocked above but might need different arguments if called again.
	// Since we are using mock.Anything it should be fine, or we can use Unset and re-mock.

	mockClient.On("GenerateDocx", mock.Anything, mock.Anything).Return(&document.GenerateDocxResponse{
		DocxBytes: []byte("generated-docx"),
	}, nil)

	// Update TemplateDocxPath for handler
	tmpDocx, _ := os.CreateTemp("", "template.docx")
	defer os.Remove(tmpDocx.Name())
	h.TemplateDocxPath = tmpDocx.Name()

	if assert.NoError(t, h.VaultSignHandler(c)) {
		assert.Equal(t, http.StatusOK, rec.Code)

		// Verify status changed to signed
		entry := GlobalVault.GetEntry(token)
		assert.NotNil(t, entry)
		assert.Equal(t, "signed", entry.Status)
	}
}
