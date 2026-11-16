package tracing

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// --- InitTracer Tests ---

func TestInitTracer_NoopWhenEndpointEmpty(t *testing.T) {
	tp, err := InitTracer(context.Background(), "")
	require.NoError(t, err)
	assert.Nil(t, tp, "empty endpoint should return nil TracerProvider (noop)")
}

func TestShutdown_NilProvider_NoPanic(t *testing.T) {
	// Should not panic when called with nil.
	assert.NotPanics(t, func() {
		Shutdown(context.Background(), nil)
	})
}

func TestTracer_ReturnsNonNil(t *testing.T) {
	tr := Tracer("test-tracer")
	assert.NotNil(t, tr)
}

// --- HTTPMiddleware Tests ---

func TestHTTPMiddleware_SetsStatusCode(t *testing.T) {
	handler := HTTPMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusCreated)
		w.Write([]byte("created"))
	}))

	req := httptest.NewRequest(http.MethodPost, "/api/soc/event", nil)
	rr := httptest.NewRecorder()

	handler.ServeHTTP(rr, req)

	assert.Equal(t, http.StatusCreated, rr.Code)
	assert.Equal(t, "created", rr.Body.String())
}

func TestHTTPMiddleware_Default200(t *testing.T) {
	handler := HTTPMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("ok"))
	}))

	req := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	rr := httptest.NewRecorder()

	handler.ServeHTTP(rr, req)

	assert.Equal(t, http.StatusOK, rr.Code)
}

func TestHTTPMiddleware_ErrorStatus(t *testing.T) {
	handler := HTTPMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))

	req := httptest.NewRequest(http.MethodGet, "/error", nil)
	rr := httptest.NewRecorder()

	handler.ServeHTTP(rr, req)

	assert.Equal(t, http.StatusInternalServerError, rr.Code)
}

// --- statusWriter Tests ---

func TestStatusWriter_DefaultStatus(t *testing.T) {
	rr := httptest.NewRecorder()
	sw := &statusWriter{ResponseWriter: rr, status: http.StatusOK}
	assert.Equal(t, http.StatusOK, sw.status)
	assert.False(t, sw.wroteHeader)
}

func TestStatusWriter_WriteHeaderOnce(t *testing.T) {
	rr := httptest.NewRecorder()
	sw := &statusWriter{ResponseWriter: rr, status: http.StatusOK}

	sw.WriteHeader(http.StatusNotFound)
	assert.Equal(t, http.StatusNotFound, sw.status)
	assert.True(t, sw.wroteHeader)

	// Second call should NOT change status.
	sw.WriteHeader(http.StatusCreated)
	assert.Equal(t, http.StatusNotFound, sw.status, "status should not change on second WriteHeader")
}

func TestStatusWriter_WriteImplicitHeader(t *testing.T) {
	rr := httptest.NewRecorder()
	sw := &statusWriter{ResponseWriter: rr, status: http.StatusOK}

	n, err := sw.Write([]byte("hello"))
	assert.NoError(t, err)
	assert.Equal(t, 5, n)
	assert.True(t, sw.wroteHeader, "Write should set wroteHeader")
}
