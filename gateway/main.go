package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"gateway/client"
	"gateway/handlers"
	"gateway/middleware"

	"github.com/labstack/echo/v4"
	echoMiddleware "github.com/labstack/echo/v4/middleware"
)

func main() {
	// Create Echo instance
	e := echo.New()

	// Middleware
	e.Use(middleware.StructuredLogger())
	e.Use(echoMiddleware.Recover())

	// Initialize gRPC client
	docClient, err := client.NewDocumentClient()
	if err != nil {
		e.Logger.Fatalf("Failed to initialize gRPC client: %v", err)
	}
	defer docClient.Close()

	// Initialize handler context
	templatePdfPath := os.Getenv("TEMPLATE_PDF_PATH")
	if templatePdfPath == "" {
		templatePdfPath = "../resources/OriginalApplication.pdf"
	}
	templateDocxPath := os.Getenv("TEMPLATE_DOCX_PATH")
	if templateDocxPath == "" {
		templateDocxPath = "../resources/BlueTable.docx"
	}

	hCtx := &handlers.HandlerContext{
		DocClient:        docClient,
		TemplatePDFPath:  templatePdfPath,
		TemplateDocxPath: templateDocxPath,
	}

	// Static files
	e.Static("/", "public")

	// Health check endpoint
	e.GET("/health", func(c echo.Context) error {
		return c.JSON(http.StatusOK, map[string]interface{}{
			"status":              "ok",
			"worker_connectivity": docClient.GetConnectivityState(),
			"worker_healthy":      docClient.IsHealthy(),
		})
	})

	// API routes
	api := e.Group("/api")
	api.POST("/process-pdf", hCtx.ProcessPdfHandler)
	api.POST("/generate-pdf", hCtx.GeneratePdfHandler)
	api.POST("/generate-docx", hCtx.GenerateDocxHandler)
	api.POST("/stamp-signature", hCtx.StampSignatureHandler)
	api.POST("/vault/create", hCtx.VaultCreateHandler)
	api.GET("/vault/verify", hCtx.VaultVerifyHandler)
	api.POST("/vault/verify-identity", hCtx.VaultVerifyIdentityHandler)
	api.GET("/vault/status", hCtx.VaultStatusHandler)
	api.POST("/vault/sign", hCtx.VaultSignHandler)
	api.GET("/vault/download/:token/:type", hCtx.VaultDownloadHandler)
	api.POST("/vault/clear", hCtx.VaultClearHandler)
	api.GET("/registry", hCtx.RegistryHandler)
	api.POST("/config", hCtx.SaveConfigHandler)
	api.GET("/config-options", hCtx.ConfigOptionsHandler)

	// Get port from environment variable or default to 8080
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	// Start server in a goroutine
	go func() {
		if err := e.Start(":" + port); err != nil && err != http.ErrServerClosed {
			e.Logger.Fatal("shutting down the server")
		}
	}()

	// Wait for interrupt signal to gracefully shutdown the server
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, os.Interrupt, syscall.SIGTERM)
	<-quit
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := e.Shutdown(ctx); err != nil {
		e.Logger.Fatal(err)
	}
	log.Println("Gateway server shut down gracefully")
}
