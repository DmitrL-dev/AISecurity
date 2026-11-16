package memory

import (
	"testing"

	"github.com/stretchr/testify/require"
)

func TestFactPageMaxStoredVariableBytesPinsSerializedWork(t *testing.T) {
	_, ok := FactPageMaxStoredVariableBytes(0)
	require.False(t, ok)
	_, ok = FactPageMaxStoredVariableBytes(FactPageMaxSerializedBytes + 1)
	require.False(t, ok)

	minimum, ok := FactPageMaxStoredVariableBytes(1)
	require.True(t, ok)
	require.EqualValues(t, (512*1024-64*1024)/6, minimum)

	hardMaximum, ok := FactPageMaxStoredVariableBytes(FactPageMaxSerializedBytes)
	require.True(t, ok)
	require.EqualValues(t, (FactPageMaxSerializedBytes-64*1024)/6, hardMaximum)
}
