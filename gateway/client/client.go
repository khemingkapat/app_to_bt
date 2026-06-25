package client

import (
	"os"
	"time"

	"gateway/proto/document"

	"google.golang.org/grpc"
	"google.golang.org/grpc/connectivity"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/keepalive"
)

// DocumentClient is a wrapper around the gRPC DocumentServiceClient
type DocumentClient struct {
	Conn   *grpc.ClientConn
	Client document.DocumentServiceClient
}

// NewDocumentClient initializes a new gRPC client connection to the worker service.
func NewDocumentClient() (*DocumentClient, error) {
	addr := os.Getenv("WORKER_GRPC_ADDR")
	if addr == "" {
		addr = "localhost:50051"
	}

	// Keepalive parameters to maintain a healthy connection
	kp := keepalive.ClientParameters{
		Time:                30 * time.Second, // send pings every 30 seconds if there is no activity
		Timeout:             2 * time.Second,  // wait 2 seconds for ping ack before considering the connection dead
		PermitWithoutStream: false,             // do not send pings without active streams to prevent "too_many_pings"
	}

	// Service config for automatic retries
	// This ensures that if the worker is temporarily unavailable, the client will retry.
	retryConfig := `{
		"methodConfig": [{
			"name": [{"service": "document.DocumentService"}],
			"retryPolicy": {
				"maxAttempts": 5,
				"initialBackoff": "0.1s",
				"maxBackoff": "1s",
				"backoffMultiplier": 2,
				"retryableStatusCodes": ["UNAVAILABLE"]
			}
		}]
	}`

	conn, err := grpc.NewClient(
		addr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithKeepaliveParams(kp),
		grpc.WithDefaultServiceConfig(retryConfig),
	)
	if err != nil {
		return nil, err
	}

	client := document.NewDocumentServiceClient(conn)

	return &DocumentClient{
		Conn:   conn,
		Client: client,
	}, nil
}

// GetConnectivityState returns the current state of the gRPC connection.
func (c *DocumentClient) GetConnectivityState() string {
	state := c.Conn.GetState()
	return state.String()
}

// Close gracefully closes the gRPC connection.
func (c *DocumentClient) Close() error {
	return c.Conn.Close()
}

// IsHealthy returns true if the connection is in a healthy state (Ready or Idle).
func (c *DocumentClient) IsHealthy() bool {
	state := c.Conn.GetState()
	return state == connectivity.Ready || state == connectivity.Idle
}
