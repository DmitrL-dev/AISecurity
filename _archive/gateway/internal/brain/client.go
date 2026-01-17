package brain

import (
	"context"
	"crypto/tls"
	"log"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/credentials/insecure"
	pb "sentinel-gateway/pkg/grpc/sentinel"
)

type Client struct {
	conn   *grpc.ClientConn
	client pb.SentinelBrainClient
}

// NewClient creates a new Brain gRPC client with optional TLS
func NewClient(addr string, tlsConfig *tls.Config) (*Client, error) {
	var opts []grpc.DialOption

	if tlsConfig != nil {
		log.Println("Brain client: TLS enabled")
		opts = append(opts, grpc.WithTransportCredentials(credentials.NewTLS(tlsConfig)))
	} else {
		log.Println("Brain client: TLS disabled (insecure)")
		opts = append(opts, grpc.WithTransportCredentials(insecure.NewCredentials()))
	}

	conn, err := grpc.Dial(addr, opts...)
	if err != nil {
		return nil, err
	}

	return &Client{
		conn:   conn,
		client: pb.NewSentinelBrainClient(conn),
	}, nil
}

func (c *Client) Close() error {
	return c.conn.Close()
}

// Analyze - Ingress: Check user prompt before LLM
func (c *Client) Analyze(ctx context.Context, prompt string, meta map[string]string) (*pb.AnalyzeResponse, error) {
	ctx, cancel := context.WithTimeout(ctx, 120*time.Second)
	defer cancel()

	return c.client.Analyze(ctx, &pb.AnalyzeRequest{
		Prompt:  prompt,
		Context: meta,
	})
}

// AnalyzeOutput - Egress: Check LLM response before user
func (c *Client) AnalyzeOutput(ctx context.Context, response string, originalPrompt string, meta map[string]string) (*pb.AnalyzeOutputResponse, error) {
	ctx, cancel := context.WithTimeout(ctx, 120*time.Second)
	defer cancel()

	return c.client.AnalyzeOutput(ctx, &pb.AnalyzeOutputRequest{
		Response:       response,
		OriginalPrompt: originalPrompt,
		Context:        meta,
	})
}

// AnalyzeStream - Streaming: Real-time token analysis
func (c *Client) AnalyzeStream(ctx context.Context) (pb.SentinelBrain_AnalyzeStreamClient, error) {
	return c.client.AnalyzeStream(ctx)
}

// StreamChunk is a convenience wrapper for creating stream chunks
type StreamChunk = pb.StreamChunk

// StreamResult is a convenience wrapper for stream results
type StreamResult = pb.StreamResult

