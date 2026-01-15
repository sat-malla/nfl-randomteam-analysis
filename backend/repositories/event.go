package repositories

import (
	"context"

	"github.com/sat-malla/nfl-random-team-analysis/backend/models"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
)

type eventRepository struct {
	collection *mongo.Collection
}

func (r *eventRepository) GetMany(ctx context.Context) ([]*models.Event, error) {
	cursor, err := r.collection.Find(ctx, bson.M{}) // cursor is an iterator MongoDB returns
	if err != nil {
		return nil, err
	}
	defer cursor.Close(ctx)

	var events []*models.Event
	if err := cursor.All(ctx, &events); err != nil { // reads all documents from the cursor into the events slice
		return nil, err
	}

	return events, nil
}

func (r *eventRepository) GetOne(ctx context.Context, eventId string) (*models.Event, error) {
	objectId, err := primitive.ObjectIDFromHex(eventId)
	if err != nil {
		return nil, err
	}
	var event models.Event
	err = r.collection.FindOne(ctx, bson.M{"_id": objectId}).Decode(&event) // finds the document with the given ID, and the Decode() populates event struct with document data
	if err != nil {
		return nil, err
	}
	return &event, nil
}

func (r *eventRepository) CreateOne(ctx context.Context, event models.Event) (*models.Event, error) {
	event.ID = primitive.NewObjectID()
	_, err := r.collection.InsertOne(ctx, event)
	if err != nil {
		return nil, err
	}
	return &event, nil
}

func NewEventRepository(collection *mongo.Collection) models.EventRepository {
	return &eventRepository{
		collection: collection,
	}
}
