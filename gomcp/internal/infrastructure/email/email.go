// Package email provides email notification service for the SYNTREX SOC platform.
// Supports Resend (resend.com) as the primary transactional email provider.
package email

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"time"
)

// Sender defines the email sending interface.
type Sender interface {
	Send(to, subject, htmlBody string) error
}

// StubSender logs emails instead of sending them (development mode).
type StubSender struct{}

func (s *StubSender) Send(to, subject, htmlBody string) error {
	slog.Info("email: stub send",
		"to", to,
		"subject", subject,
		"body_len", len(htmlBody))
	return nil
}

// ResendSender sends emails via Resend API (https://resend.com).
type ResendSender struct {
	apiKey   string
	fromAddr string
	client   *http.Client
}

// NewResendSender creates a Resend email sender.
// apiKey format: "re_xxxxxxxxx"
// fromAddr example: "SYNTREX <noreply@syntrex.pro>"
func NewResendSender(apiKey, fromAddr string) *ResendSender {
	return &ResendSender{
		apiKey:   apiKey,
		fromAddr: fromAddr,
		client: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

func (s *ResendSender) Send(to, subject, htmlBody string) error {
	payload := map[string]interface{}{
		"from":    s.fromAddr,
		"to":      []string{to},
		"subject": subject,
		"html":    htmlBody,
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("email: marshal payload: %w", err)
	}

	req, err := http.NewRequest("POST", "https://api.resend.com/emails", bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("email: create request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+s.apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := s.client.Do(req)
	if err != nil {
		return fmt.Errorf("email: send request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		respBody, _ := io.ReadAll(resp.Body)
		slog.Error("email: resend API error",
			"status", resp.StatusCode,
			"body", string(respBody),
			"to", to,
			"subject", subject)
		return fmt.Errorf("email: resend API returned %d: %s", resp.StatusCode, string(respBody))
	}

	slog.Info("email: sent via Resend",
		"to", to,
		"subject", subject,
		"status", resp.StatusCode)
	return nil
}

// Template IDs for standard emails.
const (
	TemplateWelcome       = "welcome"
	TemplatePasswordReset = "password_reset"
	TemplateIncidentAlert = "incident_alert"
	TemplatePlanUpgrade   = "plan_upgrade"
	TemplateInvoice       = "invoice"
)

// Service provides email notifications with templates.
type Service struct {
	sender   Sender
	fromName string
	fromAddr string
}

// NewService creates an email service.
// Pass nil sender for stub mode (logs only).
// For Resend: NewService(NewResendSender(apiKey, from), "SYNTREX", "noreply@syntrex.pro")
func NewService(sender Sender, fromName, fromAddr string) *Service {
	if sender == nil {
		sender = &StubSender{}
	}
	if fromName == "" {
		fromName = "SYNTREX"
	}
	if fromAddr == "" {
		fromAddr = "noreply@syntrex.pro"
	}
	return &Service{
		sender:   sender,
		fromName: fromName,
		fromAddr: fromAddr,
	}
}

// SendVerificationCode sends a 6-digit verification code after registration.
// locale: "ru" for Russian, anything else for English.
func (s *Service) SendVerificationCode(toEmail, userName, code string) error {
	return s.SendVerificationCodeLocalized(toEmail, userName, code, "ru")
}

// SendVerificationCodeLocalized sends a localized verification code email.
func (s *Service) SendVerificationCodeLocalized(toEmail, userName, code, locale string) error {
	ru := locale == "ru"
	var subject, greeting, instruction, validity, disclaimer string
	if ru {
		subject = "SYNTREX — Код подтверждения"
		greeting = fmt.Sprintf("Здравствуйте, <strong>%s</strong>!", userName)
		instruction = "Ваш код подтверждения email:"
		validity = "Код действителен <strong>24 часа</strong>."
		disclaimer = "Если вы не регистрировались на SYNTREX — проигнорируйте это письмо."
	} else {
		subject = "SYNTREX — Verification Code"
		greeting = fmt.Sprintf("Hello, <strong>%s</strong>!", userName)
		instruction = "Your email verification code:"
		validity = "This code is valid for <strong>24 hours</strong>."
		disclaimer = "If you did not sign up for SYNTREX, please ignore this email."
	}
	body := fmt.Sprintf(`
<!DOCTYPE html>
<html>
<body style="font-family: 'Inter', Arial, sans-serif; background: #0a0f1e; color: #e1e5ee; padding: 40px; margin: 0;">
<div style="max-width: 600px; margin: 0 auto; background: #111827; border-radius: 12px; padding: 32px; border: 1px solid #1e293b;">
  <h1 style="color: #34d399; margin: 0 0 20px; font-size: 24px;">🛡️ SYNTREX</h1>
  <p style="margin: 0 0 8px;">%s</p>
  <p style="margin: 0 0 24px; color: #9ca3af;">%s</p>
  <div style="background: #0a0f1e; border: 2px solid #34d399; border-radius: 8px; padding: 20px; text-align: center; margin: 0 0 24px;">
    <span style="font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #34d399; font-family: monospace;">%s</span>
  </div>
  <p style="color: #9ca3af; font-size: 13px; margin: 0 0 8px;">%s</p>
  <p style="color: #6b7280; font-size: 12px; margin: 24px 0 0; padding-top: 16px; border-top: 1px solid #1e293b;">
    %s
  </p>
</div>
</body>
</html>`, greeting, instruction, code, validity, disclaimer)

	return s.sender.Send(toEmail, subject, body)
}

// SendWelcome sends a welcome email after registration.
func (s *Service) SendWelcome(toEmail, userName, orgName string) error {
	subject := "Welcome to SYNTREX / Добро пожаловать в SYNTREX"
	body := fmt.Sprintf(`
<!DOCTYPE html>
<html>
<body style="font-family: 'Inter', Arial, sans-serif; background: #0a0f1e; color: #e1e5ee; padding: 40px; margin: 0;">
<div style="max-width: 600px; margin: 0 auto; background: #111827; border-radius: 12px; padding: 32px; border: 1px solid #1e293b;">
  <h1 style="color: #34d399; margin: 0 0 20px;">🛡️ SYNTREX</h1>
  <p>Hello / Здравствуйте, <strong>%s</strong>!</p>
  <p>Your organization <strong>%s</strong> has been registered. / Ваша организация <strong>%s</strong> успешно зарегистрирована.</p>
  <h3 style="color: #818cf8;">Getting Started / Как начать:</h3>
  <ol>
    <li>Open <strong>Quick Start</strong> in the sidebar / Откройте <strong>Quick Start</strong> в боковом меню</li>
    <li>Create an API key in <strong>Settings → API Keys</strong> / Создайте API-ключ</li>
    <li>Send your first security event / Отправьте первое событие</li>
  </ol>
  <p style="color: #9ca3af; font-size: 12px; margin-top: 30px;">
    This is an automated email from SYNTREX. If you did not register, please ignore it.
  </p>
</div>
</body>
</html>`, userName, orgName, orgName)

	return s.sender.Send(toEmail, subject, body)
}

// SendIncidentAlert sends an alert when a critical incident is created.
func (s *Service) SendIncidentAlert(toEmail, incidentID, title, severity string) error {
	subject := fmt.Sprintf("[SYNTREX] Инцидент %s: %s", severity, title)
	body := fmt.Sprintf(`
<!DOCTYPE html>
<html>
<body style="font-family: 'Inter', Arial, sans-serif; background: #0a0f1e; color: #e1e5ee; padding: 40px; margin: 0;">
<div style="max-width: 600px; margin: 0 auto; background: #111827; border-radius: 12px; padding: 32px; border: 1px solid #dc2626;">
  <h1 style="color: #ef4444; margin: 0 0 20px;">🚨 Инцидент безопасности</h1>
  <table style="width: 100%%; border-collapse: collapse;">
    <tr><td style="color: #9ca3af; padding: 8px 0;">ID:</td><td><strong>%s</strong></td></tr>
    <tr><td style="color: #9ca3af; padding: 8px 0;">Название:</td><td><strong>%s</strong></td></tr>
    <tr><td style="color: #9ca3af; padding: 8px 0;">Критичность:</td><td style="color: #ef4444;"><strong>%s</strong></td></tr>
  </table>
</div>
</body>
</html>`, incidentID, title, severity)

	return s.sender.Send(toEmail, subject, body)
}

// SendPasswordReset sends a password reset link.
func (s *Service) SendPasswordReset(toEmail, resetToken string) error {
	subject := "SYNTREX — Сброс пароля"
	body := fmt.Sprintf(`
<!DOCTYPE html>
<html>
<body style="font-family: 'Inter', Arial, sans-serif; background: #0a0f1e; color: #e1e5ee; padding: 40px; margin: 0;">
<div style="max-width: 600px; margin: 0 auto; background: #111827; border-radius: 12px; padding: 32px; border: 1px solid #1e293b;">
  <h1 style="color: #60a5fa; margin: 0 0 20px;">🔐 Сброс пароля</h1>
  <p>Вы запросили сброс пароля. Нажмите кнопку ниже:</p>
  <p style="margin: 20px 0;">
    <a href="https://syntrex.pro/reset-password?token=%s" 
       style="background: #2563eb; color: white; padding: 12px 28px; border-radius: 6px; text-decoration: none; font-weight: bold;">
      Сбросить пароль
    </a>
  </p>
  <p style="color: #9ca3af; font-size: 12px;">Ссылка действительна 1 час. Если вы не запрашивали сброс — проигнорируйте.</p>
</div>
</body>
</html>`, resetToken)

	return s.sender.Send(toEmail, subject, body)
}
