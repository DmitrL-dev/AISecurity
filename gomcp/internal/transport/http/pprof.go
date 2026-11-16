package httpserver

import (
	"net/http"
	"net/http/pprof"
)

// EnablePprof activates debug profiling endpoints.
// Should only be enabled in development/staging environments.
func (s *Server) EnablePprof() {
	s.pprofEnabled = true
}

// handlePprof serves the pprof index page.
func (s *Server) handlePprof(w http.ResponseWriter, r *http.Request) {
	pprof.Index(w, r)
}

// handlePprofProfile serves CPU profile data.
func (s *Server) handlePprofProfile(w http.ResponseWriter, r *http.Request) {
	pprof.Profile(w, r)
}

// handlePprofHeap serves heap memory profile data.
func (s *Server) handlePprofHeap(w http.ResponseWriter, r *http.Request) {
	pprof.Handler("heap").ServeHTTP(w, r)
}

// handlePprofGoroutine serves goroutine stack traces.
func (s *Server) handlePprofGoroutine(w http.ResponseWriter, r *http.Request) {
	pprof.Handler("goroutine").ServeHTTP(w, r)
}
