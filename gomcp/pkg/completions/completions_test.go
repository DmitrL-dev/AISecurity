package completions

import (
	"context"
	"testing"
)

func TestManager_Complete(t *testing.T) {
	m := NewManager()

	m.RegisterProvider(RefTypePrompt, "test", NewStaticProvider([]string{"foo", "bar", "baz"}))

	resp, err := m.Complete(context.Background(), &Request{
		Ref:      CompletionRef{Type: RefTypePrompt, Name: "test"},
		Argument: CompletionArg{Name: "arg", Value: "b"},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(resp.Completion.Values) != 2 {
		t.Errorf("expected 2 values, got %d", len(resp.Completion.Values))
	}
}

func TestManager_Complete_NilRequest(t *testing.T) {
	m := NewManager()

	_, err := m.Complete(context.Background(), nil)
	if err != ErrNilRequest {
		t.Errorf("expected ErrNilRequest, got %v", err)
	}
}

func TestManager_Complete_NoProvider(t *testing.T) {
	m := NewManager()

	resp, err := m.Complete(context.Background(), &Request{
		Ref:      CompletionRef{Type: RefTypeResource, URI: "test"},
		Argument: CompletionArg{Name: "arg", Value: "x"},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(resp.Completion.Values) != 0 {
		t.Error("expected empty completion")
	}
}

func TestStaticProvider(t *testing.T) {
	p := NewStaticProvider([]string{"alpha", "beta", "gamma"})

	resp, err := p.Complete(context.Background(), &Request{
		Argument: CompletionArg{Value: "a"},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(resp.Completion.Values) != 1 {
		t.Errorf("expected 1 match, got %d", len(resp.Completion.Values))
	}

	if resp.Completion.Values[0] != "alpha" {
		t.Error("expected alpha")
	}
}

func TestStaticProvider_Supports(t *testing.T) {
	p := NewStaticProvider([]string{})

	if !p.Supports(CompletionRef{}) {
		t.Error("should support any ref")
	}
}

func TestPrefixProvider(t *testing.T) {
	values := []string{"one", "two", "three"}
	p := NewPrefixProvider(func() []string { return values })

	resp, err := p.Complete(context.Background(), &Request{
		Argument: CompletionArg{Value: "t"},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(resp.Completion.Values) != 2 {
		t.Errorf("expected 2 matches, got %d", len(resp.Completion.Values))
	}
}

func TestPrefixProvider_Supports(t *testing.T) {
	p := NewPrefixProvider(func() []string { return nil })

	if !p.Supports(CompletionRef{}) {
		t.Error("should support any ref")
	}
}

func TestProviderFunc(t *testing.T) {
	pf := ProviderFunc(func(ctx context.Context, req *Request) (*Response, error) {
		return &Response{
			Completion: Completion{Values: []string{"test"}},
		}, nil
	})

	resp, err := pf.Complete(context.Background(), &Request{})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(resp.Completion.Values) != 1 {
		t.Error("expected 1 value")
	}

	if !pf.Supports(CompletionRef{}) {
		t.Error("should support any ref")
	}
}

func TestResponse_ToJSON(t *testing.T) {
	resp := &Response{
		Completion: Completion{
			Values:  []string{"a", "b"},
			Total:   2,
			HasMore: false,
		},
	}

	data, err := resp.ToJSON()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(data) == 0 {
		t.Error("JSON should not be empty")
	}
}

func TestConstants(t *testing.T) {
	if RefTypePrompt != "ref/prompt" {
		t.Error("invalid ref type")
	}

	if RefTypeResource != "ref/resource" {
		t.Error("invalid ref type")
	}

	if MethodComplete != "completion/complete" {
		t.Error("invalid method")
	}
}

func TestCompletionRef_Fields(t *testing.T) {
	ref := CompletionRef{
		Type: RefTypePrompt,
		Name: "myPrompt",
	}

	if ref.Type != "ref/prompt" {
		t.Error("type mismatch")
	}

	if ref.Name != "myPrompt" {
		t.Error("name mismatch")
	}
}

func TestCompletionArg_Fields(t *testing.T) {
	arg := CompletionArg{
		Name:  "param",
		Value: "val",
	}

	if arg.Name != "param" {
		t.Error("name mismatch")
	}

	if arg.Value != "val" {
		t.Error("value mismatch")
	}
}
