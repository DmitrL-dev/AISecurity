package email

import (
	"crypto/tls"
	"fmt"
	"net"
	"net/smtp"
	"time"
)

// SendDirectSMTP attempts to send an email directly to an MX server.
// It tries to use STARTTLS if available on ports other than 25.
func SendDirectSMTP(mxHost string, port string, from string, to string, msg []byte) error {
	addr := mxHost + ":" + port

	// Timeout logic
	conn, err := net.DialTimeout("tcp", addr, 5*time.Second)
	if err != nil {
		return err // Likely timeout/blocked
	}

	host, _, _ := net.SplitHostPort(addr)
	c, err := smtp.NewClient(conn, host)
	if err != nil {
		return err
	}
	defer c.Quit()

	// If Port is NOT 25, try STARTTLS
	if port != "25" {
		if ok, _ := c.Extension("STARTTLS"); ok {
			config := &tls.Config{InsecureSkipVerify: true, ServerName: host}
			if err = c.StartTLS(config); err != nil {
				return fmt.Errorf("STARTTLS error: %v", err)
			}
		}
	}

	if err := c.Mail(from); err != nil {
		return err
	}
	if err := c.Rcpt(to); err != nil {
		return err
	}

	w, err := c.Data()
	if err != nil {
		return err
	}

	_, err = w.Write(msg)
	if err != nil {
		return err
	}

	return w.Close()
}
