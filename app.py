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


# Core ingredients for each meal, without quantities or pantry staples.
INGREDIENTS = {
    'Berry oats with oat milk': ('oats', 'berries', 'oat milk'),
    'Chickpea cucumber bowl': ('chickpeas', 'cucumber', 'lemon'),
    'Lentil tomato stew': ('lentils', 'tomatoes', 'onion'),
    'Banana cinnamon porridge': ('banana', 'oats', 'cinnamon'),
    'Black bean and rice bowl': ('black beans', 'rice', 'lime'),
    'White bean vegetable soup': ('white beans', 'carrots', 'celery'),
    'Apple overnight oats': ('apple', 'oats', 'oat milk'),
    'Lentil quinoa salad': ('lentils', 'quinoa', 'lemon'),
    'Roasted cauliflower and chickpea bowl': ('cauliflower', 'chickpeas', 'lemon'),
    'Sweet potato breakfast hash': ('sweet potato', 'onion', 'bell peppers'),
    'Tomato and white bean salad': ('tomatoes', 'white beans', 'lemon'),
    'Black bean tacos with cabbage': ('black beans', 'tortillas', 'cabbage'),
    'Pear and oat bowl': ('pear', 'oats', 'oat milk'),
    'Roasted vegetable hummus plate': ('hummus', 'bell peppers', 'carrots'),
    'Mushroom and barley stew': ('mushrooms', 'barley', 'onion'),
    'Blueberry oat porridge': ('blueberries', 'oats', 'oat milk'),
    'Potato and green bean salad': ('potatoes', 'green beans', 'lemon'),
    'Chickpea spinach curry': ('chickpeas', 'spinach', 'curry powder'),
    'Peach breakfast quinoa': ('peach', 'quinoa', 'oat milk'),
    'Three-bean salad': ('chickpeas', 'white beans', 'black beans'),
    'Lentil stuffed peppers': ('lentils', 'bell peppers', 'tomatoes'),
    'Greek yogurt with berries': ('Greek yogurt', 'berries'),
    'Lentil and feta salad': ('lentils', 'feta', 'lemon'),
    'Spinach ricotta pasta': ('spinach', 'ricotta', 'pasta'),
    'Egg and spinach toast': ('eggs', 'spinach', 'bread'),
    'Chickpea and feta wrap': ('chickpeas', 'feta', 'tortillas'),
    'Mushroom omelet with potatoes': ('mushrooms', 'eggs', 'potatoes'),
    'Cottage cheese with peaches': ('cottage cheese', 'peach'),
    'Roasted vegetable grain bowl': ('quinoa', 'bell peppers', 'carrots'),
    'White bean and parmesan soup': ('white beans', 'vegetarian parmesan', 'celery'),
    'Egg and avocado toast': ('eggs', 'avocado', 'bread'),
    'Chicken and barley salad': ('chicken', 'barley', 'cucumber'),
    'Salmon with potatoes and green beans': ('salmon', 'potatoes', 'green beans'),
    'Yogurt with oats and berries': ('yogurt', 'oats', 'berries'),
    'Turkey and vegetable wrap': ('turkey', 'tortillas', 'bell peppers'),
    'Chicken and rice skillet': ('chicken', 'rice', 'onion'),
    'Spinach scrambled eggs': ('spinach', 'eggs'),
    'Tuna and white bean salad': ('tuna', 'white beans', 'lemon'),
    'Roasted chicken with squash': ('chicken', 'squash', 'onion'),
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
    selected = menus[:days]
    groceries = sorted({
        ingredient
        for meals in selected
        for meal in meals
        for ingredient in INGREDIENTS[meal]
    }, key=str.casefold)
    return {
        "groceries": groceries,
        "id": str(uuid4()),
        "bmi": round(weight / (height / 100) ** 2, 1),
        "diet": diet,
        "days": [
            dict(zip(("breakfast", "lunch", "dinner"), meals))
            for meals in selected
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
