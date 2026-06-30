"""
Google Gemini AI service for generating flood damage assessment reports.
"""

import os
from google import genai
from google.genai import types
from PIL import Image
from src import config


def generate_flood_report(stats, coords, dates, image_path):
    """
    Generate an executive-level flood damage assessment report using Gemini AI.
    """
    try:
        if not config.GEMINI_API_KEY:
            return "Error: AI Report unavailable. GEMINI_API_KEY missing in environment."
        
        if not os.path.exists(image_path):
            return "Error: AI Report unavailable. Flood image overlay not found."
        
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        
        # Extract statistics
        baseline_date = dates.get('baseline', 'Unknown Baseline')
        latest_date = dates.get('latest', 'Unknown Date')
        base_sq = stats.get('baseline_sq_km', 0.0)
        curr_sq = stats.get('current_sq_km', 0.0)
        flood_sq = stats.get('flood_sq_km', 0.0)
        
        # Build comprehensive prompt
        prompt = f"""          
You are a Lead Geospatial Intelligence Analyst generating an executive-level Flood Damage and Loss Assessment (DaLA) report. 
I have provided a satellite image overlay. The red pixels definitively indicate algorithmic detections of newly accumulated floodwater.          

CONTEXTUAL TELEMETRY:          
- Bounding Box Coordinates: {coords}          
- Baseline Imagery Date: {baseline_date}
- Post-Flood Capture Date: {latest_date}          
- Pre-flood Water Extent: {base_sq:.2f} sq km          
- Current Total Water Extent: {curr_sq:.2f} sq km          
- Net New Inundation Area: {flood_sq:.2f} sq km          

YOUR DIRECTIVES:
1. Be Authoritative: Eliminate all speculative language (e.g., do not use "likely," "suggests," or "possibly"). Make definitive statements based on the visual evidence and telemetry provided. If a factor is indistinguishable, state that it cannot be determined at this resolution rather than guessing.
2. Be Analytical: Do not just read the numbers back. Calculate the percentage increase in water extent and explain what that scale of increase means for the terrain visible in the image.
3. Be Plain Text: You must output strictly in plain text. DO NOT use markdown formatting, asterisks, hashes, bolding, or special characters. Use standard ALL CAPS for your headers.

REQUIRED REPORT STRUCTURE:
EXECUTIVE SUMMARY
Provide a bottom-line-up-front (BLUF) statement summarizing the severity and scale of the inundation event.

GEOSPATIAL & CLIMATOLOGICAL CONTEXT
Identify the specific region in Pakistan based on the coordinates. Correlate the capture dates with known seasonal weather patterns (e.g., monsoon cycles or glacial melt) to establish the primary driver of the event.

INUNDATION METRICS & MORPHOLOGY
Analyze the quantitative data. Describe the morphological spread of the floodwaters (e.g., riverine overspill, pooling in low-lying plains, or flash flood patterns) based strictly on the shape and distribution of the red overlay.

INFRASTRUCTURE & SOCIO-ECONOMIC IMPACT
Examine the base imagery beneath the flood mask. Definitively state the types of terrain affected (e.g., cultivated agricultural plots, dense urban grids, rural transit corridors). Outline the immediate operational impacts on these specific sectors.

MODEL CONFIDENCE & FALSE POSITIVE ANALYSIS
Critically evaluate the segmentation mask. Identify specific areas in the image where the model may have misclassified topographical shadows, dense cloud shadows, or highly reflective urban surfaces as water. 

STRATEGIC DIRECTIVES
Provide 3 highly specific, actionable recommendations for on-the-ground disaster response agencies based on the exact terrain and impact identified above.
"""  
        
        # Load image for multimodal input
        with Image.open(image_path) as img:
            config_obj = types.GenerateContentConfig(
                temperature=config.GEMINI_TEMPERATURE,
                top_p=config.GEMINI_TOP_P,
            )
            
            response = client.models.generate_content(
                model=config.GEMINI_MODEL_ID,
                contents=[img, prompt],
                config=config_obj
            )
            
            if response.text:
                return response.text.strip()
            else:
                return "Error: Model returned an empty response."
    
    except Exception as e:
        import traceback
        print(f"❌ AI Report Error: {e}\n{traceback.format_exc()}", flush=True)
        return "Error: AI Report generation failed due to an internal system error."