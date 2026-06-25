package handlers

import (
	"bytes"
	"context"
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
	"google.golang.org/grpc"
)

// MockDocumentServiceClient is a mock of document.DocumentServiceClient
type MockDocumentServiceClient struct {
	mock.Mock
}

func (m *MockDocumentServiceClient) ProcessPdf(ctx context.Context, in *document.ProcessPdfRequest, opts ...grpc.CallOption) (*document.ProcessPdfResponse, error) {
	args := m.Called(ctx, in)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*document.ProcessPdfResponse), args.Error(1)
}

func (m *MockDocumentServiceClient) GeneratePdf(ctx context.Context, in *document.GeneratePdfRequest, opts ...grpc.CallOption) (*document.GeneratePdfResponse, error) {
	args := m.Called(ctx, in)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*document.GeneratePdfResponse), args.Error(1)
}

func (m *MockDocumentServiceClient) GenerateDocx(ctx context.Context, in *document.GenerateDocxRequest, opts ...grpc.CallOption) (*document.GenerateDocxResponse, error) {
	args := m.Called(ctx, in)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*document.GenerateDocxResponse), args.Error(1)
}

func (m *MockDocumentServiceClient) StampSignature(ctx context.Context, in *document.StampSignatureRequest, opts ...grpc.CallOption) (*document.StampSignatureResponse, error) {
	args := m.Called(ctx, in)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*document.StampSignatureResponse), args.Error(1)
}

func TestProcessPdfHandler(t *testing.T) {
	e := echo.New()
	mockClient := new(MockDocumentServiceClient)
	h := &HandlerContext{
		DocClient: &client.DocumentClient{Client: mockClient},
	}

	// Valid PDF
	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	part, _ := writer.CreateFormFile("pdf", "test.pdf")
	part.Write([]byte("%PDF-dummy-content"))
	writer.Close()

	req := httptest.NewRequest(http.MethodPost, "/api/process-pdf", body)
	req.Header.Set(echo.HeaderContentType, writer.FormDataContentType())
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	mockClient.On("ProcessPdf", mock.Anything, mock.Anything).Return(&document.ProcessPdfResponse{
		PdfId:        "test-id",
		Values:       map[string]string{"field1": "value1"},
		RegistryJson: "{}",
	}, nil)

	if assert.NoError(t, h.ProcessPdfHandler(c)) {
		assert.Equal(t, http.StatusOK, rec.Code)
		var resp map[string]interface{}
		json.Unmarshal(rec.Body.Bytes(), &resp)
		assert.Equal(t, "test-id", resp["pdf_id"])
		assert.Equal(t, float64(1), resp["fieldsExtracted"])
	}

	// Invalid PDF (no magic bytes)
	body = &bytes.Buffer{}
	writer = multipart.NewWriter(body)
	part, _ = writer.CreateFormFile("pdf", "test.pdf")
	part.Write([]byte("not-a-pdf"))
	writer.Close()

	req = httptest.NewRequest(http.MethodPost, "/api/process-pdf", body)
	req.Header.Set(echo.HeaderContentType, writer.FormDataContentType())
	rec = httptest.NewRecorder()
	c = e.NewContext(req, rec)

	h.ProcessPdfHandler(c)
	assert.Equal(t, http.StatusBadRequest, rec.Code)
	assert.Contains(t, rec.Body.String(), "invalid PDF")
}

func TestGeneratePdfHandler(t *testing.T) {
	e := echo.New()
	mockClient := new(MockDocumentServiceClient)

	// Create dummy template
	tmpFile, _ := os.CreateTemp("", "template.pdf")
	defer os.Remove(tmpFile.Name())
	tmpFile.Write([]byte("dummy-pdf-template"))
	tmpFile.Close()

	h := &HandlerContext{
		DocClient:       &client.DocumentClient{Client: mockClient},
		TemplatePDFPath: tmpFile.Name(),
	}

	jsonReq := `{"form_data": {"name": "John Doe"}}`
	req := httptest.NewRequest(http.MethodPost, "/api/generate-pdf", strings.NewReader(jsonReq))
	req.Header.Set(echo.HeaderContentType, echo.MIMEApplicationJSON)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	mockClient.On("GeneratePdf", mock.Anything, mock.Anything).Return(&document.GeneratePdfResponse{
		PdfBytes: []byte("generated-pdf"),
	}, nil)

	if assert.NoError(t, h.GeneratePdfHandler(c)) {
		assert.Equal(t, http.StatusOK, rec.Code)
		assert.Equal(t, "application/pdf", rec.Header().Get(echo.HeaderContentType))
		assert.Equal(t, "generated-pdf", rec.Body.String())
	}
}

func TestGenerateDocxHandler(t *testing.T) {
	e := echo.New()
	mockClient := new(MockDocumentServiceClient)

	// Create dummy template
	tmpFile, _ := os.CreateTemp("", "template.docx")
	defer os.Remove(tmpFile.Name())
	tmpFile.Write([]byte("dummy-docx-template"))
	tmpFile.Close()

	h := &HandlerContext{
		DocClient:        &client.DocumentClient{Client: mockClient},
		TemplateDocxPath: tmpFile.Name(),
	}

	jsonReq := `{"pdf_id": "test-id", "form_data": {"name": "John Doe"}}`
	req := httptest.NewRequest(http.MethodPost, "/api/generate-docx", strings.NewReader(jsonReq))
	req.Header.Set(echo.HeaderContentType, echo.MIMEApplicationJSON)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	mockClient.On("GenerateDocx", mock.Anything, mock.Anything).Return(&document.GenerateDocxResponse{
		DocxBytes: []byte("generated-docx"),
	}, nil)

	if assert.NoError(t, h.GenerateDocxHandler(c)) {
		assert.Equal(t, http.StatusOK, rec.Code)
		assert.Equal(t, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", rec.Header().Get(echo.HeaderContentType))
		assert.Equal(t, "generated-docx", rec.Body.String())
	}

	// Missing pdf_id
	jsonReq = `{"form_data": {"name": "John Doe"}}`
	req = httptest.NewRequest(http.MethodPost, "/api/generate-docx", strings.NewReader(jsonReq))
	req.Header.Set(echo.HeaderContentType, echo.MIMEApplicationJSON)
	rec = httptest.NewRecorder()
	c = e.NewContext(req, rec)

	h.GenerateDocxHandler(c)
	assert.Equal(t, http.StatusBadRequest, rec.Code)
	assert.Contains(t, rec.Body.String(), "pdf_id is required")
}

func TestStampSignatureHandler(t *testing.T) {
	e := echo.New()
	mockClient := new(MockDocumentServiceClient)
	h := &HandlerContext{
		DocClient: &client.DocumentClient{Client: mockClient},
	}

	token := GenerateSecureToken()
	GlobalVault.AddEntry(&VaultEntry{
		Token:      token,
		IdentityID: "ID123",
		Status:     "pending",
		CreatedAt:  time.Now(),
		TTLSeconds: 900,
	})

	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)

	pdfPart, _ := writer.CreateFormFile("pdf", "test.pdf")
	pdfPart.Write([]byte("%PDF-dummy"))

	sigPart, _ := writer.CreateFormFile("signature", "sig.png")
	sigPart.Write([]byte("\x89PNG\r\n\x1a\n-dummy"))

	writer.WriteField("token", token)
	writer.WriteField("identity_id", "ID123")
	writer.WriteField("pdf_id", "test-id")
	writer.WriteField("registry_json", "{}")
	writer.WriteField("cache_mapping_json", "{}")
	writer.Close()

	req := httptest.NewRequest(http.MethodPost, "/api/stamp-signature", body)
	req.Header.Set(echo.HeaderContentType, writer.FormDataContentType())
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	mockClient.On("StampSignature", mock.Anything, mock.Anything).Return(&document.StampSignatureResponse{
		PdfBytes: []byte("stamped-pdf"),
	}, nil)

	if assert.NoError(t, h.StampSignatureHandler(c)) {
		assert.Equal(t, http.StatusOK, rec.Code)
		assert.Equal(t, "application/pdf", rec.Header().Get(echo.HeaderContentType))
		assert.Equal(t, "stamped-pdf", rec.Body.String())
	}

	// Unauthorized (missing token)
	body = &bytes.Buffer{}
	writer = multipart.NewWriter(body)
	pdfPart, _ = writer.CreateFormFile("pdf", "test.pdf")
	pdfPart.Write([]byte("%PDF-dummy"))
	sigPart, _ = writer.CreateFormFile("signature", "sig.png")
	sigPart.Write([]byte("\x89PNG\r\n\x1a\n-dummy"))
	writer.WriteField("pdf_id", "test-id")
	writer.Close()

	req = httptest.NewRequest(http.MethodPost, "/api/stamp-signature", body)
	req.Header.Set(echo.HeaderContentType, writer.FormDataContentType())
	rec = httptest.NewRecorder()
	c = e.NewContext(req, rec)

	h.StampSignatureHandler(c)
	assert.Equal(t, http.StatusUnauthorized, rec.Code)

	// Forbidden (wrong ID)
	body = &bytes.Buffer{}
	writer = multipart.NewWriter(body)
	pdfPart, _ = writer.CreateFormFile("pdf", "test.pdf")
	pdfPart.Write([]byte("%PDF-dummy"))
	sigPart, _ = writer.CreateFormFile("signature", "sig.png")
	sigPart.Write([]byte("\x89PNG\r\n\x1a\n-dummy"))
	writer.WriteField("token", token)
	writer.WriteField("identity_id", "WRONG")
	writer.WriteField("pdf_id", "test-id")
	writer.Close()

	req = httptest.NewRequest(http.MethodPost, "/api/stamp-signature", body)
	req.Header.Set(echo.HeaderContentType, writer.FormDataContentType())
	rec = httptest.NewRecorder()
	c = e.NewContext(req, rec)

	h.StampSignatureHandler(c)
	assert.Equal(t, http.StatusForbidden, rec.Code)

	// Invalid signature (not PNG)
	body = &bytes.Buffer{}
	writer = multipart.NewWriter(body)
	pdfPart, _ = writer.CreateFormFile("pdf", "test.pdf")
	pdfPart.Write([]byte("%PDF-dummy"))
	sigPart, _ = writer.CreateFormFile("signature", "sig.png")
	sigPart.Write([]byte("not-a-png"))
	writer.WriteField("token", token)
	writer.WriteField("identity_id", "ID123")
	writer.WriteField("pdf_id", "test-id")
	writer.WriteField("registry_json", "{}")
	writer.WriteField("cache_mapping_json", "{}")
	writer.Close()

	req = httptest.NewRequest(http.MethodPost, "/api/stamp-signature", body)
	req.Header.Set(echo.HeaderContentType, writer.FormDataContentType())
	rec = httptest.NewRecorder()
	c = e.NewContext(req, rec)

	h.StampSignatureHandler(c)
	assert.Equal(t, http.StatusBadRequest, rec.Code)
	assert.Contains(t, rec.Body.String(), "invalid PNG")
}
