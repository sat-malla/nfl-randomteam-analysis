package database

import (
	"context"
	"time"

	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

func ConnectToDatabase(uri string) *mongo.Client {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second) // creates context and cancels after 10 seconds if MongoDB is unreachable
	defer cancel()

	client, err := mongo.Connect(ctx, options.Client().ApplyURI(uri))
	if err != nil {
		panic(err)
	}

	err = client.Ping(ctx, nil) // quick ping to database to make sure connection work (robustness)
	if err != nil {
		panic(err)
	}

	return client
}

func GetCollection(client *mongo.Client, dbName string, collectionName string) *mongo.Collection {
	return client.Database(dbName).Collection(collectionName) // collections in MongoDB are like tables in SQL
}
