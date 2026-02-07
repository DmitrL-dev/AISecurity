package loader

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

// Adapter implements port.Loader
type Adapter struct {
	client *http.Client
}

func NewAdapter() *Adapter {
	return &Adapter{
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// PayloadManifest matches the JSON structure of web-payloads.json
type PayloadManifest struct {
	Categories map[string][]string `json:"categories"`
	Version    string              `json:"version"`
}

// Load fetches payloads from a URL or File
func (l *Adapter) Load(source string) (map[string][]string, error) {
	var data []byte
	var err error

	if strings.HasPrefix(source, "http") {
		data, err = l.fetchFromURL(source)
	} else {
		data, err = os.ReadFile(source)
	}

	if err != nil {
		return nil, err
	}

	var manifest PayloadManifest
	if err := json.Unmarshal(data, &manifest); err != nil {
		return nil, fmt.Errorf("failed to parse payload manifest: %w", err)
	}

	if len(manifest.Categories) == 0 {
		return nil, fmt.Errorf("no payload categories found in source")
	}

	return manifest.Categories, nil
}

func (l *Adapter) fetchFromURL(url string) ([]byte, error) {
	resp, err := l.client.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("CDN returned status %d", resp.StatusCode)
	}

	return io.ReadAll(resp.Body)
}
