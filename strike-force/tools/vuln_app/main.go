package main

import (
	"fmt"
	"net/http"
)

func main() {
	fmt.Println("[*] Vulnerable App listening on :8081")
	fmt.Println("[*] Simulating: AWS Key Leak, Missing Headers, Exposed PHP Version")

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		// 1. Misconfig: Information Disclosure headers
		w.Header().Set("X-Powered-By", "PHP/5.6.40") // Old PHP
		w.Header().Set("Server", "Apache/2.4.6")

		// 2. Misconfig: Missing Security Headers
		// (We explicitly DO NOT set HSTS, CSP, X-Frame-Options)

		// 3. Secret Leak: Fake AWS Key in HTML comment
		w.WriteHeader(200)
		body := `
			<html>
			<head><title>Vulnerable App</title></head>
			<body>
				<h1>Welcome to the Legacy System</h1>
				<p>TODO: Cleanup these credentials before prod...</p>
				<!-- AWS_ACCESS_KEY_ID = AKIAIOSFODNN7EXAMPLE -->
				<!-- DB_PASSWORD = super_secret_password_123 -->
				<p>Contact admin@corp.local</p>
			</body>
			</html>
		`
		w.Write([]byte(body))
	})

	http.ListenAndServe(":8081", nil)
}
