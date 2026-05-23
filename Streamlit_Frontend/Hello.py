import streamlit as st

st.set_page_config(
    page_title="Diet Recommendation System",
    page_icon="🥗",
    layout="wide"
)

# Main Title
st.title("🥗 Diet Recommendation System")
st.markdown("""
<div style='text-align: center; margin-bottom: 2rem;'>
    <p style='font-size: 1.3rem; color: #a0aec0;'>
        Your AI-Powered Nutrition Companion
    </p>
</div>
""", unsafe_allow_html=True)

# Feature Cards
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div style='background: white; padding: 2rem; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.07); text-align: center; height: 280px;'>
        <div style='font-size: 3rem; margin-bottom: 1rem;'>💪</div>
        <h3 style='color: #667eea; margin-bottom: 1rem;'>Personalized Plans</h3>
        <p style='color: #6c757d;'>Get customized diet recommendations based on your age, weight, height, activity level, and health goals.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style='background: white; padding: 2rem; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.07); text-align: center; height: 280px;'>
        <div style='font-size: 3rem; margin-bottom: 1rem;'>🔍</div>
        <h3 style='color: #667eea; margin-bottom: 1rem;'>Custom Search</h3>
        <p style='color: #6c757d;'>Find recipes tailored to your specific nutritional needs and ingredient preferences with our smart search.</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div style='background: white; padding: 2rem; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.07); text-align: center; height: 280px;'>
        <div style='font-size: 3rem; margin-bottom: 1rem;'>🍽️</div>
        <h3 style='color: #667eea; margin-bottom: 1rem;'>Meal Planning</h3>
        <p style='color: #6c757d;'>Create complete weekly meal plans with shopping lists and budget tracking for stress-free meal prep.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# How it works section
st.markdown("""
<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 20px; margin: 2rem 0;'>
    <h2 style='color: white; text-align: center; margin-bottom: 1.5rem;'>How It Works</h2>
    <div style='color: white; font-size: 1.1rem;'>
        <p>✨ <strong>Smart Algorithm:</strong> Uses content-based filtering with scikit-learn to match recipes to your needs</p>
        <p>🎯 <strong>500,000+ Recipes:</strong> Access to a vast database from Food.com with detailed nutritional information</p>
        <p>💰 <strong>Budget Friendly:</strong> Filter recipes by cost and get estimated shopping expenses</p>
        <p>🤖 <strong>AI Assistant:</strong> Get instant answers to your nutrition questions (optional)</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Getting Started
st.markdown("### 🚀 Getting Started")
st.markdown("""
1. **Choose a tool** from the sidebar:
   - 💪 **Diet Recommendation** - For personalized daily meal plans
   - 🔍 **Custom Food Recommendation** - For specific recipe searches
   - 🍽️ **Meal Planner** - For weekly meal planning

2. **Enter your information** - Provide your details and preferences

3. **Get recommendations** - Receive tailored recipe suggestions instantly

4. **Enjoy healthy eating!** - Follow your personalized plan
""")

# Sidebar
st.sidebar.markdown("""
<div style='text-align: center; padding: 1rem;'>
    <h3 style='color: white;'>Navigation</h3>
    <p style='color: rgba(255,255,255,0.8);'>Select a tool to get started</p>
</div>
""", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #6c757d; padding: 1rem;'>
    <p>Built with ❤️ using Streamlit, FastAPI, and Scikit-Learn</p>
    <p style='font-size: 0.9rem;'>A content-based recommendation system for healthy eating</p>
</div>
""", unsafe_allow_html=True)
