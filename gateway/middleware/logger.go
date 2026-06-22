package middleware

import (
	"context"
	"io"
	"log/slog"
	"os"
	"time"

	"github.com/labstack/echo/v4"
)

// StructuredLogger returns a middleware that logs HTTP requests in a structured JSON format using slog to stdout.
func StructuredLogger() echo.MiddlewareFunc {
	return StructuredLoggerWithWriter(os.Stdout)
}

// StructuredLoggerWithWriter returns a middleware that logs HTTP requests in a structured JSON format using slog to the provided writer.
func StructuredLoggerWithWriter(w io.Writer) echo.MiddlewareFunc {
	logger := slog.New(slog.NewJSONHandler(w, &slog.HandlerOptions{
		ReplaceAttr: func(groups []string, a slog.Attr) slog.Attr {
			if a.Key == slog.TimeKey {
				return slog.Attr{
					Key:   "time",
					Value: slog.StringValue(a.Value.Time().Format(time.RFC3339)),
				}
			}
			return a
		},
	}))

	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			start := time.Now()

			err := next(c)
			if err != nil {
				c.Error(err)
			}

			stop := time.Now()
			req := c.Request()
			res := c.Response()

			payloadHash, _ := c.Get("payload_hash").(string)

			latency := stop.Sub(start)

			level := slog.LevelInfo
			if res.Status >= 500 {
				level = slog.LevelError
			} else if res.Status >= 400 {
				level = slog.LevelWarn
			}

			logger.LogAttrs(context.Background(), level, "http_request",
				slog.String("method", req.Method),
				slog.String("uri", req.RequestURI),
				slog.Int("status", res.Status),
				slog.Int64("latency_ms", latency.Milliseconds()),
				slog.String("ip", c.RealIP()),
				slog.String("payload_hash", payloadHash),
			)

			return err
		}
	}
}
