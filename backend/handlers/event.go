package handlers

import (
	"context"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/sat-malla/nfl-random-team-analysis/backend/models"
)

type eventHandler struct {
	repository models.EventRepository
}

func (h *eventHandler) GetMany(c *fiber.Ctx) error {
	context, cancel := context.WithTimeout(context.Background(), time.Duration(5*time.Second))
	defer cancel()

	events, err := h.repository.GetMany(context)

	if err != nil {
		return c.Status(fiber.StatusBadGateway).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to fetch events",
		})
	}

	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"status":  "Success",
		"message": "Events fetched successfully",
		"data":    events,
	})
}

func (h *eventHandler) GetOne(c *fiber.Ctx) error {
	return c.JSON("GetOne")
}

func (h *eventHandler) CreateOne(c *fiber.Ctx) error {
	return c.JSON("CreateOne")
}

func NewEventHandler(router fiber.Router, repository models.EventRepository) {
	handler := &eventHandler{
		repository: repository,
	}

	// defining endpoints
	router.Get("/", handler.GetMany)
	router.Get("/:eventId", handler.GetOne)
	router.Post("/", handler.CreateOne)
}
