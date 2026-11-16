package tools

import (
	"context"
	"strings"
	"testing"

	"github.com/stretchr/testify/require"

	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

func TestProjectService_CreateValidatesProjectID(t *testing.T) {
	service := NewProjectService(&projectStoreStub{})

	for _, projectID := range []string{"", "bad/project", "bad project", "bad\nproject", strings.Repeat("a", 129)} {
		t.Run(projectID, func(t *testing.T) {
			_, err := service.Create(context.Background(), CreateProjectParams{ProjectID: projectID})
			require.Error(t, err)
		})
	}
}

func TestProjectService_CreateTrimsAndDelegates(t *testing.T) {
	store := &projectStoreStub{}
	service := NewProjectService(store)

	project, err := service.Create(context.Background(), CreateProjectParams{
		ProjectID: " project-alpha ",
		Name:      " Alpha Project ",
	})
	require.NoError(t, err)
	require.Equal(t, "project-alpha", store.createdProjectID)
	require.Equal(t, "Alpha Project", store.createdName)
	require.Equal(t, "project-alpha", project.ProjectID)
}

type projectStoreStub struct {
	createdProjectID string
	createdName      string
}

func (s *projectStoreStub) Ensure(_ context.Context, sc rlmscope.Scope, name string) (*rlmscope.Project, error) {
	if name == "" {
		name = sc.ProjectID
	}
	return &rlmscope.Project{TenantID: sc.TenantID, ProjectID: sc.ProjectID, Name: name, Status: rlmscope.ProjectStatusActive}, nil
}

func (s *projectStoreStub) Create(_ context.Context, projectID, name string) (*rlmscope.Project, error) {
	s.createdProjectID = projectID
	s.createdName = name
	return &rlmscope.Project{TenantID: rlmscope.DefaultTenantID, ProjectID: projectID, Name: name, Status: rlmscope.ProjectStatusActive}, nil
}

func (s *projectStoreStub) Get(_ context.Context, projectID string) (*rlmscope.Project, error) {
	return &rlmscope.Project{ProjectID: projectID, Status: rlmscope.ProjectStatusActive}, nil
}

func (s *projectStoreStub) List(_ context.Context, _ bool) ([]*rlmscope.Project, error) {
	return []*rlmscope.Project{{ProjectID: s.createdProjectID, Status: rlmscope.ProjectStatusActive}}, nil
}

func (s *projectStoreStub) Archive(_ context.Context, projectID string) (*rlmscope.Project, error) {
	return &rlmscope.Project{ProjectID: projectID, Status: rlmscope.ProjectStatusArchived}, nil
}

func (s *projectStoreStub) Activate(_ context.Context, projectID string) (*rlmscope.Project, error) {
	return &rlmscope.Project{ProjectID: projectID, Status: rlmscope.ProjectStatusActive}, nil
}

func (s *projectStoreStub) Stats(_ context.Context, projectID string) (*rlmscope.ProjectStats, error) {
	return &rlmscope.ProjectStats{
		Project: &rlmscope.Project{ProjectID: projectID, Status: rlmscope.ProjectStatusActive},
	}, nil
}
