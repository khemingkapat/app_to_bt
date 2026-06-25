package client

import (
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
	"google.golang.org/grpc/connectivity"
)

func TestNewDocumentClient_DefaultAddr(t *testing.T) {
	os.Unsetenv("WORKER_GRPC_ADDR")
	client, err := NewDocumentClient()
	assert.NoError(t, err)
	assert.NotNil(t, client)
	defer client.Close()

	assert.Equal(t, "localhost:50051", client.Conn.Target())
}

func TestNewDocumentClient_CustomAddr(t *testing.T) {
	os.Setenv("WORKER_GRPC_ADDR", "another-host:1234")
	defer os.Unsetenv("WORKER_GRPC_ADDR")

	client, err := NewDocumentClient()
	assert.NoError(t, err)
	assert.NotNil(t, client)
	defer client.Close()

	assert.Equal(t, "another-host:1234", client.Conn.Target())
}

func TestDocumentClient_GetConnectivityState(t *testing.T) {
	client, err := NewDocumentClient()
	assert.NoError(t, err)
	defer client.Close()

	state := client.GetConnectivityState()
	assert.NotEmpty(t, state)
	// Initial state should be IDLE
	assert.Equal(t, connectivity.Idle.String(), state)
}

func TestDocumentClient_IsHealthy(t *testing.T) {
	client, err := NewDocumentClient()
	assert.NoError(t, err)
	defer client.Close()

	// Initially it might be IDLE or CONNECTING, but for gRPC NewClient it starts as IDLE
	assert.True(t, client.IsHealthy(), "Initially client should be in IDLE state which we consider healthy")
}
