package handlers

import (
	"bytes"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"

	"gateway/client"

	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/assert"
)

func TestGRPCResiliency(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping integration test in short mode")
	}

	// 0. Setup paths
	cwd, _ := os.Getwd()
	// handlers is in gateway/handlers, repo root is ../..
	repoRoot, err := filepath.Abs(filepath.Join(cwd, "../.."))
	assert.NoError(t, err)
	workerDir := filepath.Join(repoRoot, "worker")
	pdfPath := filepath.Join(repoRoot, "resources/OriginalApplication.pdf")

	// Ensure port 50051 is free before starting
	killWorker()

	// 1. Initialize Gateway Handler Context with real gRPC client
	// We set WORKER_GRPC_ADDR to localhost:50051 explicitly
	os.Setenv("WORKER_GRPC_ADDR", "localhost:50051")
	docClient, err := client.NewDocumentClient()
	assert.NoError(t, err)
	defer docClient.Close()

	h := &HandlerContext{
		DocClient:        docClient,
		TemplatePDFPath:  filepath.Join(repoRoot, "resources/OriginalApplication.pdf"),
		TemplateDocxPath: filepath.Join(repoRoot, "resources/BlueTable.docx"),
	}

	e := echo.New()

	// 2. Call /api/process-pdf while worker is offline
	t.Run("Worker Offline", func(t *testing.T) {
		rec := httptest.NewRecorder()
		req := createProcessPdfRequest(t, pdfPath)
		c := e.NewContext(req, rec)

		err := h.ProcessPdfHandler(c)

		// The handler returns c.JSON(http.StatusInternalServerError, ...) if gRPC fails
		if err != nil {
			he, ok := err.(*echo.HTTPError)
			if ok {
				assert.True(t, he.Code >= 500, "expected 5xx error")
			}
		} else {
			assert.True(t, rec.Code >= 500, "expected 5xx status code, got %d", rec.Code)
		}

		// Verify health check reflects offline state
		healthRec := httptest.NewRecorder()
		healthReq := httptest.NewRequest(http.MethodGet, "/health", nil)
		healthC := e.NewContext(healthReq, healthRec)

		healthHandler := func(c echo.Context) error {
			return c.JSON(http.StatusOK, map[string]interface{}{
				"status":              "ok",
				"worker_connectivity": docClient.GetConnectivityState(),
				"worker_healthy":      docClient.IsHealthy(),
			})
		}

		if assert.NoError(t, healthHandler(healthC)) {
			assert.Contains(t, healthRec.Body.String(), `"worker_healthy":false`)
		}
	})

	// 3. Start the worker
	t.Log("Starting Python worker...")
	cmd := exec.Command("uv", "run", "python", "src/server.py")
	cmd.Dir = workerDir
	// Avoid process hanging if it writes too much to stdout/stderr
	cmd.Stdout = nil
	cmd.Stderr = nil
	err = cmd.Start()
	assert.NoError(t, err)

	workerStopped := false
	stopWorker := func() {
		if !workerStopped && cmd.Process != nil {
			t.Log("Stopping Python worker...")
			// Kill the process group to ensure children are also killed
			// On Unix, we can use syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL) if we set Setpgid
			// For simplicity here, just kill the process itself.
			cmd.Process.Kill()
			cmd.Wait()
			workerStopped = true
		}
	}
	defer stopWorker()

	// 4. Wait for worker to be ready and connection to re-establish
	t.Log("Waiting for worker to come online and connection to re-establish...")

	success := false
	// Give it up to 30 seconds as UV might need to sync or Python might start slowly
	for i := 0; i < 30; i++ {
		time.Sleep(1 * time.Second)
		rec := httptest.NewRecorder()
		req := createProcessPdfRequest(t, pdfPath)
		c := e.NewContext(req, rec)

		// We don't want to log errors during retry loop
		if err := h.ProcessPdfHandler(c); err == nil && rec.Code == http.StatusOK {
			success = true
			t.Logf("Success after %d seconds", i+1)
			break
		}
		t.Logf("Attempt %d: worker not ready yet or request failed...", i+1)
	}

	assert.True(t, success, "Gateway failed to recover connection to worker")

	// 5. Verify /health reflects online state
	t.Run("Health Check Online", func(t *testing.T) {
		rec := httptest.NewRecorder()
		req := httptest.NewRequest(http.MethodGet, "/health", nil)
		c := e.NewContext(req, rec)

		healthHandler := func(c echo.Context) error {
			return c.JSON(http.StatusOK, map[string]interface{}{
				"status":              "ok",
				"worker_connectivity": docClient.GetConnectivityState(),
				"worker_healthy":      docClient.IsHealthy(),
			})
		}

		if assert.NoError(t, healthHandler(c)) {
			assert.Equal(t, http.StatusOK, rec.Code)
			assert.Contains(t, rec.Body.String(), `"worker_healthy":true`)
		}
	})
}

func createProcessPdfRequest(t *testing.T, pdfPath string) *http.Request {
	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	part, err := writer.CreateFormFile("pdf", "application.pdf")
	if err != nil {
		t.Fatalf("failed to create form file: %v", err)
	}

	pdfBytes, err := os.ReadFile(pdfPath)
	if err != nil {
		t.Fatalf("failed to read pdf file: %v", err)
	}
	part.Write(pdfBytes)
	writer.Close()

	req := httptest.NewRequest(http.MethodPost, "/api/process-pdf", body)
	req.Header.Set(echo.HeaderContentType, writer.FormDataContentType())
	return req
}

func killWorker() {
	// Kill any process on port 50051
	exec.Command("sh", "-c", "lsof -t -i :50051 | xargs kill -9 2>/dev/null || true").Run()
}
