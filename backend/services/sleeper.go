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
	YearsExp        int    `json:"years_exp"`
	SearchRank      int    `json:"search_rank"`
	Active          bool   `json:"active"`
	InjuryStatus    string `json:"injury_status"`
}

type SleeperService struct {
	collection *mongo.Collection
}

func selectionWeight(searchRank, yearsExp, depthChartOrder int) int {
	const noRank = 999
	const sentinel = 9999999
	
	var base int
	if searchRank <= 0 || searchRank >= sentinel {
		if yearsExp <= 0 {
			base = 1
		} else if yearsExp >= 3 {
			base = 3
		} else {
			base = 2
		}
	} else if searchRank < noRank {
		switch {
		case searchRank <= 100:
			base = 20
		case searchRank <= 300:
			base = 15
		default:
			base = 10
		}
	} else {
		if yearsExp <= 0 {
			base = 1
		} else if yearsExp >= 5 {
			base = 8
		} else {
			base = 2 + yearsExp
		}
	}

	switch {
	case depthChartOrder <= 0:
		base = base * 2 / 5
	case depthChartOrder == 1:
		// None - Starter: full weight (no change)
	case depthChartOrder == 2:
		base = base / 2
	default:
		base = base / 5
	}

	if base < 1 {
		base = 1
	}
	return base
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
		"G": true,
		"C": true,
		"DE": true,
		"DT": true,
		"NT": true,
		"LB": true,
		"CB": true,
		"DB": true,
		"SS": true,
		"S": true,
		"K": true,
		"P": true,
		"LS": true,
	}

	var operations []mongo.WriteModel
	for playerID, player := range players {
		if !player.Active || player.NFLTeam == "" || !validPositions[player.Position] || player.InjuryStatus != "" {
			continue
		}
		filter := bson.M{"player_id": playerID}
		update := bson.M{"$set": bson.M{
			"player_id": playerID,
			"full_name": player.FullName,
			"first_name": player.FirstName,
			"last_name": player.LastName,
			"position": func() string {
				if player.DepthChartOrder > 2 && (player.Position == "RB" || player.Position == "WR") {
					return "RS"
				} else if player.Position == "NT" {
					return "DT"
				}
				return player.Position
			}(),
			"nfl_team": player.NFLTeam,
			"depth_chart_order": player.DepthChartOrder,
			"years_exp": player.YearsExp,
			"search_rank": player.SearchRank,
			"selection_weight": selectionWeight(player.SearchRank, player.YearsExp, player.DepthChartOrder),
			"active": player.Active,
			"injury_status": player.InjuryStatus,
			"updated_at": time.Now(),
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
		opts := options.BulkWrite().SetOrdered(false)
		result, err := s.collection.BulkWrite(ctx, batch, opts)
		if err != nil {
			log.Printf("Error in bulk write batch %d-%d: %v", i, end, err)
			continue
		}
		totalUpserted += int(result.UpsertedCount) + int(result.ModifiedCount)
		log.Printf("Processed batch %d-%d", i, end)

		time.Sleep(100 * time.Millisecond)
	}
	log.Printf("Synced %d active NFL players to database", totalUpserted)
	return nil
}
