package middleware

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/assert"
)

func TestStructuredLogger(t *testing.T) {
	// Setup
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)
	c.Set("payload_hash", "abc123hash")

	var buf bytes.Buffer
	mw := StructuredLoggerWithWriter(&buf)
	handler := mw(func(c echo.Context) error {
		return c.String(http.StatusOK, "ok")
	})

	// Execute
	err := handler(c)

	// Assert
	assert.NoError(t, err)
	assert.Equal(t, http.StatusOK, rec.Code)

	// Check log output
	var logEntry map[string]interface{}
	err = json.Unmarshal(buf.Bytes(), &logEntry)
	assert.NoError(t, err)

	assert.Equal(t, "INFO", logEntry["level"])
	assert.Equal(t, "GET", logEntry["method"])
	assert.Equal(t, "/test", logEntry["uri"])
	assert.Equal(t, float64(http.StatusOK), logEntry["status"])
	assert.Equal(t, "abc123hash", logEntry["payload_hash"])
	assert.Contains(t, logEntry, "time")
	assert.Contains(t, logEntry, "latency_ms")
	assert.Contains(t, logEntry, "ip")
}
