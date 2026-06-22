# Stage 1: Builder
FROM golang:1.25-alpine AS builder

WORKDIR /app

# Install dependencies
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Build static binary
RUN CGO_ENABLED=0 GOOS=linux go build -o gateway main.go

# Stage 2: Runner
FROM alpine:latest

WORKDIR /app

# Copy binary from builder
COPY --from=builder /app/gateway .

# Copy public directory for static files
COPY --from=builder /app/public ./public

# Expose port 8080
EXPOSE 8080

# Command to run the gateway
CMD ["./gateway"]
