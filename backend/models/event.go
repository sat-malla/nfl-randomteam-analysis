package models

import (
	"context"
	"time"

	"go.mongodb.org/mongo-driver/bson/primitive"
)

type Event struct {
	ID        primitive.ObjectID `json:"id" bson:"_id,omitempty"` // mongoDB's unique identifier type when creating new Events, omitempty means if this is empty mongodb will auto-generate an ID
	Name      string             `json:"name" bson:"name"`
	Location  string             `json:"location" bson:"location"`
	Date      time.Time          `json:"date" bson:"date"`
	CreatedAt time.Time          `json:"createdAt" bson:"created_at"`
	UpdatedAt time.Time          `json:"updatedAt" bson:"updated_at"`
}

// struct stored to json the field name is the json tag. For example, for ID the json field name is "id"
// struct stored to mongodb the field name is the bson tag. For example, for ID the mongodb field name is "_id"

type EventRepository interface {
	GetMany(ctx context.Context) ([]*Event, error)
	GetOne(ctx context.Context, eventId string) (*Event, error)
	CreateOne(ctx context.Context, event Event) (*Event, error)
}
