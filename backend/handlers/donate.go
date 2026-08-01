package handlers

import (
	"os"

	"github.com/gofiber/fiber/v2"
	"github.com/stripe/stripe-go/v82"
	"github.com/stripe/stripe-go/v82/checkout/session"
)

type DonateRequest struct {
	AmountCents int64  `json:"amount_cents"`
	Currency string `json:"currency"`
}

func CreateCheckoutSession(c *fiber.Ctx) error {
	var body DonateRequest
	if err := c.BodyParser(&body); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(&fiber.Map{
			"status": "Failure",
			"message": "Invalid request body",
		})
	}
	if body.AmountCents < 50 {
		return c.Status(fiber.StatusBadRequest).JSON(&fiber.Map{
			"status": "Failure",
			"message": "Minimum donation is $0.50",
		})
	}
	if body.Currency == "" {
		body.Currency = "usd"
	}

	stripe.Key = os.Getenv("STRIPE_SECRET_KEY")

	params := &stripe.CheckoutSessionParams{
		PaymentMethodTypes: stripe.StringSlice([]string{"card"}),
		LineItems: []*stripe.CheckoutSessionLineItemParams{
			{
				PriceData: &stripe.CheckoutSessionLineItemPriceDataParams{
					Currency: stripe.String(body.Currency),
					ProductData: &stripe.CheckoutSessionLineItemPriceDataProductDataParams{
						Name: stripe.String("Donation to Pro Football RTGA"),
						Description: stripe.String("Thank you so much for supporting the Pro Football RTGA app!"),
					},
					UnitAmount: stripe.Int64(body.AmountCents),
				},
				Quantity: stripe.Int64(1),
			},
		},
		Mode: stripe.String(string(stripe.CheckoutSessionModePayment)),
		SuccessURL: stripe.String("https://nfl-rtga.com/donate/success"),
		CancelURL: stripe.String("https://nfl-rtga.com/donate/cancel"),
	}

	s, err := session.New(params)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status": "Failure",
			"message": "Failed to create checkout session",
		})
	}

	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"status": "Success",
		"url": s.URL,
	})
}

func NewDonateHandler(router fiber.Router) {
	router.Post("/checkout", CreateCheckoutSession)
}
