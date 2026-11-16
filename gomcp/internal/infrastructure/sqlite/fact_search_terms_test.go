package sqlite

import (
	"context"
	"testing"

	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// The six queries below are the ones that were run against live memory on 2026-08-20, on facts this
// agent had just stored. Three of them returned nothing while the answer was present, and the tool
// answered «Nothing is known about this yet» each time. They are kept verbatim as the regression:
//
//	"bash читает файл по смещению"   verbatim phrase          found before the fix
//	"портит хвост"                   verbatim phrase          found before the fix
//	"прогон"                         single word              found before the fix
//	"править прогон"                 both words in one fact   MISSED before the fix
//	"скрипт выполняется править"     all three in one fact    MISSED before the fix
//	"Портит Хвост"                   same phrase, capitals    MISSED before the fix
//
// The last one is the case-folding half: SQLite's LIKE folds ASCII only, so a capitalised Cyrillic
// word never matched its stored lowercase form.
const searchFixture = "Нельзя править shell-скрипт, пока он выполняется: bash читает файл " +
	"по смещению, и вставка выше текущей позиции портит хвост молча. Прогон пришлось снять."

func seedSearchFacts(t *testing.T, repo *FactRepo) {
	t.Helper()
	ctx := context.Background()
	for _, content := range []string{
		searchFixture,
		"Все тяжёлые прогоны идут на VPS, не на ноутбуке: ноутбук перегревается и меняет результат.",
		"Локальный прогон governance не является вердиктом: ни один интерпретатор не гоняет набор целиком.",
		"Совершенно посторонний факт про цвет неба и сроки поставки.",
	} {
		f := memory.NewFact(content, memory.LevelProject, "infrastructure", "gate")
		require.NoError(t, repo.Add(ctx, f))
	}
}

func TestFactRepo_Search_VerbatimPhraseStillWins(t *testing.T) {
	repo := newTestFactRepo(t)
	seedSearchFacts(t, repo)

	got, err := repo.Search(context.Background(), "bash читает файл по смещению", 10)
	require.NoError(t, err)
	require.NotEmpty(t, got, "an exact phrase must still match; that behaviour was never the defect")
	assert.Equal(t, searchFixture, got[0].Content, "the phrase match must rank first")
}

func TestFactRepo_Search_AllTermsMatchWithoutBeingContiguous(t *testing.T) {
	// The defect this rewrite exists for. Both words are in the same fact and were never adjacent.
	repo := newTestFactRepo(t)
	seedSearchFacts(t, repo)

	got, err := repo.Search(context.Background(), "править прогон", 10)
	require.NoError(t, err)
	require.NotEmpty(t, got, "a query whose terms are all present must match")
	assert.Equal(t, searchFixture, got[0].Content)

	got, err = repo.Search(context.Background(), "скрипт выполняется править", 10)
	require.NoError(t, err)
	require.NotEmpty(t, got, "three terms, all present in one fact")
	assert.Equal(t, searchFixture, got[0].Content)
}

func TestFactRepo_Search_FoldsCyrillicCase(t *testing.T) {
	// SQLite's LIKE folds ASCII only, which is why this had to move into Go.
	repo := newTestFactRepo(t)
	seedSearchFacts(t, repo)

	lower, err := repo.Search(context.Background(), "портит хвост", 10)
	require.NoError(t, err)
	upper, err := repo.Search(context.Background(), "Портит Хвост", 10)
	require.NoError(t, err)

	require.NotEmpty(t, upper, "capitalising a Cyrillic query must not empty the result")
	assert.Equal(t, len(lower), len(upper), "case must not change how many facts match")
	assert.Equal(t, lower[0].Content, upper[0].Content)
}

func TestFactRepo_Search_PartialQueryDegradesInsteadOfEmptying(t *testing.T) {
	// A natural question carries words no fact contains. Before the rewrite that emptied the result;
	// now the fact matching the most terms comes back, which is the difference between «I do not know»
	// and «here is the closest thing I hold».
	repo := newTestFactRepo(t)
	seedSearchFacts(t, repo)

	got, err := repo.Search(context.Background(), "можно ли править скрипт пока идёт прогон гейта", 10)
	require.NoError(t, err)
	require.NotEmpty(t, got, "a question with one unknown word must still land on the best fact")
	assert.Equal(t, searchFixture, got[0].Content, "the fact matching the most terms must rank first")
}

func TestFactRepo_Search_RanksAllTermsAboveSomeTerms(t *testing.T) {
	repo := newTestFactRepo(t)
	seedSearchFacts(t, repo)

	// «прогон» alone appears in three facts; adding «выполняется» should lift the one that has both.
	got, err := repo.Search(context.Background(), "прогон выполняется", 10)
	require.NoError(t, err)
	require.NotEmpty(t, got)
	assert.Equal(t, searchFixture, got[0].Content, "the fact with both terms must outrank one-term facts")
	assert.Greater(t, len(got), 1, "the one-term facts must still be returned, ranked lower")
}

func TestFactRepo_Search_ShortAndUnknownQueries(t *testing.T) {
	repo := newTestFactRepo(t)
	seedSearchFacts(t, repo)
	ctx := context.Background()

	// A word no fact contains must return nothing rather than everything: the OR tier ranks by
	// matched terms, and zero matched terms is not a match.
	got, err := repo.Search(ctx, "криптовалюта", 10)
	require.NoError(t, err)
	assert.Empty(t, got, "an unrelated query must not drag facts in on zero term matches")

	// Terms shorter than three characters are dropped, so a query made only of them matches nothing
	// on the term tiers; it may still match as a phrase, which is why the assertion is about the
	// absence of noise rather than a hard empty.
	got, err = repo.Search(ctx, "и в", 10)
	require.NoError(t, err)
	assert.LessOrEqual(t, len(got), 4, "function words must not rank the whole corpus as relevant")

	got, err = repo.Search(ctx, "   ", 10)
	require.NoError(t, err)
	assert.Empty(t, got, "a blank query is not a match-everything wildcard")
}
