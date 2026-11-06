import json
import math
import os
from uuid import uuid4

from flask import Flask, jsonify, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8192

# Each tuple supplies breakfast, lunch and dinner in that order.
MENUS = {
    "vegan": [
        ("Berry oats with oat milk", "Chickpea cucumber bowl", "Lentil tomato stew"),
        ("Banana cinnamon porridge", "Black bean and rice bowl", "White bean vegetable soup"),
        ("Apple overnight oats", "Lentil quinoa salad", "Roasted cauliflower and chickpea bowl"),
        ("Sweet potato breakfast hash", "Tomato and white bean salad", "Black bean tacos with cabbage"),
        ("Pear and oat bowl", "Roasted vegetable hummus plate", "Mushroom and barley stew"),
        ("Blueberry oat porridge", "Potato and green bean salad", "Chickpea spinach curry"),
        ("Peach breakfast quinoa", "Three-bean salad", "Lentil stuffed peppers"),
    ],
    "vegetarian": [
        ("Greek yogurt with berries", "Lentil and feta salad", "Spinach ricotta pasta"),
        ("Egg and spinach toast", "Chickpea and feta wrap", "Mushroom omelet with potatoes"),
        ("Cottage cheese with peaches", "Roasted vegetable grain bowl", "White bean and parmesan soup"),
    ],
    "omnivore": [
        ("Egg and avocado toast", "Chicken and barley salad", "Salmon with potatoes and green beans"),
        ("Yogurt with oats and berries", "Turkey and vegetable wrap", "Chicken and rice skillet"),
        ("Spinach scrambled eggs", "Tuna and white bean salad", "Roasted chicken with squash"),
    ],
}


def number(data, name, minimum, maximum):
    value = data.get(name)
    if (
        type(value) not in (int, float)
        or not minimum <= value <= maximum
        or not math.isfinite(value)
    ):
        raise ValueError(f"{name} must be a number between {minimum} and {maximum}.")
    return value


def create_plan(data):
    if not isinstance(data, dict):
        raise ValueError("Send a JSON object with your preferences.")
    height = number(data, "height_cm", 80, 250)
    weight = number(data, "weight_kg", 20, 350)
    diet = data.get("diet")
    if not isinstance(diet, str) or diet not in MENUS:
        raise ValueError("Choose omnivore, vegetarian, or vegan.")
    days = data.get("days", 3)
    if type(days) is not int or not 1 <= days <= 7:
        raise ValueError("Choose between 1 and 7 days.")
    menus = MENUS[diet] if diet == "vegan" else MENUS[diet] + MENUS["vegan"]
    return {
        "id": str(uuid4()),
        "bmi": round(weight / (height / 100) ** 2, 1),
        "diet": diet,
        "days": [
            dict(zip(("breakfast", "lunch", "dinner"), meals))
            for meals in menus[:days]
        ],
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/plans")
def plans():
    try:
        plan = create_plan(request.get_json(silent=True))
    except ValueError as error:
        return jsonify(error=str(error)), 400
    table = os.environ.get("PLANS_TABLE")
    if table:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError

        # Store the menu and dietary preference only. BMI and measurements are ephemeral.
        try:
            boto3.client("dynamodb").put_item(
                TableName=table,
                Item={
                    "id": {"S": plan["id"]},
                    "menu": {"S": json.dumps({"diet": plan["diet"], "days": plan["days"]})},
                },
            )
        except (BotoCoreError, ClientError):
            app.logger.exception("Could not save generated menu")
            return jsonify(error="Could not save the plan. Try again in a moment."), 503
    response = jsonify(plan)
    response.headers["Cache-Control"] = "no-store"
    return response, 201
