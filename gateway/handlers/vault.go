package handlers

import (
	"crypto/rand"
	"encoding/hex"
	"regexp"
	"strings"
	"sync"
	"time"
)

type VaultEntry struct {
	Token            string
	PdfId            string
	CustomerName     string
	IdentityID       string // Raw truth ID for gate check
	Status           string // "pending", "signed"
	CreatedAt        time.Time
	TTLSeconds       int
	SignedPdfBytes   []byte
	SignedDocxBytes  []byte
	RegistryJSON     string
	CacheMappingJSON string
	FormData         map[string]string // Rebuild mappings
	PdfBytes         []byte            // Original template PDF bytes
}

type MemoryVault struct {
	mu      sync.RWMutex
	entries map[string]*VaultEntry
}

var GlobalVault = &MemoryVault{
	entries: make(map[string]*VaultEntry),
}

func (v *MemoryVault) PurgeExpired() {
	v.mu.Lock()
	defer v.mu.Unlock()
	now := time.Now()
	for token, entry := range v.entries {
		ttl := time.Duration(entry.TTLSeconds) * time.Second
		if now.Sub(entry.CreatedAt) > ttl {
			delete(v.entries, token)
		}
	}
}

func (v *MemoryVault) AddEntry(entry *VaultEntry) {
	v.mu.Lock()
	defer v.mu.Unlock()
	
	// Purge expired when adding
	now := time.Now()
	for t, e := range v.entries {
		ttl := time.Duration(e.TTLSeconds) * time.Second
		if now.Sub(e.CreatedAt) > ttl {
			delete(v.entries, t)
		}
	}
	
	v.entries[entry.Token] = entry
}

func (v *MemoryVault) GetEntry(token string) *VaultEntry {
	v.mu.Lock()
	defer v.mu.Unlock()
	
	// Purge expired when getting
	now := time.Now()
	for t, entry := range v.entries {
		ttl := time.Duration(entry.TTLSeconds) * time.Second
		if now.Sub(entry.CreatedAt) > ttl {
			delete(v.entries, t)
		}
	}

	return v.entries[token]
}

func (v *MemoryVault) RemoveEntry(token string) {
	v.mu.Lock()
	defer v.mu.Unlock()
	delete(v.entries, token)
}

func GenerateSecureToken() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

func NormalizeID(idVal string) string {
	reg := regexp.MustCompile(`[^a-zA-Z0-9]`)
	cleaned := reg.ReplaceAllString(idVal, "")
	return strings.ToLower(cleaned)
}
