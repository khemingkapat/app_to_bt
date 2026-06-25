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

	"gateway/client"

	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func setupTestServer(t *testing.T) (*echo.Echo, *HandlerContext) {
	e := echo.New()

	docClient, err := client.NewDocumentClient()
	require.NoError(t, err)

	hCtx := &HandlerContext{
		DocClient:        docClient,
		TemplatePDFPath:  "../../resources/OriginalApplication.pdf",
		TemplateDocxPath: "../../resources/BlueTable.docx",
	}

	return e, hCtx
}

func TestProcessPdf_Integration(t *testing.T) {
	if os.Getenv("SKIP_INTEGRATION_TEST") != "" {
		t.Skip("Skipping integration test")
	}

	e, hCtx := setupTestServer(t)
	defer hCtx.DocClient.Close()

	// Load real PDF
	pdfPath := "../../resources/OriginalApplication.pdf"
	pdfData, err := os.ReadFile(pdfPath)
	require.NoError(t, err)

	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	part, err := writer.CreateFormFile("pdf", "OriginalApplication.pdf")
	require.NoError(t, err)
	_, err = part.Write(pdfData)
	require.NoError(t, err)
	writer.Close()

	req := httptest.NewRequest(http.MethodPost, "/api/process-pdf", body)
	req.Header.Set(echo.HeaderContentType, writer.FormDataContentType())
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err = hCtx.ProcessPdfHandler(c)
	assert.NoError(t, err)
	assert.Equal(t, http.StatusOK, rec.Code)

	var resp map[string]interface{}
	err = json.Unmarshal(rec.Body.Bytes(), &resp)
	require.NoError(t, err)

	assert.NotEmpty(t, resp["pdf_id"])
	assert.Greater(t, resp["fieldsExtracted"], float64(0))
}

func TestGeneratePdf_Integration(t *testing.T) {
	if os.Getenv("SKIP_INTEGRATION_TEST") != "" {
		t.Skip("Skipping integration test")
	}

	e, hCtx := setupTestServer(t)
	defer hCtx.DocClient.Close()

	formData := map[string]string{
		"Full Name": "Integration Test User",
	}
	reqBody, _ := json.Marshal(map[string]interface{}{
		"form_data": formData,
	})

	req := httptest.NewRequest(http.MethodPost, "/api/generate-pdf", strings.NewReader(string(reqBody)))
	req.Header.Set(echo.HeaderContentType, echo.MIMEApplicationJSON)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := hCtx.GeneratePdfHandler(c)
	assert.NoError(t, err)
	assert.Equal(t, http.StatusOK, rec.Code)
	assert.Equal(t, "application/pdf", rec.Header().Get(echo.HeaderContentType))
	assert.NotEmpty(t, rec.Body.Bytes())
}

func TestGenerateDocx_Integration(t *testing.T) {
	if os.Getenv("SKIP_INTEGRATION_TEST") != "" {
		t.Skip("Skipping integration test")
	}

	e, hCtx := setupTestServer(t)
	defer hCtx.DocClient.Close()

	formData := map[string]string{
		"name": "Integration Test User",
	}
	reqBody, _ := json.Marshal(map[string]interface{}{
		"pdf_id":    "test-pdf-id",
		"form_data": formData,
	})

	req := httptest.NewRequest(http.MethodPost, "/api/generate-docx", strings.NewReader(string(reqBody)))
	req.Header.Set(echo.HeaderContentType, echo.MIMEApplicationJSON)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := hCtx.GenerateDocxHandler(c)
	assert.NoError(t, err)
	assert.Equal(t, http.StatusOK, rec.Code)
	assert.Equal(t, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", rec.Header().Get(echo.HeaderContentType))
	assert.NotEmpty(t, rec.Body.Bytes())
}
