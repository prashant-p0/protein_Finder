import streamlit as st
import database as db
import os
import google.generativeai as genai
from dotenv import find_dotenv, load_dotenv
import re
from PIL import Image
import rag_engin as rag



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
if 'last_result' not in st.session_state:
    st.session_state.last_result = None
if 'kb_result' not in st.session_state:
    st.session_state.kb_result = None

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
#st.title("🥗 AI Image & Text Nutritionist")
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


st.write("")
btn_col1, btn_col2 = st.columns(2)

with btn_col1:
    analyze_clicked = st.button("🔍 Analyze Meal & Log", use_container_width=True)

with btn_col2:
    kb_clicked = st.button("📚 Search Science KB", use_container_width=True)

# --- BUTTON LOGIC ---

# 1. Analyze Meal Logic
if analyze_clicked:
    st.session_state.kb_result = None # Clear KB result when analyzing meal
    if not uploaded_file and not text_query:
        st.warning("Please provide a photo or text description.")
    else:
        cached_data = db.check_cache(text_query) if (text_query and not uploaded_file) else None
        
        if cached_data:
            p, c, f, advice = cached_data
            st.session_state.last_result = {
                "food": text_query, "p": p, "c": c, "f": f, "advice": advice, "source": "Local Cache"
            }
        else:
            with st.spinner('AI analyzing...'):
                contents = [Image.open(uploaded_file)] if uploaded_file else []
                user_input = text_query if text_query else "the food in the image"
                prompt = f"""Analyze food: {user_input}. Return ONLY: NAME: [name], PROTEIN: [num], CARBS: [num], FATS: [num], ADVICE: [tip]"""
                contents.append(prompt)
                
                response = model.generate_content(contents)
                res_text = response.text

                # Regex parsing
                n_m = re.search(r"NAME:\s*(.*)", res_text, re.I)
                p_m = re.search(r"PROTEIN:\s*([\d.]+)", res_text, re.I)
                c_m = re.search(r"CARBS:\s*([\d.]+)", res_text, re.I)
                f_m = re.search(r"FATS:\s*([\d.]+)", res_text, re.I)
                a_m = re.search(r"ADVICE:\s*(.*)", res_text, re.I)

                food_name = n_m.group(1) if n_m else "Unknown"
                p, c, f = float(p_m.group(1)) if p_m else 0.0, float(c_m.group(1)) if c_m else 0.0, float(f_m.group(1)) if f_m else 0.0
                advice = a_m.group(1) if a_m else "Eat well!"
                
                db.save_meal(food_name, p, c, f, advice)
                st.session_state.last_result = {
                    "food": food_name, "p": p, "c": c, "f": f, "advice": advice, "source": "AI Analysis"
                }
        st.rerun()

# 2. Knowledge Base Logic
if kb_clicked:
    st.session_state.last_result = None # Clear meal result when searching KB
    if not text_query:
        st.warning("Please type a question in the text area to search the Knowledge Base.")
    else:
        with st.spinner('Searching Scientific PDFs...'):
            answer = rag.ask_rag_assistant(text_query)
            st.session_state.kb_result = answer
        st.rerun()

# --- DISPLAY RESULTS ---

# Display Meal Analysis
if st.session_state.last_result:
    res = st.session_state.last_result
    st.divider()
    st.write(f"**Source:** `{res['source']}`")
    st.subheader(f"🍽️ {res['food'].title()}")
    m1, m2, m3 = st.columns(3)
    m1.metric("🍗 Protein", f"{res['p']}g")
    m2.metric("🍞 Carbs", f"{res['c']}g")
    m3.metric("🥑 Fats", f"{res['f']}g")
    st.info(f"**AI Coach:** {res['advice']}")

# Display KB Search
if st.session_state.kb_result:
    st.divider()
    st.markdown(f"""
        <div style="background-color:#e8f5e9; padding:20px; border-radius:10px; border-left: 8px solid #4caf50;">
            <h3 style="color:#2e7d32; margin-top:0;">🔬 Scientific KB Result</h3>
            <p style="color:#1b5e20; font-size:1.1em;">{st.session_state.kb_result}</p>
        </div>
    """, unsafe_allow_html=True)

st.divider()
st.caption("AI estimates for educational purposes. Run 'ingest.py' to update Knowledge Base.")