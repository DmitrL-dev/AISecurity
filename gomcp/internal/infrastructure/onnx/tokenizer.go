// Package onnx provides a native Go ONNX Runtime embedder for the Sentinel Local Oracle.
//
// Replaces the Python bridge (pybridge) with direct ONNX inference.
// Uses yalue/onnxruntime_go which dynamically loads the ONNX Runtime
// shared library (no CGO required).
//
// Model: paraphrase-multilingual-MiniLM-L12-v2 (ONNX, dim=384)
// Tokenizer: WordPiece (BERT-compatible)
// Fallback: If ONNX Runtime or model not found → returns error,
//
//	caller should fall back to FTS5Embedder.
//go:build onnx

package onnx

import (
	"bufio"
	"fmt"
	"os"
	"strings"
	"unicode"
)

// Tokenizer implements a BERT-compatible WordPiece tokenizer.
// Reads vocabulary from vocab.txt (standard HuggingFace format).
type Tokenizer struct {
	vocab    map[string]int64 // token → ID
	invVocab map[int64]string // ID → token
	maxLen   int              // max sequence length

	// Special token IDs.
	clsID int64
	sepID int64
	padID int64
	unkID int64
}

// TokenizerConfig holds tokenizer settings.
type TokenizerConfig struct {
	VocabPath string // Path to vocab.txt
	MaxLength int    // Max sequence length (default: 128)
}

// NewTokenizer creates a WordPiece tokenizer from a vocabulary file.
func NewTokenizer(cfg TokenizerConfig) (*Tokenizer, error) {
	// MaxLength must leave room for the mandatory [CLS] and [SEP] sentinels
	// (Encode does maxLen-2 and writes inputIDs[seqLen-1]); a value < 2 would
	// produce a negative truncation index / out-of-bounds write and panic.
	if cfg.MaxLength < 2 {
		cfg.MaxLength = 128
	}

	vocab, err := loadVocab(cfg.VocabPath)
	if err != nil {
		return nil, fmt.Errorf("load vocab: %w", err)
	}

	invVocab := make(map[int64]string, len(vocab))
	for k, v := range vocab {
		invVocab[v] = k
	}

	t := &Tokenizer{
		vocab:    vocab,
		invVocab: invVocab,
		maxLen:   cfg.MaxLength,
	}

	// Resolve special tokens.
	t.clsID = t.tokenID("[CLS]")
	t.sepID = t.tokenID("[SEP]")
	t.padID = t.tokenID("[PAD]")
	t.unkID = t.tokenID("[UNK]")

	return t, nil
}

// TokenizedInput holds the encoded input for ONNX inference.
type TokenizedInput struct {
	InputIDs      []int64 // Token IDs
	AttentionMask []int64 // 1 for real tokens, 0 for padding
	TokenTypeIDs  []int64 // Segment IDs (all 0 for single-sentence)
}

// Encode tokenizes text into BERT-format input.
// Adds [CLS] at start, [SEP] at end, pads/truncates to MaxLength.
func (t *Tokenizer) Encode(text string) TokenizedInput {
	// Basic pre-tokenization: lowercase + split on whitespace/punctuation.
	tokens := t.preTokenize(text)

	// WordPiece sub-tokenization.
	var wordPieces []int64
	for _, token := range tokens {
		pieces := t.wordPiece(token)
		wordPieces = append(wordPieces, pieces...)
	}

	// Truncate to fit [CLS] + tokens + [SEP].
	maxTokens := t.maxLen - 2
	if len(wordPieces) > maxTokens {
		wordPieces = wordPieces[:maxTokens]
	}

	// Build final sequence: [CLS] + tokens + [SEP] + [PAD]...
	seqLen := len(wordPieces) + 2
	inputIDs := make([]int64, t.maxLen)
	attentionMask := make([]int64, t.maxLen)
	tokenTypeIDs := make([]int64, t.maxLen)

	inputIDs[0] = t.clsID
	attentionMask[0] = 1
	for i, id := range wordPieces {
		inputIDs[i+1] = id
		attentionMask[i+1] = 1
	}
	inputIDs[seqLen-1] = t.sepID
	attentionMask[seqLen-1] = 1

	// Remaining positions are [PAD] (already zero-initialized).
	for i := seqLen; i < t.maxLen; i++ {
		inputIDs[i] = t.padID
	}

	return TokenizedInput{
		InputIDs:      inputIDs,
		AttentionMask: attentionMask,
		TokenTypeIDs:  tokenTypeIDs,
	}
}

// preTokenize splits text into word-level tokens.
func (t *Tokenizer) preTokenize(text string) []string {
	text = strings.ToLower(strings.TrimSpace(text))
	var tokens []string
	var current strings.Builder

	for _, r := range text {
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			current.WriteRune(r)
		} else if unicode.IsPunct(r) {
			// Flush current word.
			if current.Len() > 0 {
				tokens = append(tokens, current.String())
				current.Reset()
			}
			// Punctuation as separate token.
			tokens = append(tokens, string(r))
		} else if unicode.IsSpace(r) {
			if current.Len() > 0 {
				tokens = append(tokens, current.String())
				current.Reset()
			}
		}
	}
	if current.Len() > 0 {
		tokens = append(tokens, current.String())
	}
	return tokens
}

// wordPiece applies WordPiece sub-word tokenization.
func (t *Tokenizer) wordPiece(token string) []int64 {
	if _, ok := t.vocab[token]; ok {
		return []int64{t.vocab[token]}
	}

	var pieces []int64
	runes := []rune(token)
	start := 0

	for start < len(runes) {
		end := len(runes)
		found := false

		for end > start {
			substr := string(runes[start:end])
			if start > 0 {
				substr = "##" + substr
			}

			if id, ok := t.vocab[substr]; ok {
				pieces = append(pieces, id)
				found = true
				start = end
				break
			}
			end--
		}

		if !found {
			// Unknown character — use [UNK].
			pieces = append(pieces, t.unkID)
			start++
		}
	}

	return pieces
}

func (t *Tokenizer) tokenID(token string) int64 {
	if id, ok := t.vocab[token]; ok {
		return id
	}
	return 0
}

// VocabSize returns the vocabulary size.
func (t *Tokenizer) VocabSize() int {
	return len(t.vocab)
}

// loadVocab reads a HuggingFace vocab.txt (one token per line, ID = line number).
func loadVocab(path string) (map[string]int64, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	vocab := make(map[string]int64)
	scanner := bufio.NewScanner(f)
	var id int64
	for scanner.Scan() {
		token := strings.TrimSpace(scanner.Text())
		if token != "" {
			vocab[token] = id
		}
		id++
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	return vocab, nil
}
