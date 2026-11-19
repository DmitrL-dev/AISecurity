//go:build onnx

package onnx

import "runtime"

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
