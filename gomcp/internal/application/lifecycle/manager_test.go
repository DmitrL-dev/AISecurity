package lifecycle

import (
	"context"
	"errors"
	"io"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestNewManager_Defaults(t *testing.T) {
	m := NewManager(0)
	require.NotNil(t, m)
	assert.Equal(t, 10*time.Second, m.timeout)
	assert.False(t, m.Done())
}

func TestNewManager_CustomTimeout(t *testing.T) {
	m := NewManager(5 * time.Second)
	assert.Equal(t, 5*time.Second, m.timeout)
}

func TestManager_Shutdown_LIFO(t *testing.T) {
	m := NewManager(5 * time.Second)
	order := []string{}

	m.OnShutdown("first", func(_ context.Context) error {
		order = append(order, "first")
		return nil
	})
	m.OnShutdown("second", func(_ context.Context) error {
		order = append(order, "second")
		return nil
	})
	m.OnShutdown("third", func(_ context.Context) error {
		order = append(order, "third")
		return nil
	})

	err := m.Shutdown()
	require.NoError(t, err)
	assert.Equal(t, []string{"third", "second", "first"}, order)
	assert.True(t, m.Done())
}

func TestManager_Shutdown_Idempotent(t *testing.T) {
	m := NewManager(5 * time.Second)
	count := 0
	m.OnShutdown("counter", func(_ context.Context) error {
		count++
		return nil
	})

	_ = m.Shutdown()
	_ = m.Shutdown()
	_ = m.Shutdown()
	assert.Equal(t, 1, count)
}

func TestManager_Shutdown_ReturnsFirstError(t *testing.T) {
	m := NewManager(5 * time.Second)
	errFirst := errors.New("first error")
	errSecond := errors.New("second error")

	m.OnShutdown("ok", func(_ context.Context) error { return nil })
	m.OnShutdown("fail1", func(_ context.Context) error { return errFirst })
	m.OnShutdown("fail2", func(_ context.Context) error { return errSecond })

	// LIFO: fail2 runs first, then fail1, then ok.
	err := m.Shutdown()
	assert.Equal(t, errSecond, err)
}

func TestManager_Shutdown_ContinuesOnError(t *testing.T) {
	m := NewManager(5 * time.Second)
	reached := false

	m.OnShutdown("will-run", func(_ context.Context) error {
		reached = true
		return nil
	})
	m.OnShutdown("will-fail", func(_ context.Context) error {
		return errors.New("fail")
	})

	_ = m.Shutdown()
	assert.True(t, reached, "hook after error should still run")
}

type mockCloser struct {
	closed bool
}

func (m *mockCloser) Close() error {
	m.closed = true
	return nil
}

func TestManager_OnClose(t *testing.T) {
	m := NewManager(5 * time.Second)
	mc := &mockCloser{}

	m.OnClose("mock-closer", mc)
	_ = m.Shutdown()
	assert.True(t, mc.closed)
}

func TestManager_OnClose_Interface(t *testing.T) {
	m := NewManager(5 * time.Second)
	// Verify OnClose accepts io.Closer interface.
	var c io.Closer = &mockCloser{}
	m.OnClose("io-closer", c)
	err := m.Shutdown()
	require.NoError(t, err)
}

func TestManager_EmptyShutdown(t *testing.T) {
	m := NewManager(5 * time.Second)
	err := m.Shutdown()
	require.NoError(t, err)
	assert.True(t, m.Done())
}
