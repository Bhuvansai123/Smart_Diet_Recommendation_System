"""
Multi-Turn Meal Planning Dialogue
Interactive conversational meal planner powered by local LLM
"""

import streamlit as st
from llm_chat import generate_chat_answer
from Generate_Recommendations import Generator
from ImageFinder.ImageFinder import get_images_links as find_image
import pandas as pd
from shopping_list_generator import generate_shopping_list, format_shopping_list_markdown, estimate_recipe_cost, estimate_shopping_cost
import json

st.set_page_config(page_title="AI Meal Planner", page_icon="🍽️", layout="wide")

# Session state initialization
if 'planner_stage' not in st.session_state:
    st.session_state.planner_stage = 'welcome'  # welcome, collecting_info, generating, results
    st.session_state.planner_data = {}
    st.session_state.planner_conversation = []
    st.session_state.meal_plan = None
    st.session_state.current_question = None
    st.session_state.used_recipe_names = set()  # Track used recipes for variety

if 'meal_plan_chat_history' not in st.session_state:
    st.session_state.meal_plan_chat_history = []

# Planner stages and questions
PLANNER_FLOW = {
    'welcome': {
        'message': """👋 **Welcome to the AI Meal Planner!**

I'll help you create a personalized weekly meal plan through a simple conversation.

I'll ask you a few questions about:
- Your dietary goals
- Calorie requirements
- Food preferences and restrictions
- Number of meals per day

Ready to start?""",
        'next_stage': 'goal',
        'button_text': 'Start Planning'
    },
    'goal': {
        'question': "🎯 **What's your primary goal?**",
        'options': ['Maintain weight', 'Weight loss', 'Muscle gain', 'General health'],
        'key': 'goal',
        'next_stage': 'calories'
    },
    'calories': {
        'question': "🔥 **What's your target daily calorie intake?**\n\n*If you're not sure, a typical range is 1500-2500 kcal*",
        'input_type': 'number',
        'key': 'daily_calories',
        'min': 1000,
        'max': 4000,
        'default': 2000,
        'next_stage': 'meals_per_day'
    },
    'meals_per_day': {
        'question': "🍽️ **How many meals do you want per day?**",
        'options': ['3 meals (breakfast, lunch, dinner)', 
                    '4 meals (includes morning snack)', 
                    '5 meals (includes morning & afternoon snack)'],
        'key': 'meals_per_day',
        'next_stage': 'dietary_restrictions'
    },
    'dietary_restrictions': {
        'question': "🚫 **Any dietary restrictions or preferences?**",
        'input_type': 'multiselect',
        'options': ['Vegetarian', 'Vegan', 'Gluten-free', 'Dairy-free', 'Nut-free', 
                    'Low-carb', 'High-protein', 'Halal', 'Kosher', 
                    'Prefer Chicken', 'Prefer Fish/Seafood', 'Prefer Beef', 'Prefer Pork',
                    'None'],
        'key': 'dietary_restrictions',
        'next_stage': 'cuisines'
    },
    'cuisines': {
        'question': "🌍 **What cuisines do you enjoy?** (Select multiple)",
        'input_type': 'multiselect',
        'options': ['American', 'Italian', 'Mexican', 'Asian', 'Mediterranean', 
                    'Indian', 'Middle Eastern', 'French', 'Japanese', 'Any'],
        'key': 'preferred_cuisines',
        'next_stage': 'budget'
    },
    'budget': {
        'question': "💰 **What's your daily budget for meals?**\n\n*This helps us recommend cost-effective recipes*",
        'options': ['No budget limit', '$15-20/day (Budget-friendly)', '$20-35/day (Moderate)', '$35-50/day (Flexible)', '$50+/day (Premium)'],
        'key': 'budget',
        'next_stage': 'days'
    },
    'days': {
        'question': "📅 **How many days do you want to plan for?**",
        'options': ['3 days', '5 days (weekdays)', '7 days (full week)'],
        'key': 'planning_days',
        'next_stage': 'generating'
    }
}


def process_user_response(stage, response):
    """Store user response and move to next stage"""
    stage_config = PLANNER_FLOW[stage]
    
    if 'key' in stage_config:
        st.session_state.planner_data[stage_config['key']] = response
    
    # Add to conversation history
    st.session_state.planner_conversation.append({
        'role': 'assistant',
        'content': stage_config.get('question', stage_config.get('message', ''))
    })
    st.session_state.planner_conversation.append({
        'role': 'user',
        'content': str(response)
    })
    
    # Move to next stage
    st.session_state.planner_stage = stage_config['next_stage']


def generate_meal_plan_with_llm():
    """Use LLM to help generate meal plan"""
    data = st.session_state.planner_data
    
    # Parse data
    daily_calories = data.get('daily_calories', 2000)
    meals_option = data.get('meals_per_day', '3 meals')
    num_meals = int(meals_option[0])  # Extract number from "3 meals..."
    
    days_option = data.get('planning_days', '7 days')
    num_days = int(days_option.split()[0])
    
    dietary_restrictions = data.get('dietary_restrictions', [])
    cuisines = data.get('preferred_cuisines', [])
    goal = data.get('goal', 'General health')
    
    # Parse budget
    budget_option = data.get('budget', 'No budget limit')
    budget_per_meal = None
    if '$15-20/day' in budget_option:
        budget_per_meal = 17.5 / num_meals
    elif '$20-35/day' in budget_option:
        budget_per_meal = 27.5 / num_meals
    elif '$35-50/day' in budget_option:
        budget_per_meal = 42.5 / num_meals
    elif '$50+/day' in budget_option:
        budget_per_meal = 60.0 / num_meals
    
    # Calculate meal calorie distribution
    if num_meals == 3:
        meal_calories = {
            'breakfast': int(daily_calories * 0.35),
            'lunch': int(daily_calories * 0.40),
            'dinner': int(daily_calories * 0.25)
        }
    elif num_meals == 4:
        meal_calories = {
            'breakfast': int(daily_calories * 0.30),
            'morning_snack': int(daily_calories * 0.05),
            'lunch': int(daily_calories * 0.40),
            'dinner': int(daily_calories * 0.25)
        }
    else:  # 5 meals
        meal_calories = {
            'breakfast': int(daily_calories * 0.30),
            'morning_snack': int(daily_calories * 0.05),
            'lunch': int(daily_calories * 0.40),
            'afternoon_snack': int(daily_calories * 0.05),
            'dinner': int(daily_calories * 0.20)
        }
    
    # Generate recommendations for each meal for each day
    meal_plan = {}
    used_recipes = set()  # Track recipes used in this meal plan
    
    # Add some randomization to nutrition targets for variety
    import random
    
    with st.spinner(f'🔮 Generating your {num_days}-day meal plan...'):
        for day in range(1, num_days + 1):
            meal_plan[f'Day {day}'] = {}
            
            for meal_name, calories in meal_calories.items():
                # Add randomization to create variety (±10% variation)
                cal_variation = random.uniform(0.9, 1.1)
                varied_calories = calories * cal_variation
                
                # Create nutrition target with some variation
                nutrition_target = [
                    varied_calories,  # Calories
                    varied_calories * random.uniform(0.025, 0.035),  # Fat variation
                    varied_calories * 0.007,  # Saturated fat
                    random.randint(40, 60),  # Cholesterol variation
                    random.randint(350, 450),  # Sodium variation
                    varied_calories * random.uniform(0.11, 0.15),  # Carbs variation
                    random.randint(6, 10),  # Fiber variation
                    random.randint(8, 12),  # Sugar variation
                    varied_calories * random.uniform(0.045, 0.055)  # Protein variation
                ]
                
                # Build ingredient filter based on restrictions and cuisines
                excluded_ingredients = []
                included_ingredients = []
                
                # Dietary restrictions
                if 'Vegetarian' in dietary_restrictions:
                    excluded_ingredients.extend(['beef', 'pork', 'chicken', 'fish', 'meat', 'turkey', 'lamb', 'seafood'])
                if 'Vegan' in dietary_restrictions:
                    excluded_ingredients.extend(['beef', 'pork', 'chicken', 'fish', 'meat', 'turkey', 'lamb', 'seafood',
                                                'milk', 'cheese', 'egg', 'butter', 'cream', 'yogurt', 'whey'])
                
                # Protein preferences
                if 'Prefer Chicken' in dietary_restrictions:
                    included_ingredients.extend(['chicken', 'poultry'])
                if 'Prefer Fish/Seafood' in dietary_restrictions:
                    included_ingredients.extend(['fish', 'salmon', 'tuna', 'shrimp', 'seafood', 'prawn', 'cod', 'tilapia'])
                if 'Prefer Beef' in dietary_restrictions:
                    included_ingredients.extend(['beef', 'steak', 'ground beef'])
                if 'Prefer Pork' in dietary_restrictions:
                    included_ingredients.extend(['pork', 'bacon', 'ham', 'sausage'])
                
                # Cuisine-based ingredients (add key ingredients for specific cuisines)
                cuisine_keywords = []
                if cuisines and 'Any' not in cuisines:
                    for cuisine in cuisines:
                        if cuisine == 'Indian':
                            cuisine_keywords.extend(['curry', 'garam', 'masala', 'cumin', 'turmeric', 'coriander', 
                                                    'cardamom', 'tandoori', 'tikka', 'biryani', 'paneer', 'naan',
                                                    'dal', 'samosa', 'chutney', 'raita', 'korma', 'vindaloo'])
                        elif cuisine == 'Italian':
                            cuisine_keywords.extend(['pasta', 'spaghetti', 'linguine', 'penne', 'fettuccine',
                                                    'tomato', 'basil', 'oregano', 'parmesan', 'parmigiano',
                                                    'mozzarella', 'olive', 'garlic', 'italian', 'marinara',
                                                    'pesto', 'risotto', 'pizza', 'lasagna', 'ravioli'])
                        elif cuisine == 'Mexican':
                            cuisine_keywords.extend(['taco', 'burrito', 'enchilada', 'quesadilla', 'fajita',
                                                    'salsa', 'cilantro', 'lime', 'tortilla', 'avocado', 
                                                    'guacamole', 'cumin', 'chili', 'jalapeño', 'mexican',
                                                    'nacho', 'tamale', 'poblano', 'chipotle'])
                        elif cuisine == 'Asian':
                            cuisine_keywords.extend(['soy', 'ginger', 'sesame', 'rice', 'noodle', 'asian',
                                                    'teriyaki', 'stir fry', 'wok', 'hoisin', 'oyster sauce',
                                                    'fried rice', 'lo mein', 'chow mein', 'asian'])
                        elif cuisine == 'Japanese':
                            cuisine_keywords.extend(['sushi', 'sashimi', 'teriyaki', 'miso', 'soy', 'wasabi', 
                                                    'ginger', 'seaweed', 'nori', 'rice vinegar', 'sake', 'japanese',
                                                    'ramen', 'udon', 'tempura', 'katsu', 'edamame', 'dashi'])
                        elif cuisine == 'Mediterranean':
                            cuisine_keywords.extend(['olive', 'lemon', 'feta', 'hummus', 'chickpea', 'greek',
                                                    'tahini', 'za\'atar', 'pita', 'mediterranean', 'tzatziki',
                                                    'kebab', 'gyro', 'couscous', 'tabbouleh'])
                        elif cuisine == 'French':
                            cuisine_keywords.extend(['butter', 'cream', 'wine', 'herb', 'provence', 'french',
                                                    'baguette', 'croissant', 'brie', 'camembert', 'béarnaise',
                                                    'hollandaise', 'roux', 'quiche', 'crêpe'])
                        elif cuisine == 'Middle Eastern':
                            cuisine_keywords.extend(['hummus', 'tahini', 'chickpea', 'falafel', 'pita', 
                                                    'sumac', 'za\'atar', 'shawarma', 'kebab', 'baba', 'harissa'])
                        elif cuisine == 'American':
                            cuisine_keywords.extend(['burger', 'barbecue', 'bbq', 'bacon', 'cheese', 'potato',
                                                    'american', 'steak', 'rib', 'wings', 'mac'])
                
                # Generate recommendation with more neighbors for variety
                try:
                    # Request MANY more recipes when filtering by cuisine or protein (strict filtering)
                    n_neighbors = 300 if (cuisine_keywords or included_ingredients) else (50 if budget_per_meal else 20)
                    generator = Generator(nutrition_target, [], {'n_neighbors': n_neighbors, 'return_distance': False})
                    recommendations = generator.generate()
                    
                    if recommendations and recommendations.status_code == 200:
                        recipes = recommendations.json().get('output', [])
                        
                        # Add cost estimates
                        if recipes:
                            for recipe in recipes:
                                recipe['estimated_cost'] = estimate_recipe_cost(recipe)
                            
                            # STRICT Filter by cuisine using the Cuisine column - NO FALLBACK!
                            if cuisines and 'Any' not in cuisines:
                                # Use the Cuisine column from enhanced dataset - STRICT MATCH ONLY
                                cuisine_filtered = []
                                for recipe in recipes:
                                    recipe_cuisine = recipe.get('Cuisine', 'Other')
                                    # Check if recipe cuisine matches any of the selected cuisines
                                    if recipe_cuisine in cuisines:
                                        recipe['cuisine_match_score'] = 10  # Perfect match from dataset
                                        cuisine_filtered.append(recipe)
                                
                                if cuisine_filtered:
                                    recipes = cuisine_filtered
                                    cuisine_names = '/'.join(cuisines)
                                    st.success(f"✅ Found {len(cuisine_filtered)} {cuisine_names} recipes for {meal_name}")
                                else:
                                    # STRICT: If no matching cuisine found, skip this meal with error
                                    cuisine_names = '/'.join(cuisines)
                                    st.error(f"❌ No {cuisine_names} recipes found for {meal_name}. Skipping this meal. Try adjusting your filters or selecting 'Any' cuisine.")
                                    recipes = []  # Empty list will skip this meal
                                    continue
                            
                            # STRICT Filter by protein preference if specified - NO FALLBACK!
                            if included_ingredients:
                                protein_filtered = []
                                for recipe in recipes:
                                    recipe_text = f"{recipe['Name']} {' '.join(recipe.get('RecipeIngredientParts', []))}".lower()
                                    # Check if recipe contains preferred protein
                                    if any(ingredient.lower() in recipe_text for ingredient in included_ingredients):
                                        protein_filtered.append(recipe)
                                
                                if protein_filtered:
                                    recipes = protein_filtered
                                    protein_names = '/'.join([p.capitalize() for p in included_ingredients[:3]])  # Show first 3
                                    st.success(f"✅ Found {len(protein_filtered)} {protein_names} recipes for {meal_name}")
                                else:
                                    # STRICT: If no matching protein found, skip this meal with error
                                    protein_names = '/'.join([p.capitalize() for p in included_ingredients[:3]])
                                    st.error(f"❌ No {protein_names} recipes found for {meal_name}. Skipping this meal. Try adjusting your protein preferences.")
                                    recipes = []  # Empty list will skip this meal
                                    continue
                            
                            # Exclude ingredients based on dietary restrictions
                            if excluded_ingredients:
                                restriction_filtered = []
                                for recipe in recipes:
                                    recipe_text = f"{recipe['Name']} {' '.join(recipe.get('RecipeIngredientParts', []))}".lower()
                                    # Check if recipe contains excluded ingredients
                                    has_excluded = any(ingredient.lower() in recipe_text for ingredient in excluded_ingredients)
                                    if not has_excluded:
                                        restriction_filtered.append(recipe)
                                
                                if restriction_filtered:
                                    recipes = restriction_filtered
                            
                            # Filter by budget if specified - STRICT enforcement
                            if budget_per_meal:
                                budget_filtered = [r for r in recipes if r['estimated_cost'] <= budget_per_meal]
                                if budget_filtered:
                                    recipes = budget_filtered
                                else:
                                    # If no recipes within budget, take cheapest ones and warn
                                    recipes = sorted(recipes, key=lambda x: x['estimated_cost'])[:10]
                                    st.warning(f"⚠️ Limited options within ${budget_per_meal:.2f}/meal budget for {meal_name}. Showing cheapest alternatives.")
                            
                            # Find first recipe that hasn't been used yet
                            selected_recipe = None
                            for recipe in recipes:
                                if recipe['Name'] not in used_recipes:
                                    selected_recipe = recipe
                                    used_recipes.add(recipe['Name'])
                                    break
                            
                            # If all recipes from this batch are used, request MORE recipes with different variation
                            if selected_recipe is None and len(recipes) > 0:
                                # Try generating with slightly different parameters to get new recipes
                                cal_variation = random.uniform(0.85, 1.15)  # Wider variation
                                varied_calories_alt = calories * cal_variation
                                
                                nutrition_target_alt = [
                                    varied_calories_alt,
                                    varied_calories_alt * random.uniform(0.02, 0.04),
                                    varied_calories_alt * 0.007,
                                    random.randint(30, 70),
                                    random.randint(300, 500),
                                    varied_calories_alt * random.uniform(0.10, 0.16),
                                    random.randint(5, 12),
                                    random.randint(6, 15),
                                    varied_calories_alt * random.uniform(0.04, 0.06)
                                ]
                                
                                generator_alt = Generator(nutrition_target_alt, [], {'n_neighbors': 100, 'return_distance': False})
                                recommendations_alt = generator_alt.generate()
                                
                                if recommendations_alt and recommendations_alt.status_code == 200:
                                    alt_recipes = recommendations_alt.json().get('output', [])
                                    # Find unused recipe from alternative recommendations
                                    for recipe in alt_recipes:
                                        if recipe['Name'] not in used_recipes:
                                            selected_recipe = recipe
                                            used_recipes.add(recipe['Name'])
                                            break
                            
                            # Final fallback: if still no unique recipe, pick one with different name pattern
                            if selected_recipe is None and len(recipes) > 0:
                                # Sort by how different the name is from already used recipes
                                for recipe in recipes:
                                    name_words = set(recipe['Name'].lower().split())
                                    # Calculate overlap with used recipe names
                                    min_overlap = float('inf')
                                    for used_name in used_recipes:
                                        used_words = set(used_name.lower().split())
                                        overlap = len(name_words & used_words)
                                        min_overlap = min(min_overlap, overlap)
                                    recipe['name_uniqueness'] = min_overlap
                                
                                # Sort by uniqueness and pick least similar
                                recipes_sorted = sorted(recipes, key=lambda x: x.get('name_uniqueness', 0))
                                selected_recipe = recipes_sorted[0]
                                st.info(f"ℹ️ Using similar recipe for variety: {selected_recipe['Name']}")
                            
                            if selected_recipe:
                                selected_recipe['image_link'] = find_image(selected_recipe['Name'])
                                meal_plan[f'Day {day}'][meal_name] = selected_recipe
                            else:
                                st.warning(f"⚠️ Could not find suitable recipe for {meal_name} on Day {day}")
                except Exception as e:
                    st.error(f"Error generating {meal_name} for Day {day}: {str(e)}")
                    continue
    
    st.session_state.meal_plan = meal_plan
    st.session_state.planner_stage = 'results'


def display_meal_plan():
    """Display the generated meal plan"""
    meal_plan = st.session_state.meal_plan
    
    if not meal_plan:
        st.error("No meal plan generated yet.")
        return
    
    st.success("✅ Your personalized meal plan is ready!")
    
    # Display by day
    for day, meals in meal_plan.items():
        with st.expander(f"📅 {day}", expanded=True):
            # Create columns for each meal
            cols = st.columns(len(meals))
            
            for col, (meal_name, recipe) in zip(cols, meals.items()):
                with col:
                    st.markdown(f"**{meal_name.replace('_', ' ').title()}**")
                    
                    recipe_link = recipe.get('image_link', '')
                    if recipe_link:
                        st.image(recipe_link, width=150)
                    
                    recipe_name = recipe['Name']
                    st.markdown(f"*{recipe_name}*")
                    st.caption(f"⚡ {recipe['Calories']:.0f} kcal | "
                             f"🥩 {recipe['ProteinContent']:.0f}g protein")
                    st.caption(f"⏱️ {recipe['CookTime']} min")
                    
                    # Show estimated cost
                    if 'estimated_cost' in recipe:
                        st.caption(f"💰 ~\\${recipe['estimated_cost']:.2f}")
                    
                    # Show ingredients with toggle
                    st.markdown("**Ingredients:**")
                    ingredients = recipe['RecipeIngredientParts']
                    
                    # Show first 5 ingredients
                    for ing in ingredients[:5]:
                        st.caption(f"• {ing}")
                    
                    # Show remaining ingredients in a collapsible section
                    if len(ingredients) > 5:
                        show_more_key = f"show_more_{day}_{meal_name}"
                        if show_more_key not in st.session_state:
                            st.session_state[show_more_key] = False
                        
                        # Show expand button or additional ingredients
                        if not st.session_state[show_more_key]:
                            # Show "see more" button
                            if st.button(f"...see {len(ingredients) - 5} more", key=f"btn_{show_more_key}"):
                                st.session_state[show_more_key] = True
                                st.rerun()
                        else:
                            # Show additional ingredients
                            for ing in ingredients[5:]:
                                st.caption(f"• {ing}")
                            # Show "show less" button at the bottom
                            if st.button(f"Show less", key=f"btn_{show_more_key}"):
                                st.session_state[show_more_key] = False
                                st.rerun()
    st.markdown("---")
    st.subheader("🛒 Weekly Shopping List")
    
    all_recipes = []
    for day_meals in meal_plan.values():
        all_recipes.extend(day_meals.values())
    
    shopping_list = generate_shopping_list(all_recipes)
    shopping_list_md = format_shopping_list_markdown(shopping_list)
    st.markdown(shopping_list_md)
    
    # Calculate and display budget information
    estimated_cost = estimate_shopping_cost(shopping_list)
    
    # Calculate total meal cost from recipes
    total_recipe_cost = sum(recipe.get('estimated_cost', 0) for recipe in all_recipes)
    
    data = st.session_state.planner_data
    budget_option = data.get('budget', 'No budget limit')
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("💵 Estimated Shopping Cost", f"${estimated_cost:.2f}")
    with col2:
        st.metric("🍴 Total Recipe Cost", f"${total_recipe_cost:.2f}")
    
    # Budget status
    if 'No budget limit' not in budget_option:
        # Extract budget from option
        days_option = data.get('planning_days', '7 days')
        num_days = int(days_option.split()[0])
        
        if '$15-20/day' in budget_option:
            total_budget = 17.5 * num_days
        elif '$20-35/day' in budget_option:
            total_budget = 27.5 * num_days
        elif '$35-50/day' in budget_option:
            total_budget = 42.5 * num_days
        else:
            total_budget = 60.0 * num_days
        
        budget_diff = total_budget - total_recipe_cost
        if budget_diff >= 0:
            st.success(f"✅ Within Budget: \${budget_diff:.2f} remaining of \${total_budget:.2f} total")
        else:
            st.warning(f"⚠️ Over Budget: \${abs(budget_diff):.2f} over \${total_budget:.2f} total")
    
    st.caption("*Cost estimates are approximate and may vary by location and brand*")
    
    # Download options
    col1, col2 = st.columns(2)
    with col1:
        # Export meal plan as JSON
        meal_plan_json = json.dumps(meal_plan, indent=2, default=str)
        st.download_button(
            label="📥 Download Meal Plan (JSON)",
            data=meal_plan_json,
            file_name="meal_plan.json",
            mime="application/json"
        )
    
    with col2:
        # Export shopping list as text
        st.download_button(
            label="📝 Download Shopping List",
            data=shopping_list_md,
            file_name="shopping_list.md",
            mime="text/markdown"
        )


# Main UI
title = "<h1 style='text-align: center;'>🍽️ AI Meal Planner</h1>"
st.markdown(title, unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Let's create your personalized meal plan together!</p>", 
            unsafe_allow_html=True)

# Display current stage
current_stage = st.session_state.planner_stage

if current_stage == 'welcome':
    # Welcome stage
    config = PLANNER_FLOW['welcome']
    st.markdown(config['message'])
    
    if st.button(config['button_text'], type='primary'):
        process_user_response('welcome', 'Started planning')
        st.rerun()

elif current_stage == 'generating':
    # Check if we've already shown the loading screen
    if 'generation_started' not in st.session_state:
        # FIRST RERUN: Just show the loading message
        st.session_state.generation_started = True
        
        st.markdown("### 🔮 Generating Your Personalized Meal Plan...")
        st.info("⏳ Please wait while we create your customized meal plan. This may take 30-60 seconds.")
        st.markdown("**🍳 Finding perfect recipes for you...**")
        
        # Force immediate rerun to actually start generation
        st.rerun()
    else:
        # SECOND RERUN: Actually generate the meal plan
        st.markdown("### 🔮 Generating Your Personalized Meal Plan...")
        st.info("⏳ Please wait while we create your customized meal plan. This may take 30-60 seconds.")
        
        progress_placeholder = st.empty()
        progress_placeholder.markdown("**🍳 Finding perfect recipes for you...**")
        
        # Generate meal plan
        generate_meal_plan_with_llm()
        
        # Clear the generation flag
        del st.session_state.generation_started
        
        # Show success
        progress_placeholder.success("✅ Meal plan generated successfully!")
        
        # Small delay
        import time
        time.sleep(1)
        
        st.rerun()  # Refresh page to show results

elif current_stage == 'results':
    # Display results
    display_meal_plan()
    
    # Chat with meal plan
    st.markdown("---")
    st.markdown("### 💬 Questions about your meal plan?")
    

    
    if 'meal_plan_chat_history' not in st.session_state:
        st.session_state.meal_plan_chat_history = []
    
    # Display chat history
    if st.session_state.meal_plan_chat_history:
        for role, text in st.session_state.meal_plan_chat_history:
            if role == "user":
                st.markdown(f"**🙋 You:** {text}")
            else:
                st.markdown(f"**🤖 Assistant:** {text}")
    
    # Initialize clear flag for input
    if 'clear_meal_planner_input' not in st.session_state:
        st.session_state.clear_meal_planner_input = False
    
    # Clear input if flag is set
    if st.session_state.clear_meal_planner_input:
        if 'meal_planner_chat_input' in st.session_state:
            del st.session_state.meal_planner_chat_input
        st.session_state.clear_meal_planner_input = False
    
    # Chat input using form to prevent reprocessing
    with st.form(key="meal_plan_chat_form", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            user_question = st.text_input(
                "Ask about your meal plan:",
                placeholder="e.g., Can I swap Tuesday's lunch?",
                key="meal_planner_chat_input",
                label_visibility="collapsed"
            )
        with col2:
            ask_button = st.form_submit_button("Ask", use_container_width=True)
    
    # Process the question only when form is submitted
    if ask_button and user_question:
        # Check if we're already processing this question
        if 'processing_meal_chat' not in st.session_state:
            st.session_state.processing_meal_chat = True
            
            # Build context from meal plan
            meal_plan_context = "Weekly Meal Plan:\\n"
            for day, meals in st.session_state.meal_plan.items():
                meal_plan_context += f"\\n{day}:\\n"
                for meal_name, recipe in meals.items():
                    meal_plan_context += f"  - {meal_name}: {recipe['Name']} ({recipe['Calories']:.0f} kcal)\\n"
            
            # Build history
            history_text = ""
            for role, text in st.session_state.meal_plan_chat_history:
                prefix = "User" if role == "user" else "Assistant"
                history_text += f"{prefix}: {text}\\n"
            
            with st.spinner("🤔 Thinking..."):
                answer = generate_chat_answer(meal_plan_context, history_text, user_question)
            
            # Append messages to history
            st.session_state.meal_plan_chat_history.append(("user", user_question))
            st.session_state.meal_plan_chat_history.append(("assistant", answer))
            
            # Clear the processing flag
            del st.session_state.processing_meal_chat
            
            # Rerun to show the response (form will clear automatically due to clear_on_submit=True)
            st.rerun()
    
    # Clear chat button
    if st.session_state.meal_plan_chat_history:
        if st.button("🗑️ Clear Chat"):
            st.session_state.meal_plan_chat_history = []
            if 'processing_meal_chat' in st.session_state:
                del st.session_state.processing_meal_chat
            st.rerun()
    
    # Restart button
    if st.button("🔄 Create New Meal Plan"):
        # Clear all planner-related state
        st.session_state.planner_stage = 'welcome'
        st.session_state.planner_data = {}
        st.session_state.planner_conversation = []
        st.session_state.meal_plan = None
        st.session_state.meal_plan_chat_history = []
        st.session_state.used_recipe_names = set()
        if 'clear_meal_planner_input' in st.session_state:
            del st.session_state.clear_meal_planner_input
        if 'processing_meal_chat' in st.session_state:
            del st.session_state.processing_meal_chat
        if 'generation_started' in st.session_state:
            del st.session_state.generation_started
        st.rerun()

else:
    # Question stages
    config = PLANNER_FLOW[current_stage]
    
    # Show conversation history
    if st.session_state.planner_conversation:
        with st.expander("📜 Conversation History", expanded=False):
            for msg in st.session_state.planner_conversation:
                if msg['role'] == 'assistant':
                    st.info(msg['content'])
                else:
                    st.success(f"**You:** {msg['content']}")
    
    # Display current question
    st.markdown(config['question'])
    
    # Get user input based on type
    if 'input_type' in config:
        if config['input_type'] == 'number':
            response = st.number_input(
                "Enter value:",
                min_value=config.get('min', 0),
                max_value=config.get('max', 10000),
                value=config.get('default', 0),
                key=f"input_{current_stage}"
            )
            if st.button("Next →", type='primary'):
                process_user_response(current_stage, response)
                st.rerun()
        
        elif config['input_type'] == 'multiselect':
            response = st.multiselect(
                "Select all that apply:",
                options=config['options'],
                key=f"input_{current_stage}"
            )
            if st.button("Next →", type='primary'):
                if not response:
                    st.warning("Please select at least one option")
                else:
                    process_user_response(current_stage, response)
                    st.rerun()
    
    else:
        # Button options
        for option in config['options']:
            if st.button(option, key=f"btn_{option}"):
                process_user_response(current_stage, option)
                st.rerun()
