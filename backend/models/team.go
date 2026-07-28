package models

import (
	"context"
	"time"

	"go.mongodb.org/mongo-driver/bson/primitive"
)

type Player struct {
	Name     string `json:"name" bson:"name"`
	Position string `json:"position" bson:"position"`
	NFL_Team string `json:"nfl_team" bson:"nfl_team"`
}

type Team struct {
	Device_UUID string             `json:"device_uuid" bson:"device_uuid"`
	ID          primitive.ObjectID `json:"id" bson:"_id,omitempty"`
	TeamName    string             `json:"team_name" bson:"team_name"`
	OffenseType string             `json:"offense_type" bson:"offense_type"`
	DefenseType string             `json:"defense_type" bson:"defense_type"`
	HeadCoach   string             `json:"head_coach" bson:"head_coach"`
	Players     []Player           `json:"players" bson:"players"`
	CreatedAt   time.Time          `json:"created_at" bson:"created_at"`
}

type TeamRepository interface {
	GetMany(ctx context.Context) ([]*Team, error)
	GetOne(ctx context.Context, teamId string) (*Team, error)
	GetManyByDeviceUuid(ctx context.Context, deviceUuid string) ([]*Team, error)
	CreateOne(ctx context.Context, team Team) (*Team, error)
	UpdateOne(ctx context.Context, teamId uint, team Team) (*Team, error)
	DeleteOne(ctx context.Context, teamId string) error
}
