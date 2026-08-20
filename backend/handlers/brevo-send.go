package handlers

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"os"

	"github.com/gofiber/fiber/v2"
)

type NotifyRequest struct {
	ToEmail    string         `json:"to_email"`
	ToName     string         `json:"to_name"`
	TemplateID int64          `json:"template_id"`
	Params     map[string]any `json:"params"`
}

type brevoRecipient struct {
	Email string `json:"email"`
	Name  string `json:"name,omitempty"`
}

type brevoEmailPayload struct {
	To         []brevoRecipient `json:"to"`
	TemplateID int64            `json:"templateId"`
	Params     map[string]any   `json:"params,omitempty"`
}

func SendNotification(c *fiber.Ctx) error {
	var body NotifyRequest
	if err := c.BodyParser(&body); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Invalid request body",
		})
	}
	if body.ToEmail == "" {
		return c.Status(fiber.StatusBadRequest).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "to_email is required",
		})
	}
	if body.TemplateID == 0 {
		return c.Status(fiber.StatusBadRequest).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "template_id is required",
		})
	}

	apiKey := os.Getenv("BREVO_API_KEY")
	if apiKey == "" {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "BREVO_API_KEY not configured",
		})
	}

	payload := brevoEmailPayload{
		To: []brevoRecipient{
			{Email: body.ToEmail, Name: body.ToName},
		},
		TemplateID: body.TemplateID,
		Params:     body.Params,
	}

	payloadBytes, err := json.Marshal(payload)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to build Brevo request",
		})
	}

	req, err := http.NewRequest("POST", "https://api.brevo.com/v3/smtp/email", bytes.NewReader(payloadBytes))
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to create request",
		})
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")
	req.Header.Set("api-key", apiKey)

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return c.Status(fiber.StatusBadGateway).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to reach Brevo API",
		})
	}
	defer resp.Body.Close()

	respBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to read Brevo response",
		})
	}

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		return c.Status(fiber.StatusBadGateway).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Brevo API error: " + string(respBytes),
		})
	}

	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"status":  "Success",
		"message": "Email sent",
	})
}

func NewNotifyHandler(router fiber.Router) {
	router.Post("/send", SendNotification)
}
