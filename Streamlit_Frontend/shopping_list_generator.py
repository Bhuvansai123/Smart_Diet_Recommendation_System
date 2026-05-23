"""
Smart Shopping List Generator
Consolidates ingredients from multiple recipes into an organized shopping list
"""

from collections import defaultdict
import re


def parse_ingredient(ingredient_text):
    """
    Parse ingredient text to extract quantity, unit, and ingredient name.
    
    Args:
        ingredient_text: Raw ingredient string
        
    Returns:
        dict with 'quantity', 'unit', 'ingredient' keys
    """
    # Common units
    units = [
        'cup', 'cups', 'tablespoon', 'tablespoons', 'tbsp', 'teaspoon', 'teaspoons', 'tsp',
        'pound', 'pounds', 'lb', 'lbs', 'ounce', 'ounces', 'oz',
        'gram', 'grams', 'g', 'kilogram', 'kilograms', 'kg',
        'milliliter', 'milliliters', 'ml', 'liter', 'liters', 'l',
        'pinch', 'dash', 'clove', 'cloves', 'slice', 'slices',
        'can', 'cans', 'package', 'packages', 'bottle', 'bottles'
    ]
    
    ingredient_text = ingredient_text.strip().lower()
    
    # Try to match: number + unit + ingredient
    pattern = r'^([\d./\s]+)?\s*(' + '|'.join(units) + r')?\s*(.+)$'
    match = re.match(pattern, ingredient_text, re.IGNORECASE)
    
    if match:
        quantity_str = match.group(1)
        unit = match.group(2)
        ingredient = match.group(3)
        
        # Parse quantity (handle fractions like "1/2")
        quantity = 1.0
        if quantity_str:
            try:
                # Handle fractions
                if '/' in quantity_str:
                    parts = quantity_str.strip().split()
                    if len(parts) == 2:  # "1 1/2"
                        whole = float(parts[0])
                        frac_parts = parts[1].split('/')
                        quantity = whole + float(frac_parts[0]) / float(frac_parts[1])
                    else:  # "1/2"
                        frac_parts = quantity_str.strip().split('/')
                        quantity = float(frac_parts[0]) / float(frac_parts[1])
                else:
                    quantity = float(quantity_str.strip())
            except:
                quantity = 1.0
        
        return {
            'quantity': quantity,
            'unit': unit.strip() if unit else '',
            'ingredient': ingredient.strip()
        }
    
    return {
        'quantity': 1.0,
        'unit': '',
        'ingredient': ingredient_text.strip()
    }


def normalize_ingredient_name(ingredient):
    """
    Normalize ingredient names for grouping
    (e.g., "chicken breast" and "chicken breasts" should be the same)
    """
    ingredient = ingredient.lower().strip()
    
    # Remove common descriptors that don't affect grouping
    descriptors_to_remove = [
        'fresh', 'frozen', 'dried', 'canned', 'chopped', 'diced', 
        'minced', 'sliced', 'shredded', 'grated', 'crushed',
        'large', 'small', 'medium', 'whole', 'ground'
    ]
    
    for descriptor in descriptors_to_remove:
        ingredient = re.sub(r'\b' + descriptor + r'\b', '', ingredient).strip()
    
    # Singular/plural normalization (simple approach)
    if ingredient.endswith('ies'):
        ingredient = ingredient[:-3] + 'y'
    elif ingredient.endswith('es'):
        ingredient = ingredient[:-2]
    elif ingredient.endswith('s') and not ingredient.endswith('ss'):
        ingredient = ingredient[:-1]
    
    return ingredient.strip()


def normalize_unit(unit, quantity):
    """
    Normalize units for aggregation
    """
    unit = unit.lower().strip()
    
    # Convert to standard forms
    unit_conversions = {
        'tbsp': 'tablespoon',
        'tsp': 'teaspoon',
        'lb': 'pound',
        'lbs': 'pound',
        'oz': 'ounce',
        'g': 'gram',
        'kg': 'kilogram',
        'ml': 'milliliter',
        'l': 'liter'
    }
    
    unit = unit_conversions.get(unit, unit)
    
    # Pluralize if quantity > 1
    if quantity > 1 and not unit.endswith('s'):
        if unit in ['tablespoon', 'teaspoon', 'pound', 'ounce', 'gram', 
                    'kilogram', 'milliliter', 'liter', 'cup', 'can', 
                    'package', 'bottle', 'slice', 'clove']:
            unit += 's'
    
    return unit


def categorize_ingredient(ingredient):
    """
    Categorize ingredient into store sections
    """
    ingredient = ingredient.lower()
    
    # Category keywords
    categories = {
        'Produce': [
            'lettuce', 'tomato', 'onion', 'garlic', 'potato', 'carrot', 
            'celery', 'pepper', 'spinach', 'broccoli', 'cauliflower',
            'cucumber', 'zucchini', 'mushroom', 'avocado', 'lemon', 'lime',
            'apple', 'banana', 'orange', 'berry', 'fruit', 'vegetable',
            'herb', 'parsley', 'cilantro', 'basil', 'thyme', 'rosemary'
        ],
        'Meat & Seafood': [
            'chicken', 'beef', 'pork', 'turkey', 'lamb', 'fish', 'salmon',
            'tuna', 'shrimp', 'bacon', 'sausage', 'ham', 'steak', 'meat'
        ],
        'Dairy & Eggs': [
            'milk', 'cheese', 'butter', 'cream', 'yogurt', 'egg',
            'sour cream', 'cottage cheese', 'cheddar', 'mozzarella', 'parmesan'
        ],
        'Pantry & Staples': [
            'flour', 'sugar', 'salt', 'pepper', 'oil', 'vinegar', 'rice',
            'pasta', 'bread', 'cereal', 'oat', 'bean', 'lentil', 'quinoa',
            'sauce', 'broth', 'stock', 'spice', 'seasoning', 'baking'
        ],
        'Condiments & Sauces': [
            'ketchup', 'mustard', 'mayonnaise', 'soy sauce', 'hot sauce',
            'salsa', 'dressing', 'marinade', 'paste', 'syrup'
        ],
        'Frozen': [
            'frozen', 'ice cream', 'popsicle'
        ],
        'Beverages': [
            'juice', 'soda', 'coffee', 'tea', 'water', 'wine', 'beer'
        ]
    }
    
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in ingredient:
                return category
    
    return 'Other'


def generate_shopping_list(recipes):
    """
    Generate consolidated shopping list from multiple recipes.
    
    Args:
        recipes: List of recipe dictionaries with 'RecipeIngredientParts' key
        
    Returns:
        dict: Shopping list organized by category
    """
    if not recipes:
        return {}
    
    # Dictionary to store aggregated ingredients
    # Key: (normalized_ingredient, unit), Value: total_quantity
    ingredient_aggregator = defaultdict(lambda: {'quantity': 0, 'unit': '', 'original_name': ''})
    
    # Process all recipes
    for recipe in recipes:
        ingredients = recipe.get('RecipeIngredientParts', [])
        
        for ingredient_text in ingredients:
            if not ingredient_text or ingredient_text.strip() == '':
                continue
                
            parsed = parse_ingredient(ingredient_text)
            normalized_name = normalize_ingredient_name(parsed['ingredient'])
            
            # Create unique key for grouping
            key = (normalized_name, parsed['unit'])
            
            # Aggregate
            ingredient_aggregator[key]['quantity'] += parsed['quantity']
            ingredient_aggregator[key]['unit'] = parsed['unit']
            if not ingredient_aggregator[key]['original_name']:
                ingredient_aggregator[key]['original_name'] = parsed['ingredient']
    
    # Organize by category
    categorized_list = defaultdict(list)
    
    for (normalized_name, unit), data in ingredient_aggregator.items():
        quantity = data['quantity']
        unit_normalized = normalize_unit(unit, quantity) if unit else ''
        original_name = data['original_name']
        category = categorize_ingredient(original_name)
        
        # Format quantity nicely
        if quantity == int(quantity):
            quantity_str = str(int(quantity))
        else:
            quantity_str = f"{quantity:.2f}".rstrip('0').rstrip('.')
        
        # Build display string
        if unit_normalized:
            display = f"{quantity_str} {unit_normalized} {original_name}"
        else:
            if quantity > 1:
                display = f"{quantity_str}x {original_name}"
            else:
                display = original_name
        
        categorized_list[category].append({
            'display': display,
            'ingredient': original_name,
            'quantity': quantity,
            'unit': unit_normalized
        })
    
    # Sort items within each category
    for category in categorized_list:
        categorized_list[category].sort(key=lambda x: x['ingredient'])
    
    return dict(categorized_list)


def format_shopping_list_markdown(shopping_list):
    """
    Format shopping list as markdown for display.
    
    Args:
        shopping_list: Dictionary from generate_shopping_list()
        
    Returns:
        str: Formatted markdown string
    """
    if not shopping_list:
        return "No items in shopping list."
    
    markdown = "## 🛒 Shopping List\n\n"
    
    # Category order for better UX
    category_order = [
        'Produce', 'Meat & Seafood', 'Dairy & Eggs', 
        'Pantry & Staples', 'Condiments & Sauces', 
        'Frozen', 'Beverages', 'Other'
    ]
    
    total_items = 0
    
    for category in category_order:
        if category in shopping_list:
            items = shopping_list[category]
            markdown += f"### 📦 {category}\n\n"
            for item in items:
                markdown += f"- {item['display']}\n"
                total_items += 1
            markdown += "\n"
    
    markdown += f"---\n**Total Items: {total_items}**\n"
    
    return markdown


def estimate_recipe_cost(recipe, price_database=None):
    """
    Estimate cost of a single recipe.
    
    Args:
        recipe: Recipe dictionary with 'RecipeIngredientParts' key
        price_database: Optional dict of ingredient prices
        
    Returns:
        float: Estimated recipe cost
    """
    # Simple price estimates (in USD per typical ingredient amount)
    default_prices = {
        'chicken': 3.5,
        'beef': 5.5,
        'pork': 4.0,
        'turkey': 4.5,
        'fish': 6.5,
        'salmon': 8.0,
        'shrimp': 9.0,
        'tuna': 3.0,
        'cheese': 4.5,
        'milk': 2.5,
        'cream': 3.5,
        'butter': 3.0,
        'egg': 2.5,
        'rice': 2.0,
        'pasta': 1.8,
        'bread': 2.5,
        'flour': 2.0,
        'sugar': 2.5,
        'oil': 3.5,
        'olive oil': 6.0,
        'tomato': 2.0,
        'onion': 1.5,
        'garlic': 1.0,
        'potato': 2.0,
        'carrot': 1.5,
        'broccoli': 2.5,
        'spinach': 2.5,
        'lettuce': 2.0,
        'pepper': 2.5,
        'mushroom': 3.0,
        'avocado': 2.0,
        'lemon': 1.0,
        'lime': 1.0,
        'apple': 3.0,
        'banana': 2.0,
        'berry': 4.0,
        'herbs': 2.5,
        'spice': 3.0,
        'sauce': 2.5,
        'broth': 2.0,
        'stock': 2.5,
        'wine': 8.0,
        'vinegar': 2.5
    }
    
    if price_database:
        default_prices.update(price_database)
    
    ingredients = recipe.get('RecipeIngredientParts', [])
    if not ingredients:
        return 5.0  # Default if no ingredients
    
    total_cost = 0.0
    matched_count = 0
    
    for ingredient_text in ingredients:
        ingredient_lower = ingredient_text.lower()
        matched = False
        
        # Try to match with price database
        for key, price in default_prices.items():
            if key in ingredient_lower:
                # Add partial cost (divide by ingredient count for average)
                total_cost += price * 0.3  # Each ingredient contributes 30% of its base price
                matched = True
                matched_count += 1
                break
        
        if not matched:
            # Default cost for unknown ingredients
            total_cost += 1.5
    
    # If very few ingredients matched, use a base estimate
    if matched_count < len(ingredients) * 0.3:  # Less than 30% matched
        total_cost = max(total_cost, len(ingredients) * 1.2)
    
    return round(total_cost, 2)


def estimate_shopping_cost(shopping_list, price_database=None):
    """
    Estimate total shopping cost (basic implementation).
    
    Args:
        shopping_list: Dictionary from generate_shopping_list()
        price_database: Optional dict of ingredient prices
        
    Returns:
        float: Estimated total cost
    """
    # Simple price estimates (in USD per unit)
    default_prices = {
        'chicken': 3.0,
        'beef': 5.0,
        'fish': 6.0,
        'cheese': 4.0,
        'milk': 3.5,
        'egg': 0.25,
        'rice': 2.0,
        'pasta': 1.5,
        'bread': 2.5,
        'tomato': 0.5,
        'onion': 0.3,
        'potato': 0.4,
        'carrot': 0.3
    }
    
    if price_database:
        default_prices.update(price_database)
    
    total_cost = 0.0
    
    for category, items in shopping_list.items():
        for item in items:
            ingredient = item['ingredient'].lower()
            quantity = item['quantity']
            
            # Find matching price
            price_per_unit = 1.0  # default
            for key, price in default_prices.items():
                if key in ingredient:
                    price_per_unit = price
                    break
            
            total_cost += quantity * price_per_unit
    
    return total_cost
