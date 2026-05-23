"""
Fallback chat module for Streamlit Cloud deployment.
Provides intelligent FAQ responses without requiring LLM models.
"""

import re

# Comprehensive FAQ responses
FAQ_RESPONSES = {
    "substitute": """Here are common ingredient substitutions:
    
🥚 **Eggs**: Use flax eggs (1 tbsp ground flaxseed + 3 tbsp water per egg), applesauce, or mashed banana
🥛 **Milk**: Try almond milk, oat milk, soy milk, or coconut milk
🧈 **Butter**: Use coconut oil, olive oil, or vegan butter
🍖 **Chicken**: Substitute with tofu, tempeh, or chickpeas
🐟 **Fish**: Try tofu, mushrooms, or plant-based alternatives
🧀 **Cheese**: Use nutritional yeast, cashew cheese, or vegan cheese
🍞 **Bread**: Try lettuce wraps, rice paper, or gluten-free bread
🍝 **Pasta**: Use zucchini noodles, shirataki noodles, or whole wheat pasta
🌾 **Rice**: Try quinoa, cauliflower rice, couscous, or farro""",
    
    "allergy": """For common allergies, here are safe alternatives:

🥜 **Nut Allergies**: Use sunflower seed butter, tahini, or soy nut butter
🌾 **Gluten**: Choose rice, quinoa, buckwheat, or certified gluten-free products
🥛 **Dairy**: Opt for coconut, almond, oat, or soy-based alternatives
🦐 **Shellfish**: Avoid all shellfish; use plant-based proteins instead
🥚 **Eggs**: Use commercial egg replacers or flax/chia eggs

Always read labels carefully and consult with a healthcare provider for severe allergies.""",
    
    "cooking": """Quick cooking tips:

⏱️ **Save Time**: Prep ingredients in advance, use a pressure cooker, or batch cook
🔥 **Better Flavor**: Season in layers, taste as you go, and let meat rest before cutting
🥘 **Texture**: Don't overcrowd the pan, use high heat for searing, low for braising
❄️ **Storage**: Cool food before refrigerating, use airtight containers, label with dates
♻️ **Reduce Waste**: Save vegetable scraps for stock, freeze herbs in oil, repurpose leftovers
👨‍🍳 **Pro Tips**: Toast spices before using, add acid (lemon/vinegar) to brighten flavors, salt pasta water generously""",
    
    "nutrition": """Nutrition basics:

🥗 **Balanced Plate**: 1/2 vegetables, 1/4 protein, 1/4 whole grains
💪 **Protein**: Aim for 0.8g per kg body weight (more if active)
🥤 **Hydration**: Drink 8-10 glasses of water daily
🍎 **Fiber**: Get 25-30g daily from fruits, vegetables, and whole grains
🥑 **Healthy Fats**: Include nuts, seeds, avocado, and olive oil
🍬 **Sugar**: Limit added sugars to less than 10% of daily calories
🧂 **Sodium**: Keep under 2,300mg per day
🌈 **Variety**: Eat a rainbow of colorful fruits and vegetables""",
}


def extract_recipe_info_from_context(context_text):
    """Extract recipe names and details from context for intelligent responses."""
    recipes = []
    try:
        lines = context_text.split('\n')
        current_recipe = {}
        
        for line in lines:
            if 'Name:' in line or 'Recipe:' in line:
                if current_recipe:
                    recipes.append(current_recipe)
                current_recipe = {'name': line.split(':', 1)[1].strip() if ':' in line else line}
            elif 'Calories:' in line and current_recipe:
                try:
                    cal_match = re.search(r'(\d+\.?\d*)', line)
                    if cal_match:
                        current_recipe['calories'] = float(cal_match.group(1))
                except:
                    pass
            elif 'Protein' in line and current_recipe:
                try:
                    prot_match = re.search(r'(\d+\.?\d*)', line)
                    if prot_match:
                        current_recipe['protein'] = float(prot_match.group(1))
                except:
                    pass
                    
        if current_recipe:
            recipes.append(current_recipe)
    except:
        pass
    
    return recipes


def generate_chat_answer(context_text: str, history_text: str, user_message: str) -> str:
    """
    Generate intelligent FAQ-based chat responses.
    This version doesn't require LLM models - perfect for Streamlit Cloud.
    """
    question_lower = user_message.lower()
    recipes = extract_recipe_info_from_context(context_text)
    
    # Questions about substitutions
    if any(word in question_lower for word in ['substitute', 'replace', 'instead', 'swap', 'alternative', 'change']):
        ingredients = ['egg', 'milk', 'butter', 'chicken', 'fish', 'cheese', 'bread', 'pasta', 'rice']
        mentioned = [ing for ing in ingredients if ing in question_lower]
        
        if mentioned:
            response = f"Great question about substituting **{mentioned[0]}**!\n\n"
            response += FAQ_RESPONSES['substitute']
            if recipes:
                response += f"\n\n💡 **Tip**: You have {len(recipes)} recipes. I can help you modify any of them with these substitutions!"
            return response
        return FAQ_RESPONSES['substitute']
    
    # Questions about allergies
    if any(word in question_lower for word in ['allergy', 'allergic', 'intolerance', 'sensitive', 'avoid']):
        return FAQ_RESPONSES['allergy']
    
    # Questions about cooking
    if any(word in question_lower for word in ['cook', 'prepare', 'make', 'how to', 'tips', 'bake', 'fry', 'boil']):
        return FAQ_RESPONSES['cooking']
    
    # Questions about nutrition
    if any(word in question_lower for word in ['calorie', 'calories', 'nutrition', 'protein', 'carb', 'fat']):
        if recipes and any('calories' in r for r in recipes):
            total_cal = sum(r.get('calories', 0) for r in recipes)
            avg_cal = total_cal / len(recipes) if recipes else 0
            return f"""**Nutritional Overview:**

• **Total Calories**: {total_cal:.0f} kcal across {len(recipes)} recipes
• **Average per Recipe**: {avg_cal:.0f} kcal

{FAQ_RESPONSES['nutrition']}"""
        return FAQ_RESPONSES['nutrition']
    
    # Default helpful response
    if recipes:
        return f"""I have information about your {len(recipes)} recommended recipes!

**I can help you with:**
• Ingredient substitutions
• Nutritional information
• Cooking tips and techniques
• Allergy alternatives

**Try asking:**
- "What are the calories in these recipes?"
- "How can I substitute chicken?"
- "Give me cooking tips"

What would you like to know?"""
    else:
        return """I'm your diet assistant! I can help with:
        
• 🔄 **Ingredient substitutions** - Ask about swapping ingredients
• 🚫 **Allergy alternatives** - Get safe food alternatives  
• 👨‍🍳 **Cooking tips** - Learn cooking techniques
• 🥗 **Nutrition advice** - Understand nutritional basics

**Ask me anything about diet, nutrition, or cooking!**"""
