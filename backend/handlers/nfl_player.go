package handlers

import (
	"context"
	"strings"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/sat-malla/nfl-random-team-analysis/backend/services"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
)

type NFLPlayerHandler struct {
	collection     *mongo.Collection
	sleeperService *services.SleeperService
}

func (h *NFLPlayerHandler) SyncPlayers(c *fiber.Ctx) error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()
	err := h.sleeperService.SyncPlayers(ctx)
	if err != nil {
		return c.Status(fiber.StatusBadGateway).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to sync players: " + err.Error(),
		})
	}
	count, _ := h.collection.CountDocuments(ctx, bson.M{})
	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"status":  "Success",
		"message": "Players synced successfully",
		"count":   count,
	})
}

func (h *NFLPlayerHandler) GetAllPlayers(c *fiber.Ctx) error {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	cursor, err := h.collection.Find(ctx, bson.M{"active": true})
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to fetch players",
		})
	}
	defer cursor.Close(ctx)
	var players []bson.M
	cursor.All(ctx, &players)
	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"status": "Success",
		"data":   players,
		"count":  len(players),
	})
}

func (h *NFLPlayerHandler) GetByPosition(c *fiber.Ctx) error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	position := c.Query("position")
	filter := bson.M{"active": true}
	if position != "" {
		filter["position"] = position
	}
	cursor, err := h.collection.Find(ctx, filter)
	if err != nil {
		return c.Status(fiber.StatusBadGateway).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to fetch players",
		})
	}
	defer cursor.Close(ctx)
	var players []bson.M
	cursor.All(ctx, &players)
	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"status": "Success",
		"data":   players,
		"count":  len(players),
	})
}

func excludeFilter(c *fiber.Ctx) []string {
	raw := c.Query("exclude")
	if raw == "" {
		return nil
	}
	return strings.Split(raw, ",")
}

func (h *NFLPlayerHandler) GetRandomByPosition(c *fiber.Ctx) error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	position := c.Query("position")
	if position == "" {
		return c.Status(fiber.StatusBadRequest).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "position query parameter is required",
		})
	}
	matchFilter := bson.M{"position": position, "active": true}
	if excluded := excludeFilter(c); len(excluded) > 0 {
		matchFilter["full_name"] = bson.M{"$nin": excluded}
	}
	pipeline := mongo.Pipeline{
		{{Key: "$match", Value: matchFilter}},
		{{Key: "$sample", Value: bson.M{"size": 1}}},
	}
	cursor, err := h.collection.Aggregate(ctx, pipeline)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to fetch random player",
		})
	}
	defer cursor.Close(ctx)
	var players []bson.M
	cursor.All(ctx, &players)
	if len(players) == 0 {
		return c.Status(fiber.StatusNotFound).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "No players found for position: " + position,
		})
	}
	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"status": "Success",
		"data":   players[0],
	})
}

func (h *NFLPlayerHandler) GetManyRandomByPosition(c *fiber.Ctx) error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	position := c.Query("position")
	count := c.QueryInt("count", 1)
	slot := c.QueryInt("slot", 0)
	if position == "" {
		return c.Status(fiber.StatusBadRequest).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "position query parameter is required",
		})
	}

	matchFilter := bson.M{"position": position, "active": true}
	switch slot {
	case 1:
		matchFilter["depth_chart_order"] = bson.M{"$lte": 1}
	case 2:
		matchFilter["depth_chart_order"] = bson.M{"$gte": 2}
	}
	if excluded := excludeFilter(c); len(excluded) > 0 {
		matchFilter["full_name"] = bson.M{"$nin": excluded}
	}

	pipeline := mongo.Pipeline{
		{{Key: "$match", Value: matchFilter}},
		{{Key: "$addFields", Value: bson.M{
			"_copies": bson.M{"$range": []any{
				0,
				bson.M{"$max": []any{
					1,
					bson.M{"$toInt": bson.M{"$ifNull": []any{"$selection_weight", 1}}},
				}},
			}},
		}}},
		{{Key: "$unwind", Value: "$_copies"}},
		{{Key: "$sample", Value: bson.M{"size": count * 4}}},
		{{Key: "$group", Value: bson.M{
			"_id": "$_id",
			"doc": bson.M{"$first": "$$ROOT"},
		}}},
		{{Key: "$replaceRoot", Value: bson.M{"newRoot": "$doc"}}},
		{{Key: "$sort", Value: bson.D{{Key: "depth_chart_order", Value: 1}}}},
		{{Key: "$limit", Value: count}},
	}
	cursor, err := h.collection.Aggregate(ctx, pipeline)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to fetch random players",
		})
	}
	defer cursor.Close(ctx)
	var players []bson.M
	cursor.All(ctx, &players)
	if len(players) == 0 {
		return c.Status(fiber.StatusNotFound).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "No players found for position: " + position,
		})
	}
	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"status": "Success",
		"data":   players,
	})
}

func (h *NFLPlayerHandler) GetOneFromManyPositions(c *fiber.Ctx) error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	positions := c.Query("positions")
	if positions == "" {
		return c.Status(fiber.StatusBadRequest).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "positions query parameter is required",
		})
	}
	positionList := strings.Split(positions, ",")
	matchFilter := bson.M{"position": bson.M{"$in": positionList}, "active": true}
	if excluded := excludeFilter(c); len(excluded) > 0 {
		matchFilter["full_name"] = bson.M{"$nin": excluded}
	}
	pipeline := mongo.Pipeline{
		{{Key: "$match", Value: matchFilter}},
		{{Key: "$sample", Value: bson.M{"size": 1}}},
	}
	cursor, err := h.collection.Aggregate(ctx, pipeline)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to fetch random players",
		})
	}
	defer cursor.Close(ctx)
	var players []bson.M
	cursor.All(ctx, &players)
	if len(players) == 0 {
		return c.Status(fiber.StatusNotFound).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "No players found for positions: " + positions,
		})
	}
	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"status": "Success",
		"data":   players[0],
	})
}

func NewNFLPlayerHandler(router fiber.Router, collection *mongo.Collection) {
	sleeperService := services.NewSleeperService(collection)
	handler := &NFLPlayerHandler{
		collection:     collection,
		sleeperService: sleeperService,
	}
	router.Post("/sync", handler.SyncPlayers)                               // POST /api/players/sync - fetch from Sleeper
	router.Get("/", handler.GetAllPlayers)                                  // GET /api/players
	router.Get("/position", handler.GetByPosition)                          // GET /api/players/position?position=QB
	router.Get("/random-player", handler.GetRandomByPosition)               // GET /api/players/random-player?position=QB
	router.Get("/random-players", handler.GetManyRandomByPosition)          // GET /api/players/random-players?position=QB&count=5
	router.Get("/one-from-many-positions", handler.GetOneFromManyPositions) // GET /api/players/one-from-many-positions?positions=QB,WR
}
