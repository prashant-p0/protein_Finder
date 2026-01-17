import streamlit as st
import database as db
import os
import google.generativeai as genai
from dotenv import find_dotenv, load_dotenv
import re
from PIL import Image

db.init_db()

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

st.set_page_config("AI Protein Finder",page_icon="🤖")
st.title("🤖 AI Protein Finder 🤖")
st.write("Ask about any food, meal, or ingredient.")

#user Input 

if 'daily_protein' not in st.session_state:
    st.session_state.daily_protein = 0.0
if 'daily_carbs' not in st.session_state:
    st.session_state.daily_carbs = 0.0
if 'daily_fats' not in st.session_state:
    st.session_state.daily_fats = 0.0

# --- SIDEBAR: PROFILE & PROGRESS ---
with st.sidebar:
    st.header("👤 Your Profile")
    weight = st.number_input("Weight (kg)", 30, 200, 75)
    height = st.number_input("Height (cm)", 100, 250, 175)
    age = st.number_input("Age", 10, 100, 25)
    
    # Calculate Targets (Simple Science-based formula)
    protein_goal = weight * 1.8  # 1.8g per kg
    carb_goal = weight * 3.0     # 3.0g per kg
    fat_goal = weight * 0.8      # 0.8g per kg

    st.markdown("---")
    st.header("📈 Daily Progress")
    
    # Progress Bars in Sidebar
    st.write(f"Protein: {st.session_state.daily_protein:.1f} / {protein_goal:.0f}g")
    st.progress(min(st.session_state.daily_protein / protein_goal, 1.0))
    
    st.write(f"Carbs: {st.session_state.daily_carbs:.1f} / {carb_goal:.0f}g")
    st.progress(min(st.session_state.daily_carbs / carb_goal, 1.0))

    st.write(f"Fats: {st.session_state.daily_fats:.1f} / {fat_goal:.0f}g")
    st.progress(min(st.session_state.daily_fats / fat_goal, 1.0))
    
    if st.button("Reset Daily Progress"):
        st.session_state.daily_protein = 0.0
        st.session_state.daily_carbs = 0.0
        st.session_state.daily_fats = 0.0
        st.rerun()

# --- MAIN AREA: SEARCH ---
st.title("🥗 AI Image & Text Nutritionist")
st.write("Upload a photo of your food or type the description below.")

col_in1, col_in2 = st.columns(2)

with col_in1:
    uploaded_file = st.file_uploader("📸 Take a photo or upload", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Analyze this meal", use_container_width=True)

with col_in2:
    text_query = st.text_area("✍️ Or describe your meal:", placeholder="e.g. 2 eggs, 1 slice of whole wheat toast, and half an avocado")

if st.button("🔍 Analyze Meal & Update Log"):
    if not uploaded_file and not text_query:
        st.warning("Please provide either a photo or a text description.")
    else:
        with st.spinner('AI is analyzing your meal...'):
            # Prepare contents for Gemini
            contents = []
            if uploaded_file:
                contents.append(Image.open(uploaded_file))
            
            user_input = text_query if text_query else "the food in the image"
            
            prompt = f"""
            Analyze this food: {user_input}. 
            Provide the nutritional estimate in this EXACT format:
            PROTEIN: [number]
            CARBS: [number]
            FATS: [number]
            ADVICE: [One short sentence of nutritional advice]
            """
            contents.append(prompt)

    with st.spinner('Analyzing...'):
        response = model.generate_content(prompt)
        text = response.text

        try:
            # Extract numbers
            p = float(re.search(r"PROTEIN:\s*([\d.]+)", text).group(1))
            c = float(re.search(r"CARBS:\s*([\d.]+)", text).group(1))
            f = float(re.search(r"FATS:\s*([\d.]+)", text).group(1))
            advice = re.search(r"ADVICE:\s*(.*)", text).group(1)

            # Update Session State (The progress bars will update instantly)
            st.session_state.daily_protein += p
            st.session_state.daily_carbs += c
            st.session_state.daily_fats += f

            # Show results in columns
            st.success(f"Added {text_query} to your daily log!")
            col1, col2, col3 = st.columns(3)
            col1.metric("Protein", f"+{p}g")
            col2.metric("Carbs", f"+{c}g")
            col3.metric("Fats", f"+{f}g")
            st.info(f"💡 {advice}")
            
            # This triggers a rerun to update the sidebar progress bars
            st.rerun()
            db.save_meal(user_input, p, c, f)
            st.success("Meal saved to history!")

        except Exception:
            st.error("AI returned unexpected format. Try again with a simpler food name.")

        


st.caption("Note: AI provides estimates based on general data. For clinical accuracy, consult a lab-tested database.")