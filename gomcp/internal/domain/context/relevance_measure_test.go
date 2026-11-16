package context

import (
	"sort"
	"testing"
	"time"

	"github.com/syntrex/gomcp/internal/domain/memory"
)

// How good is retrieval? Until this file there was no answer — the scorer had unit tests for each
// signal and none for the thing the signals exist to produce. «Every component is tested» and «the
// output is any good» are different claims, and only the second one is what a memory product sells.
//
// The measurement below is deliberately small and hand-labelled. A hand-labelled set of 12 facts
// and 4 queries is not a benchmark; it is a floor. It catches the failure that the arithmetic
// predicts, and it puts a number in the gate output that a later change has to keep.

// relevanceCase is one query with the facts a human would expect back.
type relevanceCase struct {
	name     string
	query    string
	relevant map[string]bool // fact IDs a reader would call answers to this query
}

// buildCorpus returns facts spanning levels and ages, the way a real store looks after a few weeks.
//
// The ages matter: everything fresh, and recency stops discriminating; everything old, and it stops
// too. The mix is what exposes an ordering that lets freshness stand in for relevance.
func buildCorpus(now time.Time) []*memory.Fact {
	mk := func(id, content string, level memory.HierLevel, domain string, ageHours float64) *memory.Fact {
		f := memory.NewFact(content, level, domain, "")
		f.ID = id
		f.CreatedAt = now.Add(-time.Duration(ageHours) * time.Hour)
		return f
	}
	return []*memory.Fact{
		// Facts about TLS and certificates.
		mk("tls-1", "The gateway terminates TLS at nginx and redirects plain HTTP with 308.",
			memory.LevelDomain, "network", 200),
		mk("tls-2", "Certificate renewal runs from certbot on the host, not in a container.",
			memory.LevelModule, "network", 400),
		mk("tls-3", "A certificate expiry inside 14 days raises a ticket severity alert.",
			memory.LevelModule, "network", 500),

		// Facts about memory provenance.
		mk("prov-1", "Every stored fact records the origin of its content on a trust axis.",
			memory.LevelDomain, "memory", 30),
		mk("prov-2", "Only content a person asked to remember carries origin user.",
			memory.LevelModule, "memory", 48),

		// Facts about rate limits.
		mk("rate-1", "The free tier allows ten requests a minute and one thousand a day.",
			memory.LevelDomain, "billing", 300),
		mk("rate-2", "Enterprise keys have no daily cap, only a per-minute limit.",
			memory.LevelModule, "billing", 320),

		// Fresh, project-wide, and about none of the above. These are the distractors: highest level
		// score, highest recency score, zero topical overlap with any query below.
		mk("noise-1", "Release decisions are recorded in the release ledger before deployment.",
			memory.LevelProject, "release", 1),
		mk("noise-2", "The build pins its toolchain by checksum.",
			memory.LevelProject, "release", 2),
		mk("noise-3", "Documentation lives under docs and is reviewed with the code.",
			memory.LevelProject, "docs", 3),
		mk("noise-4", "Feature flags default to off in production.",
			memory.LevelProject, "config", 4),
		mk("noise-5", "Every alert names the runbook that resolves it.",
			memory.LevelProject, "ops", 5),
	}
}

func relevanceCases() []relevanceCase {
	return []relevanceCase{
		{"tls", "Why does the gateway redirect http requests, and how is the certificate renewed?",
			map[string]bool{"tls-1": true, "tls-2": true, "tls-3": true}},
		{"provenance", "How does memory record where the content of a fact came from?",
			map[string]bool{"prov-1": true, "prov-2": true}},
		{"limits", "What is the daily request limit on the free tier?",
			map[string]bool{"rate-1": true, "rate-2": true}},
		{"certificate expiry", "certificate expiry alert",
			map[string]bool{"tls-3": true, "tls-2": true, "tls-1": true}},
	}
}

// precisionAtK is the fraction of the first k results a human would call relevant.
func precisionAtK(ranked []*ScoredFact, relevant map[string]bool, k int) float64 {
	if k > len(ranked) {
		k = len(ranked)
	}
	if k == 0 {
		return 0
	}
	hits := 0
	for _, sf := range ranked[:k] {
		if relevant[sf.Fact.ID] {
			hits++
		}
	}
	return float64(hits) / float64(k)
}

// rankByCompositeOnly reproduces the ordering that shipped before relevance became the precondition:
// a single weighted sum, sorted descending. Kept so the measurement reports a before and an after
// rather than an unanchored number.
func rankByCompositeOnly(rs *RelevanceScorer, facts []*memory.Fact, keywords []string) []*ScoredFact {
	var scored []*ScoredFact
	for _, f := range facts {
		s := rs.ScoreFact(f, keywords, 0)
		if s <= 0 {
			continue
		}
		scored = append(scored, NewScoredFact(f, s))
	}
	sort.SliceStable(scored, func(i, j int) bool { return scored[i].Score > scored[j].Score })
	return scored
}

func defaultScorer() *RelevanceScorer {
	// The shipped configuration, not a hand-built one: the measurement is only worth anything if it
	// runs against the weights users actually get.
	return NewRelevanceScorer(DefaultEngineConfig())
}

func TestRetrievalPrecisionAtFive(t *testing.T) {
	now := time.Now().UTC()
	corpus := buildCorpus(now)
	scorer := defaultScorer()

	var beforeTotal, afterTotal float64
	cases := relevanceCases()
	for _, c := range cases {
		keywords := ExtractKeywords(c.query)
		before := precisionAtK(rankByCompositeOnly(scorer, corpus, keywords), c.relevant, 5)
		after := precisionAtK(scorer.RankFacts(corpus, keywords, nil), c.relevant, 5)
		beforeTotal += before
		afterTotal += after
		t.Logf("%-18s p@5 %.2f → %.2f", c.name, before, after)
	}
	before := beforeTotal / float64(len(cases))
	after := afterTotal / float64(len(cases))

	// p@5 is bounded by how many relevant facts exist. Two of these queries have only two answers
	// in the corpus, so their p@5 cannot exceed 0.40 however perfect the ranking is; the mean
	// ceiling across the four is 0.50. Comparing a raw p@5 against an absolute number is therefore
	// a category error — the first version of this test asserted a floor of 0.50 and demanded a
	// flawless ranking without noticing. The measured value was 0.450, which is 90% of what is
	// achievable, and it failed.
	ceiling := 0.0
	for _, c := range cases {
		k := 5
		if len(c.relevant) < k {
			k = len(c.relevant)
		}
		ceiling += float64(k) / 5.0
	}
	ceiling /= float64(len(cases))

	t.Logf("mean p@5 over %d queries: %.3f → %.3f (ceiling %.3f)", len(cases), before, after, ceiling)
	t.Logf("share of achievable precision: %.0f%% → %.0f%%", 100*before/ceiling, 100*after/ceiling)

	if after < before {
		t.Errorf("ranking got worse: mean p@5 %.3f → %.3f", before, after)
	}
	// A floor on the achievable share, and this one IS the measured value: 0.450/0.500 = 90%.
	// Rounded down to 0.85 so that a corpus tweak does not fail the gate for a rounding difference,
	// but a real regression in ordering does.
	const floor = 0.85
	if share := after / ceiling; share < floor {
		t.Errorf("achieved %.0f%% of achievable precision (p@5 %.3f of %.3f), below the floor of %.0f%%",
			100*share, after, ceiling, 100*floor)
	}
}

// The frequency signal was effectively off, and turning it on needs measuring rather than assuming.
//
// Ranking read a per-process counter map created empty at startup, while the durable counter
// `hit_count` was written by TouchFact and read by nobody. So frequency contributed 0 to every fact in
// every freshly started server — which is most of them, since an MCP server restarts constantly. The
// repair reads the column, and that means a weight of 0.15 that used to do nothing now does something.
//
// This measures the worst case for that change: every fact a reader would NOT call an answer carries
// ninety recorded accesses, every genuinely relevant fact carries none. If frequency can buy rank
// against relevance, this is where it shows.
//
// No precision floor is asserted here yet, and that is deliberate — the number is measured on the gate
// before it is pinned, because a floor invented at the keyboard is a guess wearing a threshold's
// clothes. What IS asserted is the structural property the ordering guarantees: history cannot carry a
// topically unrelated fact past a related one, whatever the counts say.
func TestFrequencyDoesNotBuyRankAgainstRelevance(t *testing.T) {
	now := time.Now()
	corpus := buildCorpus(now)
	cases := relevanceCases()
	scorer := defaultScorer()

	// Everything a reader would not call an answer, to any query, gets the history.
	everRelevant := map[string]bool{}
	for _, c := range cases {
		for id := range c.relevant {
			everRelevant[id] = true
		}
	}
	hostile := map[string]int{}
	for _, f := range corpus {
		if !everRelevant[f.ID] {
			hostile[f.ID] = 90
		}
	}

	var withoutHistory, withHostileHistory float64
	for _, c := range cases {
		keywords := ExtractKeywords(c.query)
		clean := precisionAtK(scorer.RankFacts(corpus, keywords, nil), c.relevant, 5)
		loaded := precisionAtK(scorer.RankFacts(corpus, keywords, hostile), c.relevant, 5)
		withoutHistory += clean
		withHostileHistory += loaded
		t.Logf("%-18s p@5 %.2f no history → %.2f with hostile history", c.name, clean, loaded)

		// The structural guarantee: relevance is the precondition, not one signal among four. A fact
		// matching no keyword must not take a top-5 slot from one that matches, however often it was
		// used before.
		ranked := scorer.RankFacts(corpus, keywords, hostile)
		limit := 5
		if len(ranked) < limit {
			limit = len(ranked)
		}
		matchingSeen := 0
		for _, sf := range ranked {
			if scorer.scoreKeywordMatch(sf.Fact, keywords) > 0 {
				matchingSeen++
			}
		}
		for i := 0; i < limit; i++ {
			if scorer.scoreKeywordMatch(ranked[i].Fact, keywords) == 0 && matchingSeen > i {
				t.Errorf("%s: %q matches no keyword yet holds slot %d while %d matching facts exist",
					c.name, ranked[i].Fact.ID, i+1, matchingSeen)
			}
		}
	}
	n := float64(len(cases))
	t.Logf("mean p@5 over %d queries: %.3f no history → %.3f with hostile history",
		len(cases), withoutHistory/n, withHostileHistory/n)
}

func TestAFreshUnrelatedFactDoesNotOutrankAMatchingOne(t *testing.T) {
	// The arithmetic, made concrete. With the shipped weights a brand-new L0 fact matching nothing
	// scores 0.30*0 + 0.25*1.00 + 0.15*0 + 0.30*1.00 = 0.55, and a week-old L2 fact matching every
	// keyword scores 0.30*1.00 + 0.25*0.20 + 0.15*0 + 0.30*0.40 = 0.47. Additive ordering puts the
	// unrelated fact first.
	now := time.Now().UTC()
	scorer := defaultScorer()

	matching := memory.NewFact("Certificate renewal runs from certbot on the host.",
		memory.LevelModule, "network", "")
	matching.ID = "matching"
	matching.CreatedAt = now.Add(-168 * time.Hour)

	unrelated := memory.NewFact("Feature flags default to off in production.",
		memory.LevelProject, "config", "")
	unrelated.ID = "unrelated"
	unrelated.CreatedAt = now

	keywords := ExtractKeywords("certificate renewal certbot")

	// The composite still prefers the distractor — the weights are unchanged, and this records that
	// the defect is in the ordering rather than in any single signal.
	if scorer.ScoreFact(unrelated, keywords, 0) <= scorer.ScoreFact(matching, keywords, 0) {
		t.Log("note: the composite no longer prefers the distractor; the weights must have changed")
	}

	ranked := scorer.RankFacts([]*memory.Fact{unrelated, matching}, keywords, nil)
	if len(ranked) != 2 {
		t.Fatalf("expected both facts ranked, got %d", len(ranked))
	}
	if ranked[0].Fact.ID != "matching" {
		t.Errorf("an unrelated fresh fact outranked a matching one: order %s, %s",
			ranked[0].Fact.ID, ranked[1].Fact.ID)
	}
}

func TestWithoutKeywordsTheCompositeOrderingIsUnchanged(t *testing.T) {
	// Context injected without a query. Every fact is in the no-match group, so the composite decides
	// and L0 invariants keep their place. If this broke, standing project context would silently stop
	// being injected — a loss that produces no error anywhere.
	now := time.Now().UTC()
	corpus := buildCorpus(now)
	scorer := defaultScorer()

	withoutKeywords := scorer.RankFacts(corpus, nil, nil)
	composite := rankByCompositeOnly(scorer, corpus, nil)
	if len(withoutKeywords) != len(composite) {
		t.Fatalf("different number of results: %d vs %d", len(withoutKeywords), len(composite))
	}
	for i := range composite {
		if withoutKeywords[i].Fact.ID != composite[i].Fact.ID {
			t.Fatalf("position %d: %s vs %s — ordering changed with no keywords to order by",
				i, withoutKeywords[i].Fact.ID, composite[i].Fact.ID)
		}
	}
}

func TestEveryMatchingFactPrecedesEveryNonMatchingOne(t *testing.T) {
	// The invariant behind the number: once a fact matches a keyword, no unrelated fact may sit
	// above it, whatever its level or age.
	now := time.Now().UTC()
	corpus := buildCorpus(now)
	scorer := defaultScorer()

	for _, c := range relevanceCases() {
		keywords := ExtractKeywords(c.query)
		ranked := scorer.RankFacts(corpus, keywords, nil)
		seenNonMatch := ""
		for _, sf := range ranked {
			matches := scorer.scoreKeywordMatch(sf.Fact, keywords) > 0
			if !matches && seenNonMatch == "" {
				seenNonMatch = sf.Fact.ID
				continue
			}
			if matches && seenNonMatch != "" {
				t.Errorf("%s: %q matched but ranked below %q which did not",
					c.name, sf.Fact.ID, seenNonMatch)
				break
			}
		}
	}
}

func TestKeywordMatchIsSubstringAndThatIsRecorded(t *testing.T) {
	// Not a fix, a measurement. scoreKeywordMatch uses strings.Contains, so «cert» matches
	// «concert» and «uncertain». On a technical corpus the effect is small and it buys prefix
	// matching for free, but it is a real source of false positives and it should be written down
	// rather than discovered later by someone debugging a ranking.
	scorer := defaultScorer()
	f := memory.NewFact("The team went to a concert.", memory.LevelDomain, "social", "")
	got := scorer.scoreKeywordMatch(f, []string{"cert"})
	if got == 0 {
		t.Log("substring matching has been replaced by token matching; this note is now stale")
		return
	}
	t.Logf("substring matching: keyword %q matches %q with score %.2f", "cert", f.Content, got)
}
