import streamlit as st
from Generate_Recommendations import Generator
from ImageFinder.ImageFinder import get_images_links as find_image
import pandas as pd
from streamlit_echarts import st_echarts
from llm_chat import generate_chat_answer
from shopping_list_generator import generate_shopping_list, format_shopping_list_markdown, estimate_shopping_cost, estimate_recipe_cost

st.set_page_config(page_title="Custom Food Recommendation", page_icon="🔍",layout="wide")

nutrition_values=['Calories','FatContent','SaturatedFatContent','CholesterolContent','SodiumContent','CarbohydrateContent','FiberContent','SugarContent','ProteinContent']
if 'custom_generated' not in st.session_state:
    st.session_state.custom_generated = False
    st.session_state.custom_recommendations=None
    st.session_state.custom_recipes_context = ""
    st.session_state.budget_per_recipe = None
    st.session_state.budget_warning = None

# Initialize chat history for this page
if 'custom_chat_history' not in st.session_state:
    st.session_state.custom_chat_history = []

# Initialize chat history for other page (to prevent errors when switching)
if 'diet_chat_history' not in st.session_state:
    st.session_state.diet_chat_history = []

class Recommendation:
    def __init__(self,nutrition_list,nb_recommendations,ingredient_txt,budget_per_recipe=None):
        self.nutrition_list=nutrition_list
        self.nb_recommendations=nb_recommendations
        self.ingredient_txt=ingredient_txt
        self.budget_per_recipe=budget_per_recipe
        pass
    def generate(self,):
        # Request more recipes for budget filtering (budget is required)
        n_neighbors = self.nb_recommendations * 3
        params={'n_neighbors':n_neighbors,'return_distance':False}
        ingredients=self.ingredient_txt.split(';')
        generator=Generator(self.nutrition_list,ingredients,params)
        recommendations=generator.generate()
        
        if recommendations and recommendations.status_code == 200:
            recommendations = recommendations.json()['output']
        else:
            return None, None
        
        budget_warning = None
        
        if recommendations and len(recommendations) > 0:
            # Add cost estimates
            for recipe in recommendations:
                recipe['estimated_cost'] = estimate_recipe_cost(recipe)
                recipe['image_link']=find_image(recipe['Name'])
            
            # Filter by budget - with fallback
            if self.budget_per_recipe:
                budget_filtered = [r for r in recommendations if r['estimated_cost'] <= self.budget_per_recipe]
                if budget_filtered:
                    # Only return recipes within budget
                    recommendations = budget_filtered[:self.nb_recommendations]
                else:
                    # If no recipes within budget, take cheapest ones
                    recommendations = sorted(recommendations, key=lambda x: x['estimated_cost'])[:self.nb_recommendations]
                    cheapest_cost = recommendations[0]['estimated_cost'] if recommendations else 0
                    budget_warning = f"⚠️ No recipes found under \\${self.budget_per_recipe:.2f}. Showing cheapest options starting from \\${cheapest_cost:.2f}."
            else:
                recommendations = recommendations[:self.nb_recommendations]
        
        return recommendations, budget_warning

class Display:
    def __init__(self):
        self.nutrition_values=nutrition_values

    def display_recommendation(self,recommendations):
        st.subheader('Recommended recipes:')
        if recommendations is not None and isinstance(recommendations, list) and len(recommendations) > 0:
            rows=len(recommendations)//5
            for column,row in zip(st.columns(5),range(5)):
                with column:
                    for recipe in recommendations[rows*row:rows*(row+1)]:                             
                        recipe_name=recipe['Name']
                        expander = st.expander(recipe_name)
                        recipe_link=recipe['image_link']
                        recipe_img=f'<div><center><img src={recipe_link} alt={recipe_name}></center></div>'     
                        nutritions_df=pd.DataFrame({value:[recipe[value]] for value in nutrition_values})      
                        
                        expander.markdown(recipe_img,unsafe_allow_html=True)
                        
                        # Show estimated cost
                        if 'estimated_cost' in recipe:
                            expander.info(f"💰 Estimated Cost: ${recipe['estimated_cost']:.2f}")
                        
                        expander.markdown(f'<h5 style="text-align: center;font-family:sans-serif;">Nutritional Values:</h5>', unsafe_allow_html=True)
                        expander.caption('Calories in kcal, other values in grams (g)')                   
                        expander.dataframe(nutritions_df)
                        expander.markdown(f'<h5 style="text-align: center;font-family:sans-serif;">Ingredients:</h5>', unsafe_allow_html=True)
                        for ingredient in recipe['RecipeIngredientParts']:
                            expander.markdown(f"""
                                        - {ingredient}
                            """)
                        expander.markdown(f'<h5 style="text-align: center;font-family:sans-serif;">Recipe Instructions:</h5>', unsafe_allow_html=True)    
                        for instruction in recipe['RecipeInstructions']:
                            expander.markdown(f"""
                                        - {instruction}
                            """) 
                        expander.markdown(f'<h5 style="text-align: center;font-family:sans-serif;">Cooking and Preparation Time:</h5>', unsafe_allow_html=True)   
                        expander.markdown(f"""
                                - Cook Time       : {recipe['CookTime']}min
                                - Preparation Time: {recipe['PrepTime']}min
                                - Total Time      : {recipe['TotalTime']}min
                            """)                       
        else:
            st.info('Couldn\'t find any recipes with the specified ingredients', icon="🙁")
    def display_overview(self,recommendations):
        if recommendations is not None and isinstance(recommendations, list) and len(recommendations) > 0:
            st.subheader('Overview:')
            col1,col2,col3=st.columns(3)
            with col2:
                # Ensure recommendations is a list of dictionaries
                try:
                    recipe_names = [recipe['Name'] for recipe in recommendations if isinstance(recipe, dict) and 'Name' in recipe]
                    if not recipe_names:
                        st.error("No valid recipes found in recommendations")
                        return
                    selected_recipe_name=st.selectbox('Select a recipe', recipe_names)
                except (TypeError, KeyError) as e:
                    st.error(f"Error processing recommendations: {str(e)}")
                    st.write("Debug info - recommendations type:", type(recommendations))
                    if recommendations:
                        st.write("First item type:", type(recommendations[0]))
                    return
            st.markdown(f'<h5 style="text-align: center;font-family:sans-serif;">Nutritional Values:</h5>', unsafe_allow_html=True)
            for recipe in recommendations:
                if recipe['Name']==selected_recipe_name:
                    selected_recipe=recipe
            options = {
        "title": {"text": "Nutrition values", "subtext": f"{selected_recipe_name}", "left": "center"},
        "tooltip": {"trigger": "item"},
        "legend": {"orient": "vertical", "left": "left",},
        "series": [
            {
                "name": "Nutrition values",
                "type": "pie",
                "radius": "50%",
                "data": [{"value":selected_recipe[nutrition_value],"name":nutrition_value} for nutrition_value in self.nutrition_values],
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowOffsetX": 0,
                        "shadowColor": "rgba(0, 0, 0, 0.5)",
                    }
                },
            }
        ],
    }
            st_echarts(options=options, height="600px",)
            st.caption('You can select/deselect an item (nutrition value) from the legend.')

title="<h1 style='text-align: center;'>Custom Food Recommendation</h1>"
st.markdown(title, unsafe_allow_html=True)


display=Display()

with st.form("recommendation_form"):
    st.header('Nutritional values:')
    Calories = st.slider('Calories (kcal)', 0, 2000, 500)
    FatContent = st.slider('FatContent', 0, 100, 50)
    SaturatedFatContent = st.slider('SaturatedFatContent', 0, 13, 0)
    CholesterolContent = st.slider('CholesterolContent', 0, 300, 0)
    SodiumContent = st.slider('SodiumContent', 0, 2300, 400)
    CarbohydrateContent = st.slider('CarbohydrateContent', 0, 325, 100)
    FiberContent = st.slider('FiberContent', 0, 50, 10)
    SugarContent = st.slider('SugarContent', 0, 40, 10)
    ProteinContent = st.slider('ProteinContent', 0, 40, 10)
    nutritions_values_list=[Calories,FatContent,SaturatedFatContent,CholesterolContent,SodiumContent,CarbohydrateContent,FiberContent,SugarContent,ProteinContent]
    st.header('Recommendation options (OPTIONAL):')
    nb_recommendations = st.slider('Number of recommendations', 5, 20,step=5)
    ingredient_txt=st.text_input('Specify ingredients to include in the recommendations separated by ";" :',placeholder='Ingredient1;Ingredient2;...')
    st.caption('Example: Milk;eggs;butter;chicken...')
    
    st.markdown("---")
    st.markdown("### 💰 Budget per Recipe (Required)")
    st.markdown("*Set maximum cost per recipe to filter recommendations*")
    budget_per_recipe = st.number_input('Maximum cost per recipe (USD)', min_value=3.0, max_value=50.0, step=1.0, format="%.2f")
    st.caption(f"✓ Will show recipes under ${budget_per_recipe:.2f} each")
    st.session_state.budget_per_recipe = budget_per_recipe
    
    generated = st.form_submit_button("Generate")
if generated:
    # Validate budget is set (min is 3.0, so anything >= 3.0 is valid)
    if budget_per_recipe is None or budget_per_recipe < 3.0:
        st.error("❌ Please enter a budget amount (minimum $3.00) before generating recommendations.")
        st.stop()
    
    with st.spinner('Generating recommendations...'): 
        recommendation=Recommendation(nutritions_values_list,nb_recommendations,ingredient_txt,budget_per_recipe)
        recommendations, budget_warning = recommendation.generate()
        st.session_state.custom_recommendations=recommendations
        st.session_state.budget_warning = budget_warning
    st.session_state.custom_generated=True 

if st.session_state.custom_generated:
    # Show budget warning if present
    if hasattr(st.session_state, 'budget_warning') and st.session_state.budget_warning:
        st.warning(st.session_state.budget_warning)
    
    if st.session_state.custom_recommendations is None or (isinstance(st.session_state.custom_recommendations, list) and len(st.session_state.custom_recommendations) == 0):
        st.error("No recipes found matching your criteria. Try adjusting your nutritional values or ingredients.")
    else:
        with st.container():
            display.display_recommendation(st.session_state.custom_recommendations)
        with st.container():
            display.display_overview(st.session_state.custom_recommendations)
    
    # Format recommendations as context for chatbot
    def format_recipes_for_context(recommendations):
        if recommendations is None or not isinstance(recommendations, list) or len(recommendations) == 0:
            return "No recommendations available."
        lines = ["Recommended Recipes:"]
        for i, recipe in enumerate(recommendations, start=1):
            # Skip if recipe is not a dictionary
            if not isinstance(recipe, dict):
                continue
            recipe_name = recipe.get('Name', f'Recipe {i}')
            ingredients = ', '.join(recipe.get('RecipeIngredientParts', [])[:5])  # First 5 ingredients
            calories = recipe.get('Calories', 'N/A')
            protein = recipe.get('ProteinContent', 'N/A')
            carbs = recipe.get('CarbohydrateContent', 'N/A')
            lines.append(f"\n{i}. {recipe_name}")
            lines.append(f"   Calories: {calories}, Protein: {protein}g, Carbs: {carbs}g")
            lines.append(f"   Main ingredients: {ingredients}")
        return '\n'.join(lines)
    
    # Store context if recommendations exist and are valid
    if st.session_state.custom_recommendations and isinstance(st.session_state.custom_recommendations, list) and len(st.session_state.custom_recommendations) > 0:
        st.session_state.custom_recipes_context = format_recipes_for_context(st.session_state.custom_recommendations)
    
    # Shopping List Section
    st.markdown("---")
    st.markdown("### 🛒 Shopping List")
    st.markdown("*Get your consolidated grocery list for all recommended recipes*")
    
    if st.button("Generate Shopping List", type="primary"):
        if st.session_state.custom_recommendations:
            with st.spinner("📝 Creating your shopping list..."):
                # Generate shopping list
                shopping_list = generate_shopping_list(st.session_state.custom_recommendations)
                shopping_list_md = format_shopping_list_markdown(shopping_list)
                
                # Display
                st.markdown(shopping_list_md)
                
                # Estimate cost
                estimated_cost = estimate_shopping_cost(shopping_list)
                
                # Calculate total recipe cost
                total_recipe_cost = sum(recipe.get('estimated_cost', 0) for recipe in st.session_state.custom_recommendations)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("💵 Shopping Cost", f"${estimated_cost:.2f}")
                with col2:
                    st.metric("🍴 Recipe Total", f"${total_recipe_cost:.2f}")
                
                # Show budget status if budget was set
                if st.session_state.budget_per_recipe:
                    total_budget = st.session_state.budget_per_recipe * len(st.session_state.custom_recommendations)
                    budget_diff = total_budget - total_recipe_cost
                    if budget_diff >= 0:
                        st.success(f"✅ Within Budget: \${budget_diff:.2f} remaining of \${total_budget:.2f} total")
                    else:
                        st.warning(f"⚠️ Over Budget: \${abs(budget_diff):.2f} over \${total_budget:.2f} total")
                
                st.caption("*Cost estimates are approximate and may vary by location and brand*")
                
                # Download button
                st.download_button(
                    label="📥 Download Shopping List",
                    data=shopping_list_md,
                    file_name="shopping_list.md",
                    mime="text/markdown"
                )
        else:
            st.warning("No recommendations available. Generate recommendations first!")
    
    # Chat UI Section
    st.markdown("---")
    st.markdown("### 💬 Ask the Diet Assistant")
    
    st.markdown("*Have questions about your recommendations? Ask about ingredient substitutions, alternatives, or cooking tips!*")
    
    # Display chat history
    if st.session_state.custom_chat_history:
        st.markdown("### Conversation:")
        for role, text in st.session_state.custom_chat_history:
            if role == "user":
                st.markdown(f"**🙋 You:** {text}")
            else:
                st.markdown(f"**🤖 Assistant:** {text}")
        st.markdown("---")
    
    # Initialize clear flag
    if 'clear_input' not in st.session_state:
        st.session_state.clear_input = False
    
    # Clear input if flag is set
    if st.session_state.clear_input:
        if 'chat_input' in st.session_state:
            del st.session_state.chat_input
        st.session_state.clear_input = False
    
    # Chat input
    col1, col2 = st.columns([4, 1])
    with col1:
        user_question = st.text_input(
            "Ask a question:",
            placeholder="e.g., What can I use instead of eggs?",
            key="chat_input"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing
        ask_button = st.button("Ask")
    
    if ask_button and user_question:
        # Append user message
        st.session_state.custom_chat_history.append(("user", user_question))
        
        # Build history text
        history_text = ""
        for role, text in st.session_state.custom_chat_history:
            prefix = "User" if role == "user" else "Assistant"
            history_text += f"{prefix}: {text}\n"
        
        # Get context from session
        context_text = st.session_state.get("custom_recipes_context", "No recipes context available.")
        
        # Generate answer
        with st.spinner("🤔 Thinking..."):
            answer = generate_chat_answer(context_text, history_text, user_question)
        
        # Append assistant answer
        st.session_state.custom_chat_history.append(("assistant", answer))
        
        # Set flag to clear input on next run
        st.session_state.clear_input = True
        
        # Rerun to refresh the chat display
        st.rerun()
    
    # Clear chat button
    if st.session_state.custom_chat_history:
        if st.button("Clear Chat History"):
            st.session_state.custom_chat_history = []
            st.rerun()