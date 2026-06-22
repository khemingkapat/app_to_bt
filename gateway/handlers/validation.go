package handlers

import (
	"bytes"
	"errors"
	"io"
)

const maxFileSize = 5 * 1024 * 1024 // 5MB

var (
	pdfMagicBytes = []byte("%PDF-")
	pngMagicBytes = []byte("\x89PNG\r\n\x1a\n")
)

// ValidateFileSize checks if the file size is within the allowed limit.
func ValidateFileSize(size int64) error {
	if size > maxFileSize {
		return errors.New("file size exceeds 5MB limit")
	}
	return nil
}

// ValidatePDFMagicBytes checks if the reader starts with the PDF magic bytes.
func ValidatePDFMagicBytes(r io.Reader) error {
	header := make([]byte, len(pdfMagicBytes))
	_, err := io.ReadFull(r, header)
	if err != nil {
		return errors.New("failed to read PDF header")
	}
	if !bytes.Equal(header, pdfMagicBytes) {
		return errors.New("invalid PDF: missing %PDF- header")
	}
	return nil
}

// ValidatePNGMagicBytes checks if the reader starts with the PNG magic bytes.
func ValidatePNGMagicBytes(r io.Reader) error {
	header := make([]byte, len(pngMagicBytes))
	_, err := io.ReadFull(r, header)
	if err != nil {
		return errors.New("failed to read PNG header")
	}
	if !bytes.Equal(header, pngMagicBytes) {
		return errors.New("invalid PNG: missing magic bytes")
	}
	return nil
}
