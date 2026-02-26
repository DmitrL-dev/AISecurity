// Package causal defines domain entities for causal reasoning chains.
package causal

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"strings"
	"time"
)

// NodeType classifies causal chain nodes.
type NodeType string

const (
	NodeDecision    NodeType = "decision"
	NodeReason      NodeType = "reason"
	NodeConsequence NodeType = "consequence"
	NodeConstraint  NodeType = "constraint"
	NodeAlternative NodeType = "alternative"
	NodeAssumption  NodeType = "assumption" // DB-compatible
)

// IsValid checks if the node type is known.
func (nt NodeType) IsValid() bool {
	switch nt {
	case NodeDecision, NodeReason, NodeConsequence, NodeConstraint, NodeAlternative, NodeAssumption:
		return true
	}
	return false
}

// EdgeType classifies causal chain edges.
type EdgeType string

const (
	EdgeJustifies  EdgeType = "justifies"
	EdgeCauses     EdgeType = "causes"
	EdgeConstrains EdgeType = "constrains"
)

// IsValid checks if the edge type is known.
func (et EdgeType) IsValid() bool {
	switch et {
	case EdgeJustifies, EdgeCauses, EdgeConstrains:
		return true
	}
	return false
}

// Node represents a single node in a causal chain.
type Node struct {
	ID        string    `json:"id"`
	Type      NodeType  `json:"type"`
	Content   string    `json:"content"`
	CreatedAt time.Time `json:"created_at"`
}

// NewNode creates a new Node with a generated ID and timestamp.
func NewNode(nodeType NodeType, content string) *Node {
	return &Node{
		ID:        generateID(),
		Type:      nodeType,
		Content:   content,
		CreatedAt: time.Now(),
	}
}

// Validate checks required fields.
func (n *Node) Validate() error {
	if n.ID == "" {
		return errors.New("node ID is required")
	}
	if n.Content == "" {
		return errors.New("node content is required")
	}
	if !n.Type.IsValid() {
		return fmt.Errorf("invalid node type: %s", n.Type)
	}
	return nil
}

// Edge represents a directed relationship between two nodes.
type Edge struct {
	ID     string   `json:"id"`
	FromID string   `json:"from_id"`
	ToID   string   `json:"to_id"`
	Type   EdgeType `json:"type"`
}

// NewEdge creates a new Edge with a generated ID.
func NewEdge(fromID, toID string, edgeType EdgeType) *Edge {
	return &Edge{
		ID:     generateID(),
		FromID: fromID,
		ToID:   toID,
		Type:   edgeType,
	}
}

// Validate checks required fields and constraints.
func (e *Edge) Validate() error {
	if e.ID == "" {
		return errors.New("edge ID is required")
	}
	if e.FromID == "" {
		return errors.New("edge from_id is required")
	}
	if e.ToID == "" {
		return errors.New("edge to_id is required")
	}
	if !e.Type.IsValid() {
		return fmt.Errorf("invalid edge type: %s", e.Type)
	}
	if e.FromID == e.ToID {
		return errors.New("self-loop edges are not allowed")
	}
	return nil
}

// Chain represents a complete causal chain for a decision.
type Chain struct {
	Decision     *Node   `json:"decision,omitempty"`
	Reasons      []*Node `json:"reasons,omitempty"`
	Consequences []*Node `json:"consequences,omitempty"`
	Constraints  []*Node `json:"constraints,omitempty"`
	Alternatives []*Node `json:"alternatives,omitempty"`
	TotalNodes   int     `json:"total_nodes"`
}

// ToMermaid renders the chain as a Mermaid diagram.
func (c *Chain) ToMermaid() string {
	var sb strings.Builder
	sb.WriteString("graph TD\n")

	if c.Decision != nil {
		fmt.Fprintf(&sb, "  %s[\"%s\"]\n", c.Decision.ID, c.Decision.Content)

		for _, r := range c.Reasons {
			fmt.Fprintf(&sb, "  %s[\"%s\"] -->|justifies| %s\n", r.ID, r.Content, c.Decision.ID)
		}
		for _, co := range c.Consequences {
			fmt.Fprintf(&sb, "  %s -->|causes| %s[\"%s\"]\n", c.Decision.ID, co.ID, co.Content)
		}
		for _, cn := range c.Constraints {
			fmt.Fprintf(&sb, "  %s[\"%s\"] -->|constrains| %s\n", cn.ID, cn.Content, c.Decision.ID)
		}
		for _, a := range c.Alternatives {
			fmt.Fprintf(&sb, "  %s[\"%s\"] -.->|alternative| %s\n", a.ID, a.Content, c.Decision.ID)
		}
	}

	return sb.String()
}

// CausalStats holds aggregate statistics about the causal store.
type CausalStats struct {
	TotalNodes int              `json:"total_nodes"`
	TotalEdges int              `json:"total_edges"`
	ByType     map[NodeType]int `json:"by_type"`
}

// CausalStore defines the interface for causal chain persistence.
type CausalStore interface {
	AddNode(ctx context.Context, node *Node) error
	AddEdge(ctx context.Context, edge *Edge) error
	GetChain(ctx context.Context, query string, maxDepth int) (*Chain, error)
	Stats(ctx context.Context) (*CausalStats, error)
}

func generateID() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}
