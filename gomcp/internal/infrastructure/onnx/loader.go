//go:build onnx

package onnx

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
)

// ModelPaths holds discovered paths for ONNX model and tokenizer.
type ModelPaths struct {
	ModelPath   string // Path to sentinel_brain.onnx
	VocabPath   string // Path to vocab.txt
	RuntimePath string // Path to onnxruntime shared library
}

// DiscoverModel searches for the ONNX model and runtime in standard locations.
// Search order:
//  1. <rlmDir>/models/ (primary — sidecar delivery)
//  2. Current working directory
//  3. Executable directory
func DiscoverModel(rlmDir string) (*ModelPaths, error) {
	paths := &ModelPaths{}

	// Search for model file.
	modelName := "sentinel_brain.onnx"
	vocabName := "vocab.txt"

	searchDirs := []string{
		filepath.Join(rlmDir, "models"),
		".",
	}

	// Add executable directory.
	if exe, err := os.Executable(); err == nil {
		searchDirs = append(searchDirs, filepath.Dir(exe))
	}

	for _, dir := range searchDirs {
		modelPath := filepath.Join(dir, modelName)
		if fileExists(modelPath) {
			paths.ModelPath = modelPath
			break
		}
	}

	// Search for vocab.
	for _, dir := range searchDirs {
		vocabPath := filepath.Join(dir, vocabName)
		if fileExists(vocabPath) {
			paths.VocabPath = vocabPath
			break
		}
	}

	// Also check model dir for vocab.
	if paths.ModelPath != "" && paths.VocabPath == "" {
		modelDir := filepath.Dir(paths.ModelPath)
		vocabPath := filepath.Join(modelDir, vocabName)
		if fileExists(vocabPath) {
			paths.VocabPath = vocabPath
		}
	}

	// Search for ONNX Runtime shared library.
	runtimeName := runtimeLibName()
	runtimeSearchDirs := append(searchDirs,
		filepath.Join(rlmDir, "lib"),
	)

	for _, dir := range runtimeSearchDirs {
		libPath := filepath.Join(dir, runtimeName)
		if fileExists(libPath) {
			paths.RuntimePath = libPath
			break
		}
	}

	// Validate minimum requirements.
	if paths.ModelPath == "" {
		return paths, fmt.Errorf("model not found: %s (searched: %v)", modelName, searchDirs)
	}
	if paths.VocabPath == "" {
		return paths, fmt.Errorf("vocab not found: %s (searched: %v)", vocabName, searchDirs)
	}

	return paths, nil
}

// runtimeLibName returns the platform-specific ONNX Runtime library name.
func runtimeLibName() string {
	switch runtime.GOOS {
	case "windows":
		return "onnxruntime.dll"
	case "darwin":
		return "libonnxruntime.dylib"
	default:
		return "libonnxruntime.so"
	}
}

func fileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}
