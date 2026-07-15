package handlers

import (
	"encoding/json"
	"fmt"
	"io"
	"math/rand"
	"net/http"
	"os"

	"github.com/gofiber/fiber/v2"
)

type coachRow struct {
	ID        int    `json:"id"`
	Season    int    `json:"season"`
	Team      string `json:"team"`
	HeadCoach string `json:"head_coach"`
}

func GetRandomCoach(c *fiber.Ctx) error {
	supabaseURL := os.Getenv("SUPABASE_URL")
	supabaseKey := os.Getenv("SUPABASE_KEY")
	if supabaseURL == "" || supabaseKey == "" {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Supabase not configured",
		})
	}

	url := fmt.Sprintf("%s/rest/v1/coaches?select=id,season,team,head_coach&season=eq.2025", supabaseURL)
	req, _ := http.NewRequest("GET", url, nil)
	req.Header.Set("apikey", supabaseKey)
	req.Header.Set("Authorization", "Bearer "+supabaseKey)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return c.Status(fiber.StatusBadGateway).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to reach Supabase: " + err.Error(),
		})
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	var coaches []coachRow
	if err := json.Unmarshal(body, &coaches); err != nil || len(coaches) == 0 {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "No coaches found",
		})
	}

	coach := coaches[rand.Intn(len(coaches))]
	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"status": "Success",
		"data":   coach,
	})
}

func NewCoachHandler(router fiber.Router) {
	router.Get("/random", GetRandomCoach)
}
