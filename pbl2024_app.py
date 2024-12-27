# STREAMLIT APP CODE

# Import libraries
import streamlit as st

# Set up the app title
st.title("Simple Streamlit App")

# Add a description
st.write("Enter a text prompt below and see the output!")

# Input box for user prompt
user_prompt = st.text_input("Enter your prompt:")

# Button to generate a response
if st.button("Generate Response"):
    if user_prompt:
        # Simulate a generated response
        generated_response = f"You entered: {user_prompt}"
        st.success("Response generated successfully!")
        st.write("Generated Response:")
        st.write(generated_response)
    else:
        st.warning("Please enter a prompt before clicking the button.")

# Add a footer
st.write("---")
st.write("Powered by Streamlit")
