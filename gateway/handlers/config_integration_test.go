package handlers

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestSaveConfigHandler_Success(t *testing.T) {
	// Setup
	e := echo.New()
	h := &HandlerContext{}

	// Ensure directories exist relative to gateway/handlers
	err := os.MkdirAll("../config", 0755)
	require.NoError(t, err)
	err = os.MkdirAll("../outputs", 0755)
	require.NoError(t, err)

	testPdfId := "test-pdf-id-success"
	testFilename := "test-config-success.json"
	testConfigBody := map[string]interface{}{
		"product_options": map[string]interface{}{
			"test_option": "test_value",
		},
	}

	reqBody, err := json.Marshal(map[string]interface{}{
		"pdf_id":      testPdfId,
		"filename":    testFilename,
		"config_body": testConfigBody,
	})
	require.NoError(t, err)

	req := httptest.NewRequest(http.MethodPost, "/api/config", strings.NewReader(string(reqBody)))
	req.Header.Set(echo.HeaderContentType, echo.MIMEApplicationJSON)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	// Execute
	if assert.NoError(t, h.SaveConfigHandler(c)) {
		assert.Equal(t, http.StatusOK, rec.Code)

		// Verify config file
		configPath := filepath.Join("../config", testFilename)
		assert.FileExists(t, configPath)
		defer os.Remove(configPath)

		configData, err := os.ReadFile(configPath)
		assert.NoError(t, err)
		var savedConfig map[string]interface{}
		err = json.Unmarshal(configData, &savedConfig)
		assert.NoError(t, err)

		po, ok := savedConfig["product_options"].(map[string]interface{})
		assert.True(t, ok)
		assert.Equal(t, "test_value", po["test_option"])

		// Verify assignment_cache.json
		cachePath := "../outputs/assignment_cache.json"
		assert.FileExists(t, cachePath)
		// No defer remove for cachePath as it might contain other data,
		// but for integration test isolation we should ideally manage it.
		// For now, let's just make sure we can read it.

		cacheData, err := os.ReadFile(cachePath)
		assert.NoError(t, err)
		var globalCache map[string]interface{}
		err = json.Unmarshal(cacheData, &globalCache)
		assert.NoError(t, err)

		entry, ok := globalCache[testPdfId].(map[string]interface{})
		assert.True(t, ok)
		assert.Equal(t, testFilename, entry["product_config"])

		// Cleanup: remove the specific test entry from cache
		delete(globalCache, testPdfId)
		newCacheData, _ := json.MarshalIndent(globalCache, "", "    ")
		os.WriteFile(cachePath, newCacheData, 0644)
	}
}

func TestSaveConfigHandler_PathTraversal(t *testing.T) {
	// Setup
	e := echo.New()
	h := &HandlerContext{}

	testPdfId := "test-pdf-id-traversal"
	// Malicious filename
	testFilename := "../../dangerous.json"
	testConfigBody := map[string]interface{}{"danger": "zone"}

	reqBody, err := json.Marshal(map[string]interface{}{
		"pdf_id":      testPdfId,
		"filename":    testFilename,
		"config_body": testConfigBody,
	})
	require.NoError(t, err)

	req := httptest.NewRequest(http.MethodPost, "/api/config", strings.NewReader(string(reqBody)))
	req.Header.Set(echo.HeaderContentType, echo.MIMEApplicationJSON)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	// Execute
	if assert.NoError(t, h.SaveConfigHandler(c)) {
		assert.Equal(t, http.StatusOK, rec.Code)

		// The filename should be sanitized: "../../dangerous.json" -> "dangerous.json"
		sanitizedFilename := "dangerous.json"
		configPath := filepath.Join("../config", sanitizedFilename)
		assert.FileExists(t, configPath)
		defer os.Remove(configPath)

		// Ensure it didn't write to root or elsewhere (relative to gateway/handlers)
		// Root is ../..
		assert.NoFileExists(t, "../../dangerous.json")

		// Cleanup cache
		cachePath := "../outputs/assignment_cache.json"
		if cacheData, err := os.ReadFile(cachePath); err == nil {
			var globalCache map[string]interface{}
			if err := json.Unmarshal(cacheData, &globalCache); err == nil {
				delete(globalCache, testPdfId)
				newCacheData, _ := json.MarshalIndent(globalCache, "", "    ")
				os.WriteFile(cachePath, newCacheData, 0644)
			}
		}
	}
}

func TestConfigOptionsHandler(t *testing.T) {
	// Setup
	e := echo.New()
	h := &HandlerContext{}

	// Ensure default config exists for test
	configDir := "../config"
	err := os.MkdirAll(configDir, 0755)
	require.NoError(t, err)
	defaultConfigPath := filepath.Join(configDir, "health_and_accident_insurance.json")

	// Create a dummy config if it doesn't exist
	if _, err := os.Stat(defaultConfigPath); os.IsNotExist(err) {
		dummyContent := `{"product_options": {"dummy": true}}`
		err = os.WriteFile(defaultConfigPath, []byte(dummyContent), 0644)
		require.NoError(t, err)
		defer os.Remove(defaultConfigPath)
	}

	req := httptest.NewRequest(http.MethodGet, "/api/config-options", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	// Execute
	if assert.NoError(t, h.ConfigOptionsHandler(c)) {
		assert.Equal(t, http.StatusOK, rec.Code)
		var resp map[string]interface{}
		err := json.Unmarshal(rec.Body.Bytes(), &resp)
		assert.NoError(t, err)

		po, ok := resp["product_options"].(map[string]interface{})
		assert.True(t, ok)
		// Depending on if it was existing or we created it, we check at least it exists
		assert.NotNil(t, po)
	}
}
