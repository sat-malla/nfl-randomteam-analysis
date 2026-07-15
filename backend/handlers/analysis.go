package handlers

import (
	"context"
	"time"

	"github.com/gofiber/fiber/v2"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

type analysisHandler struct {
	collection *mongo.Collection
}

type SaveAnalysisRequest struct {
	TeamID   string         `json:"team_id"`
	Analysis map[string]any `json:"analysis"`
}

func (h *analysisHandler) GetAnalysis(c *fiber.Ctx) error {
	teamId := c.Params("teamId")
	objId, err := primitive.ObjectIDFromHex(teamId)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Invalid team ID",
		})
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	var result bson.M
	err = h.collection.FindOne(ctx, bson.M{"team_id": objId}).Decode(&result)
	if err == mongo.ErrNoDocuments {
		return c.Status(fiber.StatusNotFound).JSON(&fiber.Map{
			"status":  "NotFound",
			"message": "No analysis found for this team",
		})
	}
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to fetch analysis",
		})
	}

	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"status": "Success",
		"data":   result["analysis"],
	})
}

func (h *analysisHandler) SaveAnalysis(c *fiber.Ctx) error {
	teamId := c.Params("teamId")
	objId, err := primitive.ObjectIDFromHex(teamId)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Invalid team ID",
		})
	}

	var body SaveAnalysisRequest
	if err := c.BodyParser(&body); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Invalid request body",
		})
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	doc := bson.M{
		"team_id":    objId,
		"analysis":   body.Analysis,
		"updated_at": time.Now(),
	}

	opts := options.Update().SetUpsert(true)
	_, err = h.collection.UpdateOne(ctx, bson.M{"team_id": objId}, bson.M{"$set": doc}, opts)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to save analysis",
		})
	}

	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"status":  "Success",
		"message": "Analysis saved",
	})
}

func NewAnalysisHandler(router fiber.Router, collection *mongo.Collection) {
	handler := &analysisHandler{collection: collection}
	router.Get("/:teamId", handler.GetAnalysis)
	router.Post("/:teamId", handler.SaveAnalysis)
}
