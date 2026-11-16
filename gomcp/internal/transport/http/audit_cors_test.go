package httpserver

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestAuditWildcardCORSNeverGrantsCredentials(t *testing.T) {
	request := httptest.NewRequest("OPTIONS", "/api/fixture", nil)
	request.Header.Set("Origin", "https://synthetic.invalid")
	for _, allowed := range [][]string{{"*"}, {"https://synthetic.invalid"}} {
		response := httptest.NewRecorder()
		corsMiddleware(allowed)(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {})).ServeHTTP(response, request)
		if allowed[0] == "*" && response.Header().Get("Access-Control-Allow-Credentials") != "" {
			t.Fatal("wildcard granted credential access")
		}
		if allowed[0] != "*" && response.Header().Get("Access-Control-Allow-Credentials") != "true" {
			t.Fatal("explicit trusted origin lost credentials")
		}
	}
}
