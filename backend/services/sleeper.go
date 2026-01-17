package services

import (
	"context"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

type SleeperPlayer struct {
	PlayerID        string `json:"player_id"`
	FullName        string `json:"full_name"`
	FirstName       string `json:"first_name"`
	LastName        string `json:"last_name"`
	Position        string `json:"position"`
	NFLTeam         string `json:"team"`
	DepthChartOrder int    `json:"depth_chart_order"`
	Active          bool   `json:"active"`
	InjuryStatus    string `json:"injury_status"`
}

type SleeperService struct {
	collection *mongo.Collection
}

func NewSleeperService(collection *mongo.Collection) *SleeperService {
	return &SleeperService{
		collection: collection,
	}
}

func (s *SleeperService) SyncPlayers(ctx context.Context) error {
	log.Println("Fetching players from Sleeper API...")
	resp, err := http.Get("https://api.sleeper.app/v1/players/nfl")
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}

	var players map[string]SleeperPlayer
	if err := json.Unmarshal(body, &players); err != nil {
		return err
	}
	log.Printf("Fetched %d players from Sleeper API", len(players))

	validPositions := map[string]bool{
		"QB": true,
		"RB": true,
		"WR": true,
		"TE": true,
		"OT": true,
		"G":  true,
		"C":  true,
		"DE": true,
		"DT": true,
		"NT": true,
		"LB": true,
		"CB": true,
		"DB": true,
		"FS": true,
		"SS": true,
		"S":  true,
		"K":  true,
		"P":  true,
		"LS": true,
	}

	var operations []mongo.WriteModel
	for playerID, player := range players {
		if !player.Active || player.NFLTeam == "" || !validPositions[player.Position] || player.InjuryStatus != "" {
			continue
		}
		filter := bson.M{"player_id": playerID}
		update := bson.M{"$set": bson.M{ // only updates specified fields, preserve other existing fields
			"player_id":  playerID,
			"full_name":  player.FullName,
			"first_name": player.FirstName,
			"last_name":  player.LastName,
			"position": func() string {
				if player.DepthChartOrder > 2 && (player.Position == "RB" || player.Position == "WR") {
					return "RS"
				} else if player.Position == "NT" {
					return "DT"
				}
				return player.Position
			}(),
			"nfl_team":          player.NFLTeam,
			"depth_chart_order": player.DepthChartOrder,
			"active":            player.Active,
			"injury_status":     player.InjuryStatus,
			"updated_at":        time.Now(),
		}}
		operation := mongo.NewUpdateOneModel().
			SetFilter(filter).
			SetUpdate(update).
			SetUpsert(true)
		operations = append(operations, operation)
	}

	batchSize := 500
	totalUpserted := 0
	for i := 0; i < len(operations); i += batchSize {
		end := min(i+batchSize, len(operations))
		batch := operations[i:end]
		opts := options.BulkWrite().SetOrdered(false) // unordered for better performance
		result, err := s.collection.BulkWrite(ctx, batch, opts)
		if err != nil {
			log.Printf("Error in bulk write batch %d-%d: %v", i, end, err)
			continue
		}
		totalUpserted += int(result.UpsertedCount) + int(result.ModifiedCount)
		log.Printf("Processed batch %d-%d", i, end)

		time.Sleep(100 * time.Millisecond) // Small delay between batches to avoid overwhelming the database
	}
	log.Printf("Synced %d active NFL players to database", totalUpserted)
	return nil
}
