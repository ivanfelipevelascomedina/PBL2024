# **Educational Video Generation Tool**

## **Overview**
This tool generates AI-driven videos using prompts and visual descriptions provided by the user. It integrates multiple APIs like **OpenAI**, **ResembleAI**, and **Luma AI** for video generation and ensures session persistence to allow seamless iterative usage. The generated videos are concatenated and combined with narration to create a cohesive final output.

---

## **Files**
- **`Packages.txt`**: Contains necessary packages.
- **`Requisites.txt`**: Lists necessary libraries.
- **`PBL2024.py`**: Main code file.
- **`bollywoodkollywood-sad-love-bgm-13349`**: Background music for videos (can be changed if necessary).

---

## **Features**
- Fetches contextual data (e.g., news or academic papers) to enrich video prompts.
- Generates videos scene-by-scene using **Luma AI**.
- Combines video segments and narrations into a single output.
- Handles errors with retry mechanisms.
- Session persistence ensures iterative processes retain prior results.
- Displays the results with a **Streamlit-based GUI**.

---

## **Troubleshooting**
### **Error: "Generation failed"**
- Ensure the prompt adheres to **Luma AI's input guidelines** and is not overly complex.  
- Check API quotas and retry if necessary.

### **Error: "No files to concatenate"**
- Verify that video generation steps completed successfully.  
- Retry or simplify the prompts.

### **"Dreaming" message in logs**
- Indicates the tool is waiting for the **Luma AI** generation to complete.  
- If this persists, check network stability or retry later.

### **Missing API keys**
- Ensure all required API keys are entered in the sidebar.

---

## **Customization**
- **Modify Prompts**: Update prompt templates to tailor the visual and narrative style.
- **Add Features**: Extend the app by integrating additional APIs or functionalities.
- **Styling**: Customize **Streamlit UI** components to enhance user experience.

---

## **Acknowledgments**
- **Luma AI** for advanced video generation.
- **OpenAI** for contextual script creation.
- **Resemble AI** for voice narration.
