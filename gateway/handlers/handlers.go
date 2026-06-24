package handlers

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

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

	hash := sha256.Sum256(pdfBytes)
	c.Set("payload_hash", hex.EncodeToString(hash[:]))

	resp, err := h.DocClient.Client.ProcessPdf(context.Background(), &document.ProcessPdfRequest{
		PdfBytes: pdfBytes,
	})
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	// Load assignment cache and configuration
	var cacheMappings interface{}
	var productOptions interface{}
	cachePath := "../outputs/assignment_cache.json"
	configName := "health_and_accident_insurance.json"

	if cacheFile, err := os.Open(cachePath); err == nil {
		defer cacheFile.Close()
		var globalCache map[string]interface{}
		if err := json.NewDecoder(cacheFile).Decode(&globalCache); err == nil {
			if entry, ok := globalCache[resp.PdfId]; ok {
				if entryMap, ok := entry.(map[string]interface{}); ok {
					if fm, ok := entryMap["field_mappings"]; ok {
						cacheMappings = fm
					} else {
						// Backward-compatibility: flat map
						cacheMappings = entry
					}

					if pc, ok := entryMap["product_config"].(string); ok && pc != "" {
						configName = pc
					}
				}
			}
		}
	}

	// Always load product config options (falls back to default if not in cache)
	configPath := "../config/" + configName
	if configFile, err := os.Open(configPath); err == nil {
		defer configFile.Close()
		var fullConfig map[string]interface{}
		if err := json.NewDecoder(configFile).Decode(&fullConfig); err == nil {
			if po, ok := fullConfig["product_options"]; ok {
				productOptions = po
			}
		}
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"pdf_id":           resp.PdfId,
		"values":           resp.Values,
		"registry_json":    resp.RegistryJson,
		"fieldsExtracted":  len(resp.Values),
		"assignment_cache": cacheMappings,
		"product_options":  productOptions,
	})
}

func (h *HandlerContext) GeneratePdfHandler(c echo.Context) error {
	var req struct {
		FormData map[string]string `json:"form_data"`
	}

	bodyBytes, err := io.ReadAll(c.Request().Body)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "failed to read request body"})
	}
	// Restore body for Bind
	c.Request().Body = io.NopCloser(bytes.NewBuffer(bodyBytes))

	hash := sha256.Sum256(bodyBytes)
	c.Set("payload_hash", hex.EncodeToString(hash[:]))

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

	bodyBytes, err := io.ReadAll(c.Request().Body)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "failed to read request body"})
	}
	// Restore body for Bind
	c.Request().Body = io.NopCloser(bytes.NewBuffer(bodyBytes))

	hash := sha256.Sum256(bodyBytes)
	c.Set("payload_hash", hex.EncodeToString(hash[:]))

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

	h256 := sha256.New()
	h256.Write(pdfBytes)
	h256.Write(sigBytes)
	hash := h256.Sum(nil)
	c.Set("payload_hash", hex.EncodeToString(hash))

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

func (h *HandlerContext) VaultCreateHandler(c echo.Context) error {
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

	var fieldMappings map[string]interface{}
	cachePath := "../outputs/assignment_cache.json"
	if cacheFile, err := os.Open(cachePath); err == nil {
		defer cacheFile.Close()
		var globalCache map[string]interface{}
		if err := json.NewDecoder(cacheFile).Decode(&globalCache); err == nil {
			if entry, ok := globalCache[resp.PdfId]; ok {
				if entryMap, ok := entry.(map[string]interface{}); ok {
					if fm, ok := entryMap["field_mappings"].(map[string]interface{}); ok {
						fieldMappings = fm
					} else {
						fieldMappings = make(map[string]interface{})
						for k, v := range entryMap {
							if k != "product_config" && k != "field_mappings" {
								fieldMappings[k] = v
							}
						}
					}
				}
			}
		}
	}

	if fieldMappings == nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "PDF template mapping config not found in assignment cache. Please map the template fields first."})
	}

	var customerName, identityID string
	for pdfField, mapping := range fieldMappings {
		var btKey string
		if mStr, ok := mapping.(string); ok {
			btKey = mStr
		} else if mObj, ok := mapping.(map[string]interface{}); ok {
			if bk, ok := mObj["bt_key"].(string); ok {
				btKey = bk
			}
		}
		if btKey == "name" {
			customerName = resp.Values[pdfField]
		} else if btKey == "id_card_no" {
			identityID = resp.Values[pdfField]
		}
	}

	if customerName == "" || identityID == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "Customer name or ID number mapping could not be extracted from the PDF template. Ensure 'name' and 'id_card_no' are mapped."})
	}

	token := GenerateSecureToken()
	cacheMappingJSON, _ := json.Marshal(fieldMappings)

	GlobalVault.AddEntry(&VaultEntry{
		Token:            token,
		PdfId:            resp.PdfId,
		CustomerName:     customerName,
		IdentityID:       identityID,
		Status:           "pending",
		CreatedAt:        time.Now(),
		TTLSeconds:       900,
		RegistryJSON:     resp.RegistryJson,
		CacheMappingJSON: string(cacheMappingJSON),
		FormData:         resp.Values,
		PdfBytes:         pdfBytes,
	})

	return c.JSON(http.StatusOK, map[string]interface{}{
		"token":        token,
		"customerName": customerName,
	})
}

func (h *HandlerContext) VaultVerifyIdentityHandler(c echo.Context) error {
	var req struct {
		Token      string `json:"token"`
		IdentityID string `json:"identityId"`
	}

	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid JSON body"})
	}

	entry := GlobalVault.GetEntry(req.Token)
	if entry == nil {
		return c.JSON(http.StatusNotFound, map[string]string{"error": "Vault session expired or invalid"})
	}

	if NormalizeID(req.IdentityID) != NormalizeID(entry.IdentityID) {
		return c.JSON(http.StatusForbidden, map[string]string{"error": "Identity verification failed"})
	}

	// Resolve plan and deductible from form data using mappings
	var fieldMappings map[string]interface{}
	if err := json.Unmarshal([]byte(entry.CacheMappingJSON), &fieldMappings); err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to parse vault mapping config"})
	}

	var resolvedPlan, resolvedDeductible string
	for pdfField, mapping := range fieldMappings {
		var btKey string
		var choicesMap map[string]interface{}
		if mStr, ok := mapping.(string); ok {
			btKey = mStr
		} else if mObj, ok := mapping.(map[string]interface{}); ok {
			if bk, ok := mObj["bt_key"].(string); ok {
				btKey = bk
			}
			if cm, ok := mObj["choices_map"].(map[string]interface{}); ok {
				choicesMap = cm
			}
		}

		if (btKey == "plan" || btKey == "deductible") && entry.FormData[pdfField] != "" {
			val := entry.FormData[pdfField]
			finalVal := val
			if choicesMap != nil && strings.HasPrefix(val, "/") {
				if rVal, ok := choicesMap[val].(string); ok {
					finalVal = rVal
				}
			}

			if btKey == "plan" {
				if strings.Contains(finalVal, " DD ") {
					finalVal = strings.TrimSpace(strings.Split(finalVal, " DD ")[0])
				}
				// We take the first non-empty plan value as the main plan key for lookup
				if resolvedPlan == "" {
					resolvedPlan = finalVal
				}
			} else if btKey == "deductible" {
				if resolvedDeductible == "" {
					resolvedDeductible = finalVal
				}
			}
		}
	}

	// Load product config to get plan details
	configName := "health_and_accident_insurance.json"
	cachePath := "../outputs/assignment_cache.json"
	if cacheFile, err := os.Open(cachePath); err == nil {
		defer cacheFile.Close()
		var globalCache map[string]interface{}
		if err := json.NewDecoder(cacheFile).Decode(&globalCache); err == nil {
			if entryCache, ok := globalCache[entry.PdfId].(map[string]interface{}); ok {
				if pc, ok := entryCache["product_config"].(string); ok && pc != "" {
					configName = pc
				}
			}
		}
	}

	configPath := "../config/" + configName
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		// Fallback to example if direct file is missing
		configPath = "../config/health_and_accident_insurance.example.json"
	}

	var planLabel, coverage, roomLimit string
	if configFile, err := os.Open(configPath); err == nil {
		defer configFile.Close()
		var fullConfig struct {
			Plans []struct {
				Key       string `json:"key"`
				Label     string `json:"label"`
				Coverage  string `json:"coverage"`
				RoomLimit string `json:"room_limit"`
			} `json:"plans"`
		}
		if err := json.NewDecoder(configFile).Decode(&fullConfig); err == nil {
			for _, p := range fullConfig.Plans {
				if p.Key == resolvedPlan {
					planLabel = p.Label
					coverage = p.Coverage
					roomLimit = p.RoomLimit
					break
				}
			}
		}
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"customerName": entry.CustomerName,
		"planDetails": map[string]string{
			"label":      planLabel,
			"coverage":   coverage,
			"roomLimit":  roomLimit,
			"deductible": resolvedDeductible,
		},
	})
}

func (h *HandlerContext) VaultVerifyHandler(c echo.Context) error {
	token := c.QueryParam("token")
	if token == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "token is required"})
	}

	entry := GlobalVault.GetEntry(token)
	if entry == nil {
		return c.JSON(http.StatusNotFound, map[string]string{"error": "Vault session expired or invalid"})
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"status":       entry.Status,
		"customerName": entry.CustomerName,
	})
}

func (h *HandlerContext) VaultStatusHandler(c echo.Context) error {
	token := c.QueryParam("token")
	if token == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "token is required"})
	}

	entry := GlobalVault.GetEntry(token)
	if entry == nil {
		return c.JSON(http.StatusNotFound, map[string]string{"error": "Vault session expired or invalid"})
	}

	elapsed := time.Since(entry.CreatedAt)
	remaining := int(float64(entry.TTLSeconds) - elapsed.Seconds())
	if remaining < 0 {
		remaining = 0
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"status":            entry.Status,
		"customerName":      entry.CustomerName,
		"remaining_seconds": remaining,
	})
}

func (h *HandlerContext) VaultSignHandler(c echo.Context) error {
	var req struct {
		Token                string `json:"token"`
		IdentityID           string `json:"identityId"`
		SignatureImageBase64 string `json:"signatureImageBase64"`
	}

	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid JSON body"})
	}

	entry := GlobalVault.GetEntry(req.Token)
	if entry == nil {
		return c.JSON(http.StatusNotFound, map[string]string{"error": "Vault session expired or invalid"})
	}

	if entry.Status != "pending" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "Document has already been signed or session state is invalid"})
	}

	if NormalizeID(req.IdentityID) != NormalizeID(entry.IdentityID) {
		return c.JSON(http.StatusForbidden, map[string]string{"error": "Identity verification failed"})
	}

	parts := strings.Split(req.SignatureImageBase64, ",")
	imageBase64 := parts[len(parts)-1]
	sigBytes, err := base64.StdEncoding.DecodeString(imageBase64)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid signature image data"})
	}

	docxBytes, err := os.ReadFile(h.TemplateDocxPath)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to read template DOCX"})
	}

	var fieldMappings map[string]interface{}
	_ = json.Unmarshal([]byte(entry.CacheMappingJSON), &fieldMappings)

	btData := make(map[string]string)
	for pdfField, mapping := range fieldMappings {
		var btKey string
		var choicesMap map[string]interface{}
		if mStr, ok := mapping.(string); ok {
			btKey = mStr
		} else if mObj, ok := mapping.(map[string]interface{}); ok {
			if bk, ok := mObj["bt_key"].(string); ok {
				btKey = bk
			}
			if cm, ok := mObj["choices_map"].(map[string]interface{}); ok {
				choicesMap = cm
			}
		}

		if btKey != "" && btKey != "SKIPPED" {
			val := entry.FormData[pdfField]
			if val != "" {
				finalVal := val
				if choicesMap != nil && strings.HasPrefix(val, "/") {
					if resolvedVal, ok := choicesMap[val].(string); ok {
						finalVal = resolvedVal
					}
				}

				if btKey == "plan" && strings.Contains(finalVal, " DD ") {
					finalVal = strings.TrimSpace(strings.Split(finalVal, " DD ")[0])
				}

				currentVal := btData[btKey]
				newVal := finalVal
				if currentVal != "" {
					newVal = currentVal + "-" + finalVal
				}
				btData[btKey] = newVal
			}
		}
	}

	prefilledPdfResp, err := h.DocClient.Client.GeneratePdf(context.Background(), &document.GeneratePdfRequest{
		PdfBytes: entry.PdfBytes,
		FormData: entry.FormData,
	})
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to prefill PDF: " + err.Error()})
	}

	stampedResp, err := h.DocClient.Client.StampSignature(context.Background(), &document.StampSignatureRequest{
		PdfBytes:            prefilledPdfResp.PdfBytes,
		SignatureImageBytes: sigBytes,
		PdfId:               entry.PdfId,
		RegistryJson:        entry.RegistryJSON,
		CacheMappingJson:    entry.CacheMappingJSON,
	})
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to stamp signature: " + err.Error()})
	}

	docxResp, err := h.DocClient.Client.GenerateDocx(context.Background(), &document.GenerateDocxRequest{
		DocxBytes: docxBytes,
		FormData:  btData,
	})
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to generate DOCX: " + err.Error()})
	}

	entry.SignedPdfBytes = stampedResp.PdfBytes
	entry.SignedDocxBytes = docxResp.DocxBytes
	entry.Status = "signed"
	entry.IdentityID = "" // Discard raw national ID for compliance

	return c.JSON(http.StatusOK, map[string]bool{"success": true})
}

func (h *HandlerContext) VaultDownloadHandler(c echo.Context) error {
	token := c.Param("token")
	docType := c.Param("type")

	if token == "" || docType == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "token and type are required"})
	}

	entry := GlobalVault.GetEntry(token)
	if entry == nil {
		return c.JSON(http.StatusNotFound, map[string]string{"error": "Vault session expired or invalid"})
	}

	if entry.Status != "signed" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "Document is not signed yet"})
	}

	if docType == "pdf" {
		if len(entry.SignedPdfBytes) == 0 {
			return c.JSON(http.StatusInternalServerError, map[string]string{"error": "Signed PDF not found"})
		}
		c.Response().Header().Set("Content-Disposition", "attachment; filename=application_signed.pdf")
		return c.Blob(http.StatusOK, "application/pdf", entry.SignedPdfBytes)
	} else if docType == "docx" {
		if len(entry.SignedDocxBytes) == 0 {
			return c.JSON(http.StatusInternalServerError, map[string]string{"error": "Signed DOCX not found"})
		}
		c.Response().Header().Set("Content-Disposition", "attachment; filename=bluetable_signed.docx")
		return c.Blob(http.StatusOK, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", entry.SignedDocxBytes)
	}

	return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid doc type"})
}

func (h *HandlerContext) VaultClearHandler(c echo.Context) error {
	var req struct {
		Token string `json:"token"`
	}
	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid JSON body"})
	}

	GlobalVault.RemoveEntry(req.Token)
	return c.JSON(http.StatusOK, map[string]bool{"success": true})
}

func (h *HandlerContext) RegistryHandler(c echo.Context) error {
	registryPath := "../outputs/pdf_registry.json"
	data, err := os.ReadFile(registryPath)
	if err != nil {
		return c.JSON(http.StatusOK, map[string]interface{}{})
	}
	
	var registry interface{}
	if err := json.Unmarshal(data, &registry); err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to parse registry file: " + err.Error()})
	}

	return c.JSON(http.StatusOK, registry)
}

func (h *HandlerContext) SaveConfigHandler(c echo.Context) error {
	var req struct {
		PdfId      string      `json:"pdf_id"`
		Filename   string      `json:"filename"`
		ConfigBody interface{} `json:"config_body"`
	}

	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid JSON body"})
	}

	if req.PdfId == "" || req.Filename == "" || req.ConfigBody == nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "pdf_id, filename, and config_body are required"})
	}

	req.Filename = strings.ReplaceAll(req.Filename, "..", "")
	req.Filename = strings.ReplaceAll(req.Filename, "/", "")
	req.Filename = strings.ReplaceAll(req.Filename, "\\", "")

	configDir := "../config"
	if err := os.MkdirAll(configDir, 0755); err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to create config directory"})
	}

	configPath := configDir + "/" + req.Filename
	configData, err := json.MarshalIndent(req.ConfigBody, "", "    ")
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to serialize config"})
	}

	if err := os.WriteFile(configPath, configData, 0644); err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to write config file"})
	}

	cachePath := "../outputs/assignment_cache.json"
	globalCache := make(map[string]interface{})
	if cacheData, err := os.ReadFile(cachePath); err == nil {
		_ = json.Unmarshal(cacheData, &globalCache)
	}

	var entryMap map[string]interface{}
	if entry, ok := globalCache[req.PdfId]; ok {
		if em, ok := entry.(map[string]interface{}); ok {
			entryMap = em
		}
	}

	if entryMap == nil {
		entryMap = make(map[string]interface{})
		entryMap["field_mappings"] = make(map[string]interface{})
	}

	entryMap["product_config"] = req.Filename
	globalCache[req.PdfId] = entryMap

	newCacheData, err := json.MarshalIndent(globalCache, "", "    ")
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to serialize assignment cache"})
	}

	if err := os.WriteFile(cachePath, newCacheData, 0644); err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to update assignment cache"})
	}

	return c.JSON(http.StatusOK, map[string]string{"status": "success"})
}

func (h *HandlerContext) ConfigOptionsHandler(c echo.Context) error {
	configName := "health_and_accident_insurance.json"
	configPath := "../config/" + configName

	// Fallback to example file if the direct config is missing
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		configPath = "../config/health_and_accident_insurance.example.json"
	}

	configFile, err := os.Open(configPath)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to open config file: " + err.Error()})
	}
	defer configFile.Close()

	var fullConfig map[string]interface{}
	if err := json.NewDecoder(configFile).Decode(&fullConfig); err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to decode config file: " + err.Error()})
	}

	return c.JSON(http.StatusOK, fullConfig)
}
