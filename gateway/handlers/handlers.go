package handlers

import (
	"context"
	"io"
	"net/http"
	"os"

	"gateway/client"
	"gateway/proto/document"

	"github.com/labstack/echo/v4"
)

type HandlerContext struct {
	DocClient        *client.DocumentClient
	TemplatePDFPath  string
	TemplateDocxPath string
}

func (h *HandlerContext) ProcessPdfHandler(c echo.Context) error {
	file, err := c.FormFile("pdf")
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "pdf file is required"})
	}

	if err := ValidateFileSize(file.Size); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": err.Error()})
	}

	src, err := file.Open()
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to open file"})
	}
	defer src.Close()

	if err := ValidatePDFMagicBytes(src); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": err.Error()})
	}

	// Seek back to start for full read
	if seeker, ok := src.(io.Seeker); ok {
		if _, err := seeker.Seek(0, io.SeekStart); err != nil {
			return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to seek file"})
		}
	}

	pdfBytes, err := io.ReadAll(src)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to read file"})
	}

	resp, err := h.DocClient.Client.ProcessPdf(context.Background(), &document.ProcessPdfRequest{
		PdfBytes: pdfBytes,
	})
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"pdf_id":          resp.PdfId,
		"values":          resp.Values,
		"registry_json":   resp.RegistryJson,
		"fieldsExtracted": len(resp.Values),
	})
}

func (h *HandlerContext) GeneratePdfHandler(c echo.Context) error {
	var req struct {
		FormData map[string]string `json:"form_data"`
	}
	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid JSON body"})
	}

	pdfBytes, err := os.ReadFile(h.TemplatePDFPath)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to read template PDF"})
	}

	resp, err := h.DocClient.Client.GeneratePdf(context.Background(), &document.GeneratePdfRequest{
		PdfBytes: pdfBytes,
		FormData: req.FormData,
	})
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.Blob(http.StatusOK, "application/pdf", resp.PdfBytes)
}

func (h *HandlerContext) GenerateDocxHandler(c echo.Context) error {
	var req struct {
		PdfId    string            `json:"pdf_id"`
		FormData map[string]string `json:"form_data"`
	}
	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid JSON body"})
	}
	if req.PdfId == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "pdf_id is required"})
	}

	docxBytes, err := os.ReadFile(h.TemplateDocxPath)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to read template DOCX"})
	}

	resp, err := h.DocClient.Client.GenerateDocx(context.Background(), &document.GenerateDocxRequest{
		DocxBytes: docxBytes,
		FormData:  req.FormData,
	})
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.Blob(http.StatusOK, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", resp.DocxBytes)
}

func (h *HandlerContext) StampSignatureHandler(c echo.Context) error {
	pdfFile, err := c.FormFile("pdf")
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "pdf file is required"})
	}
	if err := ValidateFileSize(pdfFile.Size); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "pdf: " + err.Error()})
	}

	sigFile, err := c.FormFile("signature")
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "signature file is required"})
	}
	if err := ValidateFileSize(sigFile.Size); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "signature: " + err.Error()})
	}

	pdfId := c.FormValue("pdf_id")
	if pdfId == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "pdf_id is required"})
	}
	registryJson := c.FormValue("registry_json")
	if registryJson == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "registry_json is required"})
	}
	cacheMappingJson := c.FormValue("cache_mapping_json")
	if cacheMappingJson == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "cache_mapping_json is required"})
	}

	pdfSrc, err := pdfFile.Open()
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to open pdf file"})
	}
	defer pdfSrc.Close()

	if err := ValidatePDFMagicBytes(pdfSrc); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": err.Error()})
	}
	if seeker, ok := pdfSrc.(io.Seeker); ok {
		if _, err := seeker.Seek(0, io.SeekStart); err != nil {
			return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to seek pdf file"})
		}
	}
	pdfBytes, err := io.ReadAll(pdfSrc)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to read pdf file"})
	}

	sigSrc, err := sigFile.Open()
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to open signature file"})
	}
	defer sigSrc.Close()

	if err := ValidatePNGMagicBytes(sigSrc); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": err.Error()})
	}
	if seeker, ok := sigSrc.(io.Seeker); ok {
		if _, err := seeker.Seek(0, io.SeekStart); err != nil {
			return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to seek signature file"})
		}
	}
	sigBytes, err := io.ReadAll(sigSrc)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to read signature file"})
	}

	resp, err := h.DocClient.Client.StampSignature(context.Background(), &document.StampSignatureRequest{
		PdfBytes:            pdfBytes,
		SignatureImageBytes: sigBytes,
		PdfId:               pdfId,
		RegistryJson:        registryJson,
		CacheMappingJson:    cacheMappingJson,
	})
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.Blob(http.StatusOK, "application/pdf", resp.PdfBytes)
}
