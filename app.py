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
   # age = st.number_input("Age", 10, 100, 25)

    activity = st.select_slider("Activity Level",["Sedentary", "Lightly Active", "Moderately Active", "Very Active", "Athlete"])
    
    protein_factors = {"Sedentary": 0.8, "Lightly Active": 1.0, "Moderately Active": 1.2, "Very Active": 1.6, "Athlete": 2.0}
    carb_factors = {"Sedentary": 3.0, "Lightly Active": 4.0, "Moderately Active": 5.5, "Very Active": 7.0, "Athlete": 9.0} 
    fat_factors = {"Sedentary": 0.8, "Lightly Active": 1.0, "Moderately Active": 1.2, "Very Active": 1.4, "Athlete": 1.6}
     
     # Get selected factors 
    p_factor = protein_factors[activity] 
    c_factor = carb_factors[activity] 
    f_factor = fat_factors[activity] 
    
    # Formulas 
    protein = weight * p_factor + height/100 
    carbs = weight * c_factor + height/150 
    fats = weight * f_factor + height/200

    st.markdown("---")
    st.header("📈 Daily Intake Required as per you Profile")
    
    # Progress Bars in Sidebar
    st.write(f"Protein:  {protein:.0f}g")
    #st.progress(min(st.session_state.daily_protein / protein_goal, 1.0))
    
    st.write(f"Carbs:  {carbs:.0f}g")
    #st.progress(min(st.session_state.daily_carbs / carb_goal, 1.0))

    st.write(f"Fats:  {fats:.0f}g")
    #st.progress(min(st.session_state.daily_fats / fat_goal, 1.0))
    
    

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

if 'last_result' not in st.session_state:
    st.session_state.last_result = None

if st.button("🔍 Analyze Meal & Update Log"):
    if not uploaded_file and not text_query:
        st.warning("Please provide either a photo or a text description.")
    else:
        
        p, c, f, advice, food_name, source_tag =  0.0, 0.0, 0.0, 0.0,"", ""
        
        cached_data = db.check_cache(text_query) if (text_query and not uploaded_file) else None
        
        if cached_data:
            p,c,f,advice = cached_data
            food_name = text_query
            source_tag = " Local Cache"
            st.write(f"DEBUG: Data from DB: {cached_data}")
        else:
            
            source_tag = " AI Analysis"
            with st.spinner('AI is analyzing your meal...'):
                # Prepare contents for Gemini
                contents = []
                if uploaded_file:
                    contents.append(Image.open(uploaded_file))
                
                user_input = text_query if text_query else "the food in the image"
                
                prompt = f""" 
                Analyze this food: {user_input}.
                Return ONLY the following labels and values. Do not include introductory text.
                NAME: [Brief name of food]
                PROTEIN: [number only]
                CARBS: [number only]
                FATS: [number only]
                ADVICE: [One short coaching tip]
                """
                contents.append(prompt)
                response = model.generate_content(contents)
                res_text = response.text

                name_match = re.search(r"NAME:\s*(.*)", res_text, re.I)
                p_match = re.search(r"PROTEIN:\s*([\d.]+)", res_text, re.I)
                c_match = re.search(r"CARBS:\s*([\d.]+)", res_text, re.I)
                f_match = re.search(r"FATS:\s*([\d.]+)", res_text, re.I)
                advice_match = re.search(r"ADVICE:\s*(.*)", res_text, re.I)

                food_name = name_match.group(1) if name_match else "Unknown Food"
                p = float(p_match.group(1)) if p_match else 0.0
                c = float(c_match.group(1)) if c_match else 0.0
                f = float(f_match.group(1)) if f_match else 0.0
                advice = advice_match.group(1) if advice_match else "Stay healthy!"
                
                db.save_meal(food_name, p, c, f, advice)

        st.session_state.last_result = {
                "food": food_name,
                "p": p, "c": c, "f": f,
                "advice": advice,
                "source": source_tag
            }
        st.rerun()       

if st.session_state.last_result:
    res = st.session_state.last_result
    
    st.divider()
    # Display the Source Tag
    st.write(f"**Source:** `{res['source']}`")
    
    st.subheader(f"🍽️ {res['food'].title()}")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("🍗 Protein", f"{res['p']}g")
    col2.metric("🍞 Carbs", f"{res['c']}g")
    col3.metric("🥑 Fats", f"{res['f']}g")

    st.markdown(f"""
        <div style="background-color:#f0f7ff; padding:15px; border-radius:10px; border-left: 5px solid #2196f3; margin-top:10px;">
            <span style="color:#01579b; font-weight:bold;">🤖 AI Coach Advice:</span><br>
            <span style="color:#01579b;">{res['advice']}</span>
        </div>
    """, unsafe_allow_html=True)

    st.write("")


st.caption("Note: AI provides estimates based on general data. For clinical accuracy, consult a lab-tested database.")