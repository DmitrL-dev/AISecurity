package tools

import (
	"context"
	"fmt"
	"strings"

	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

type ProjectStore interface {
	Ensure(ctx context.Context, sc rlmscope.Scope, name string) (*rlmscope.Project, error)
	Create(ctx context.Context, projectID, name string) (*rlmscope.Project, error)
	Get(ctx context.Context, projectID string) (*rlmscope.Project, error)
	List(ctx context.Context, includeArchived bool) ([]*rlmscope.Project, error)
	Archive(ctx context.Context, projectID string) (*rlmscope.Project, error)
	Activate(ctx context.Context, projectID string) (*rlmscope.Project, error)
	Stats(ctx context.Context, projectID string) (*rlmscope.ProjectStats, error)
}

type ProjectService struct {
	store ProjectStore
}

func NewProjectService(store ProjectStore) *ProjectService {
	return &ProjectService{store: store}
}

type CreateProjectParams struct {
	ProjectID string `json:"project_id"`
	Name      string `json:"name,omitempty"`
}

func (s *ProjectService) EnsureCurrent(ctx context.Context) (*rlmscope.Project, error) {
	if s == nil || s.store == nil {
		return nil, fmt.Errorf("project service not configured")
	}
	sc := rlmscope.FromContext(ctx)
	return s.store.Ensure(ctx, sc, sc.ProjectID)
}

func (s *ProjectService) Current(ctx context.Context) (*rlmscope.ProjectStats, error) {
	if _, err := s.EnsureCurrent(ctx); err != nil {
		return nil, err
	}
	sc := rlmscope.FromContext(ctx)
	return s.store.Stats(ctx, sc.ProjectID)
}

func (s *ProjectService) Create(ctx context.Context, params CreateProjectParams) (*rlmscope.Project, error) {
	if s == nil || s.store == nil {
		return nil, fmt.Errorf("project service not configured")
	}
	projectID := strings.TrimSpace(params.ProjectID)
	if err := validateProjectID(projectID); err != nil {
		return nil, err
	}
	return s.store.Create(ctx, projectID, strings.TrimSpace(params.Name))
}

func (s *ProjectService) List(ctx context.Context, includeArchived bool) ([]*rlmscope.Project, error) {
	if s == nil || s.store == nil {
		return nil, fmt.Errorf("project service not configured")
	}
	if _, err := s.EnsureCurrent(ctx); err != nil {
		return nil, err
	}
	return s.store.List(ctx, includeArchived)
}

func (s *ProjectService) Archive(ctx context.Context, projectID string) (*rlmscope.Project, error) {
	if s == nil || s.store == nil {
		return nil, fmt.Errorf("project service not configured")
	}
	projectID = strings.TrimSpace(projectID)
	if err := validateProjectID(projectID); err != nil {
		return nil, err
	}
	return s.store.Archive(ctx, projectID)
}

func (s *ProjectService) Activate(ctx context.Context, projectID string) (*rlmscope.Project, error) {
	if s == nil || s.store == nil {
		return nil, fmt.Errorf("project service not configured")
	}
	projectID = strings.TrimSpace(projectID)
	if err := validateProjectID(projectID); err != nil {
		return nil, err
	}
	return s.store.Activate(ctx, projectID)
}

func (s *ProjectService) Stats(ctx context.Context, projectID string) (*rlmscope.ProjectStats, error) {
	if s == nil || s.store == nil {
		return nil, fmt.Errorf("project service not configured")
	}
	projectID = strings.TrimSpace(projectID)
	if projectID != "" {
		if err := validateProjectID(projectID); err != nil {
			return nil, err
		}
	}
	if projectID == "" {
		if _, err := s.EnsureCurrent(ctx); err != nil {
			return nil, err
		}
	}
	return s.store.Stats(ctx, projectID)
}

func validateProjectID(projectID string) error {
	return rlmscope.ValidateID("project_id", projectID)
}
