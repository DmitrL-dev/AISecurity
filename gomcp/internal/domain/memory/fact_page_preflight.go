package memory

const (
	FactPageMaxSerializedBytes           = 16 * 1024 * 1024
	FactPageFrameRawBytes                = 512 * 1024
	FactPageSnapshotIDBytes              = 32
	FactPageSnapshotTTLSeconds     int64 = 5 * 60
	FactPageMaxActiveSnapshots           = 2
	FactPageMaxManifestBytes       int64 = 8 * 1024 * 1024
	factPageSerializedBudgetFloor        = 512 * 1024
	factPageSerializedFixedReserve       = 64 * 1024
	factPageJSONWorstCaseExpansion       = 6
)

// FactPageSnapshotCapacityError reports bounded process-local manifest
// exhaustion without evicting a live export. No content or identifiers are
// exposed through this typed error.
type FactPageSnapshotCapacityError struct {
	ActiveSnapshots    int
	MaxActiveSnapshots int
	ManifestBytes      int64
	MaxManifestBytes   int64
}

func (e *FactPageSnapshotCapacityError) Error() string {
	return "fact page snapshot capacity exhausted"
}

// FactPageStoredOversizeError carries the metadata-only SQLite measurement
// that stopped an exact fact-page read before any variable-width value was
// materialized. The measurement uses the same closed kinds as bounded search.
type FactPageStoredOversizeError struct {
	Measurement BoundedSearchStoredOversize
}

func (e *FactPageStoredOversizeError) Error() string {
	return "stored fact page data exceeds a hard limit"
}

// FactPageMaxStoredVariableBytes derives the maximum raw SQLite variable-width
// footprint that is safe to materialize before json.Marshal. Go JSON can turn
// one hostile string byte into a six-byte escape. The fixed reserve covers
// field names, booleans, numbers and canonical timestamps; the frame-size floor
// keeps small ordinary facts on the exact serialized-size error path even when
// a caller asks for a tiny max_fact_bytes.
func FactPageMaxStoredVariableBytes(maxSerializedBytes int) (int64, bool) {
	if maxSerializedBytes < 1 || maxSerializedBytes > FactPageMaxSerializedBytes {
		return 0, false
	}
	budget := maxSerializedBytes
	if budget < factPageSerializedBudgetFloor {
		budget = factPageSerializedBudgetFloor
	}
	return int64((budget - factPageSerializedFixedReserve) / factPageJSONWorstCaseExpansion), true
}
