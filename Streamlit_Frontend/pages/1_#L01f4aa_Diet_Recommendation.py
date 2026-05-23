import streamlit as st
import pandas as pd
from Generate_Recommendations import Generator
from random import uniform as rnd
from ImageFinder.ImageFinder import get_images_links as find_image
from streamlit_echarts import st_echarts
from llm_chat import generate_chat_answer
from shopping_list_generator import generate_shopping_list, format_shopping_list_markdown, estimate_shopping_cost, estimate_recipe_cost

st.set_page_config(page_title="Automatic Diet Recommendation", page_icon="💪",layout="wide")

nutritions_values=['Calories','FatContent','SaturatedFatContent','CholesterolContent','SodiumContent','CarbohydrateContent','FiberContent','SugarContent','ProteinContent']
# Streamlit states initialization
if 'person' not in st.session_state:
    st.session_state.generated = False
    st.session_state.diet_recommendations=None
    st.session_state.person=None
    st.session_state.weight_loss_option=None
    st.session_state.diet_recipes_context = ""
    st.session_state.budget_limit = None

# Initialize chat history for this page
if 'diet_chat_history' not in st.session_state:
    st.session_state.diet_chat_history = []

# Initialize chat history for other page (to prevent errors when switching)
if 'custom_chat_history' not in st.session_state:
    st.session_state.custom_chat_history = []
class Person:

    def __init__(self,age,height,weight,gender,activity,meals_calories_perc,weight_loss,budget_limit=None):
        self.age=age
        self.height=height
        self.weight=weight
        self.gender=gender
        self.activity=activity
        self.meals_calories_perc=meals_calories_perc
        self.weight_loss=weight_loss
        self.budget_limit=budget_limit
    def calculate_bmi(self,):
        bmi=round(self.weight/((self.height/100)**2),2)
        return bmi

    def display_result(self,):
        bmi=self.calculate_bmi()
        bmi_string=f'{bmi} kg/m²'
        if bmi<18.5:
            category='Underweight'
            color='Red'
        elif 18.5<=bmi<25:
            category='Normal'
            color='Green'
        elif 25<=bmi<30:
            category='Overweight'
            color='Yellow'
        else:
            category='Obesity'    
            color='Red'
        return bmi_string,category,color

    def calculate_bmr(self):
        if self.gender=='Male':
            bmr=10*self.weight+6.25*self.height-5*self.age+5
        else:
            bmr=10*self.weight+6.25*self.height-5*self.age-161
        return bmr

    def calories_calculator(self):
        activites=['Little/no exercise', 'Light exercise', 'Moderate exercise (3-5 days/wk)', 'Very active (6-7 days/wk)', 'Extra active (very active & physical job)']
        weights=[1.2,1.375,1.55,1.725,1.9]
        weight = weights[activites.index(self.activity)]
        maintain_calories = self.calculate_bmr()*weight
        return maintain_calories

    def generate_recommendations(self,):
        total_calories=self.weight_loss*self.calories_calculator()
        recommendations=[]
        
        # Calculate budget per meal - budget is now required
        budget_per_meal = self.budget_limit / len(self.meals_calories_perc)
        
        for meal in self.meals_calories_perc:
            meal_calories=self.meals_calories_perc[meal]*total_calories
            if meal=='breakfast':        
                recommended_nutrition = [meal_calories,rnd(10,30),rnd(0,4),rnd(0,30),rnd(0,400),rnd(40,75),rnd(4,10),rnd(0,10),rnd(30,100)]
            elif meal=='launch':
                recommended_nutrition = [meal_calories,rnd(20,40),rnd(0,4),rnd(0,30),rnd(0,400),rnd(40,75),rnd(4,20),rnd(0,10),rnd(50,175)]
            elif meal=='dinner':
                recommended_nutrition = [meal_calories,rnd(20,40),rnd(0,4),rnd(0,30),rnd(0,400),rnd(40,75),rnd(4,20),rnd(0,10),rnd(50,175)] 
            else:
                recommended_nutrition = [meal_calories,rnd(10,30),rnd(0,4),rnd(0,30),rnd(0,400),rnd(40,75),rnd(4,10),rnd(0,10),rnd(30,100)]
            
            # Request more recipes for budget filtering (budget is required)
            n_neighbors = 25
            generator=Generator(recommended_nutrition, [], {'n_neighbors': n_neighbors, 'return_distance': False})
            recommended_recipes=generator.generate().json()['output']
            
            # Filter by budget - STRICT enforcement (budget is required)
            if budget_per_meal:
                filtered_recipes = []
                for recipe in recommended_recipes:
                    recipe_cost = estimate_recipe_cost(recipe)
                    recipe['estimated_cost'] = recipe_cost
                    # Strict: only include recipes within budget
                    if recipe_cost <= budget_per_meal:
                        filtered_recipes.append(recipe)
                
                # Sort by cost (cheapest first) and nutritional match
                filtered_recipes.sort(key=lambda x: x.get('estimated_cost', 999))
                
                # Take top recipes within budget
                if len(filtered_recipes) >= 5:
                    recommended_recipes = filtered_recipes[:5]
                elif len(filtered_recipes) > 0:
                    # Use what we have within budget
                    recommended_recipes = filtered_recipes
                else:
                    # Last resort: take 5 cheapest recipes
                    recommended_recipes_sorted = sorted(recommended_recipes, key=lambda x: x.get('estimated_cost', 999))
                    recommended_recipes = recommended_recipes_sorted[:5]
                    st.warning(f"⚠️ No recipes found within ${budget_per_meal:.2f} budget for {meal}. Showing cheapest options.")
                
                recommended_recipes = recommended_recipes[:5]
            else:
                # Add cost estimates even without budget
                for recipe in recommended_recipes:
                    recipe['estimated_cost'] = estimate_recipe_cost(recipe)
            
            recommendations.append(recommended_recipes)
        
        for recommendation in recommendations:
            for recipe in recommendation:
                recipe['image_link']=find_image(recipe['Name']) 
        return recommendations

class Display:
    def __init__(self):
        self.plans=["Maintain weight","Mild weight loss","Weight loss","Extreme weight loss"]
        self.weights=[1,0.9,0.8,0.6]
        self.losses=['-0 kg/week','-0.25 kg/week','-0.5 kg/week','-1 kg/week']
        pass

    def display_bmi(self,person):
        st.header('BMI CALCULATOR')
        bmi_string,category,color = person.display_result()
        st.metric(label="Body Mass Index (BMI)", value=bmi_string)
        new_title = f'<p style="font-family:sans-serif; color:{color}; font-size: 25px;">{category}</p>'
        st.markdown(new_title, unsafe_allow_html=True)
        st.markdown(
            """
            Healthy BMI range: 18.5 kg/m² - 25 kg/m².
            """)   

    def display_calories(self,person):
        st.header('CALORIES CALCULATOR')        
        maintain_calories=person.calories_calculator()
        st.write('The results show a number of daily calorie estimates that can be used as a guideline for how many calories to consume each day to maintain, lose, or gain weight at a chosen rate.')
        for plan,weight,loss,col in zip(self.plans,self.weights,self.losses,st.columns(4)):
            with col:
                st.metric(label=plan,value=f'{round(maintain_calories*weight)} kcal/day',delta=loss,delta_color="inverse")

    def display_recommendation(self,person,recommendations):
        st.header('DIET RECOMMENDATOR')  
        with st.spinner('Generating recommendations...'): 
            meals=person.meals_calories_perc
            st.subheader('Recommended recipes:')
            for meal_name,column,recommendation in zip(meals,st.columns(len(meals)),recommendations):
                with column:
                    #st.markdown(f'<div style="text-align: center;">{meal_name.upper()}</div>', unsafe_allow_html=True) 
                    st.markdown(f'##### {meal_name.upper()}')    
                    for recipe in recommendation:
                        
                        recipe_name=recipe['Name']
                        expander = st.expander(recipe_name)
                        recipe_link=recipe['image_link']
                        recipe_img=f'<div><center><img src={recipe_link} alt={recipe_name}></center></div>'     
                        nutritions_df=pd.DataFrame({value:[recipe[value]] for value in nutritions_values})      
                        
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

    def display_meal_choices(self,person,recommendations):    
        st.subheader('Choose your meal composition:')
        # Display meal compositions choices
        if len(recommendations)==3:
            breakfast_column,launch_column,dinner_column=st.columns(3)
            with breakfast_column:
                breakfast_choice=st.selectbox(f'Choose your breakfast:',[recipe['Name'] for recipe in recommendations[0]])
            with launch_column:
                launch_choice=st.selectbox(f'Choose your launch:',[recipe['Name'] for recipe in recommendations[1]])
            with dinner_column:
                dinner_choice=st.selectbox(f'Choose your dinner:',[recipe['Name'] for recipe in recommendations[2]])  
            choices=[breakfast_choice,launch_choice,dinner_choice]     
        elif len(recommendations)==4:
            breakfast_column,morning_snack,launch_column,dinner_column=st.columns(4)
            with breakfast_column:
                breakfast_choice=st.selectbox(f'Choose your breakfast:',[recipe['Name'] for recipe in recommendations[0]])
            with morning_snack:
                morning_snack=st.selectbox(f'Choose your morning_snack:',[recipe['Name'] for recipe in recommendations[1]])
            with launch_column:
                launch_choice=st.selectbox(f'Choose your launch:',[recipe['Name'] for recipe in recommendations[2]])
            with dinner_column:
                dinner_choice=st.selectbox(f'Choose your dinner:',[recipe['Name'] for recipe in recommendations[3]])
            choices=[breakfast_choice,morning_snack,launch_choice,dinner_choice]                
        else:
            breakfast_column,morning_snack,launch_column,afternoon_snack,dinner_column=st.columns(5)
            with breakfast_column:
                breakfast_choice=st.selectbox(f'Choose your breakfast:',[recipe['Name'] for recipe in recommendations[0]])
            with morning_snack:
                morning_snack=st.selectbox(f'Choose your morning_snack:',[recipe['Name'] for recipe in recommendations[1]])
            with launch_column:
                launch_choice=st.selectbox(f'Choose your launch:',[recipe['Name'] for recipe in recommendations[2]])
            with afternoon_snack:
                afternoon_snack=st.selectbox(f'Choose your afternoon:',[recipe['Name'] for recipe in recommendations[3]])
            with dinner_column:
                dinner_choice=st.selectbox(f'Choose your  dinner:',[recipe['Name'] for recipe in recommendations[4]])
            choices=[breakfast_choice,morning_snack,launch_choice,afternoon_snack,dinner_choice] 
        
        # Calculating the sum of nutritional values of the choosen recipes
        total_nutrition_values={nutrition_value:0 for nutrition_value in nutritions_values}
        for choice,meals_ in zip(choices,recommendations):
            for meal in meals_:
                if meal['Name']==choice:
                    for nutrition_value in nutritions_values:
                        total_nutrition_values[nutrition_value]+=meal[nutrition_value]
  
        total_calories_chose=total_nutrition_values['Calories']
        loss_calories_chose=round(person.calories_calculator()*person.weight_loss)

        # Display corresponding graphs
        st.markdown(f'<h5 style="text-align: center;font-family:sans-serif;">Total Calories in Recipes vs {st.session_state.weight_loss_option} Calories (kcal):</h5>', unsafe_allow_html=True)
        total_calories_graph_options = {
    "xAxis": {
        "type": "category",
        "data": ['Total Calories you chose', f"{st.session_state.weight_loss_option} Calories"],
    },
    "yAxis": {"type": "value"},
    "series": [
        {
            "data": [
                {"value":total_calories_chose, "itemStyle": {"color":["#33FF8D","#FF3333"][total_calories_chose>loss_calories_chose]}},
                {"value": loss_calories_chose, "itemStyle": {"color": "#3339FF"}},
            ],
            "type": "bar",
        }
    ],
}
        st_echarts(options=total_calories_graph_options,height="400px",)
        st.markdown(f'<h5 style="text-align: center;font-family:sans-serif;">Nutritional Values:</h5>', unsafe_allow_html=True)
        nutritions_graph_options = {
    "tooltip": {"trigger": "item"},
    "legend": {"top": "5%", "left": "center"},
    "series": [
        {
            "name": "Nutritional Values",
            "type": "pie",
            "radius": ["40%", "70%"],
            "avoidLabelOverlap": False,
            "itemStyle": {
                "borderRadius": 10,
                "borderColor": "#fff",
                "borderWidth": 2,
            },
            "label": {"show": False, "position": "center"},
            "emphasis": {
                "label": {"show": True, "fontSize": "40", "fontWeight": "bold"}
            },
            "labelLine": {"show": False},
            "data": [{"value":round(total_nutrition_values[total_nutrition_value]),"name":total_nutrition_value} for total_nutrition_value in total_nutrition_values],
        }
    ],
}       
        st_echarts(options=nutritions_graph_options, height="500px",)
        

display=Display()
title="<h1 style='text-align: center;'>Automatic Diet Recommendation</h1>"
st.markdown(title, unsafe_allow_html=True)
with st.form("recommendation_form"):
    st.write("Modify the values and click the Generate button to use")
    age = st.number_input('Age',min_value=2, max_value=120, step=1)
    height = st.number_input('Height(cm)',min_value=50, max_value=300, step=1)
    weight = st.number_input('Weight(kg)',min_value=10, max_value=300, step=1)
    gender = st.radio('Gender',('Male','Female'))
    activity = st.select_slider('Activity',options=['Little/no exercise', 'Light exercise', 'Moderate exercise (3-5 days/wk)', 'Very active (6-7 days/wk)', 
    'Extra active (very active & physical job)'])
    option = st.selectbox('Choose your weight loss plan:',display.plans)
    st.session_state.weight_loss_option=option
    weight_loss=display.weights[display.plans.index(option)]
    number_of_meals=st.slider('Meals per day',min_value=3,max_value=5,step=1,value=3)
    if number_of_meals==3:
        meals_calories_perc={'breakfast':0.35,'lunch':0.40,'dinner':0.25}
    elif number_of_meals==4:
        meals_calories_perc={'breakfast':0.30,'morning snack':0.05,'lunch':0.40,'dinner':0.25}
    else:
        meals_calories_perc={'breakfast':0.30,'morning snack':0.05,'lunch':0.40,'afternoon snack':0.05,'dinner':0.20}
    
    st.markdown("---")
    st.markdown("### 💰 Daily Budget Limit (Required)")
    st.markdown("*Set your daily meal budget to get cost-effective recommendations*")
    budget_limit = st.number_input('Daily budget (USD)', min_value=5.0, max_value=200.0, step=5.0, format="%.2f")
    st.caption(f"✓ Budget per meal: ~${budget_limit/number_of_meals:.2f}")
    st.session_state.budget_limit = budget_limit
    
    generated = st.form_submit_button("Generate")
if generated:
    # Validate budget is set (min is 5.0, so anything >= 5.0 is valid)
    if budget_limit is None or budget_limit < 5.0:
        st.error("❌ Please enter a daily budget amount (minimum $5.00) before generating recommendations.")
        st.session_state.generated = False
        st.stop()
    
    person = Person(age,height,weight,gender,activity,meals_calories_perc,weight_loss,budget_limit)
    with st.container():
        display.display_bmi(person)
    with st.container():
        display.display_calories(person)
    with st.spinner('Generating recommendations...'):     
        recommendations=person.generate_recommendations()
        st.session_state.diet_recommendations=recommendations
        st.session_state.person=person
        st.session_state.generated=True

if st.session_state.generated and st.session_state.person is not None:
    with st.container():
        display.display_recommendation(st.session_state.person,st.session_state.diet_recommendations)
        st.success('Recommendation Generated Successfully !', icon="✅")
    with st.container():
        display.display_meal_choices(st.session_state.person,st.session_state.diet_recommendations)
    
    # Format recommendations as context for chatbot
    def format_recipes_for_context(recommendations):
        if not recommendations or not isinstance(recommendations, list) or not st.session_state.person:
            return "No recommendations available."
        lines = []
        meal_names = list(st.session_state.person.meals_calories_perc.keys())
        for meal_idx, (meal_name, meal_recipes) in enumerate(zip(meal_names, recommendations)):
            lines.append(f"\n{meal_name.upper()}:")
            for recipe in meal_recipes:
                # Skip if recipe is not a dictionary
                if not isinstance(recipe, dict):
                    continue
                recipe_name = recipe.get('Name', f'Recipe {meal_idx+1}')
                ingredients = ', '.join(recipe.get('RecipeIngredientParts', [])[:5])  # First 5 ingredients
                calories = recipe.get('Calories', 'N/A')
                protein = recipe.get('ProteinContent', 'N/A')
                lines.append(f"  - {recipe_name} (Calories: {calories}, Protein: {protein}g)")
                lines.append(f"    Main ingredients: {ingredients}")
        return '\n'.join(lines)
    
    # Store context if recommendations exist and are valid
    if st.session_state.diet_recommendations and isinstance(st.session_state.diet_recommendations, list) and st.session_state.person:
        st.session_state.diet_recipes_context = format_recipes_for_context(st.session_state.diet_recommendations)
    
    # Shopping List Section
    st.markdown("---")
    st.markdown("### 🛒 Shopping List")
    st.markdown("*Get your consolidated grocery list for all recommended meals*")
    
    if st.button("Generate Shopping List", type="primary"):
        with st.spinner("📝 Creating your shopping list..."):
            # Flatten all recipes from all meals
            all_recipes = []
            for meal_recipes in st.session_state.diet_recommendations:
                all_recipes.extend(meal_recipes)
            
            # Generate shopping list
            shopping_list = generate_shopping_list(all_recipes)
            shopping_list_md = format_shopping_list_markdown(shopping_list)
            
            # Display
            st.markdown(shopping_list_md)
            
            # Estimate cost
            estimated_cost = estimate_shopping_cost(shopping_list)
            
            # Show budget status
            if st.session_state.budget_limit:
                budget_diff = st.session_state.budget_limit - estimated_cost
                if budget_diff >= 0:
                    st.success(f"💰 Estimated Cost: \${estimated_cost:.2f} USD")
                    st.caption(f"✅ Within Budget (\${budget_diff:.2f} remaining)")
                else:
                    st.warning(f"💰 Estimated Cost: \${estimated_cost:.2f} USD")
                    st.caption(f"⚠️ Over Budget by \${abs(budget_diff):.2f}")
                    st.caption("*Consider choosing less expensive recipe alternatives*")
            else:
                st.info(f"💰 Estimated Cost: \${estimated_cost:.2f} USD")
            
            st.caption("*Cost estimates are approximate and may vary by location and brand*")
            
            # Download button
            st.download_button(
                label="📥 Download Shopping List",
                data=shopping_list_md,
                file_name="shopping_list.md",
                mime="text/markdown"
            )
    
    
    # Chat UI Section
    st.markdown("---")
    st.markdown("### 💬 Ask the Diet Assistant")
    
    st.markdown("*Have questions about your recommendations? Ask about ingredient substitutions, alternatives, or cooking tips!*")
    
    
    # Display chat history
    if st.session_state.diet_chat_history:
        st.markdown("### Conversation:")
        for role, text in st.session_state.diet_chat_history:
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
            placeholder="e.g., Can I substitute chicken with tofu?",
            key="chat_input"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing
        ask_button = st.button("Ask")
    
    if ask_button and user_question:
        # Append user message
        st.session_state.diet_chat_history.append(("user", user_question))
        
        # Build history text
        history_text = ""
        for role, text in st.session_state.diet_chat_history:
            prefix = "User" if role == "user" else "Assistant"
            history_text += f"{prefix}: {text}\n"
        
        # Get context from session
        context_text = st.session_state.get("diet_recipes_context", "No recipes context available.")
        
        # Generate answer
        with st.spinner("🤔 Thinking..."):
            answer = generate_chat_answer(context_text, history_text, user_question)
        
        # Append assistant answer
        st.session_state.diet_chat_history.append(("assistant", answer))
        
        # Set flag to clear input on next run
        st.session_state.clear_input = True
        
        # Rerun to refresh the chat display
        st.rerun()
    
    # Clear chat button
    if st.session_state.diet_chat_history:
        if st.button("Clear Chat History"):
            st.session_state.diet_chat_history = []
            st.rerun()
