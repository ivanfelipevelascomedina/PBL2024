# GUI CODE

# IMPORT LIBRARIES
import csv
from scholarly import scholarly
import feedparser
import urllib.parse
from openai import OpenAI
import requests
import time
import os
import re
import random
from lumaai import LumaAI
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
from resemble import Resemble
from pydub import AudioSegment
import streamlit as st

# INITIALIZE API KEYS

# API Keys Setup
st.sidebar.header("API Keys")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password")
resemble_key = st.sidebar.text_input("Resemble API Key", type="password")
lumaai_key = st.sidebar.text_input("LumaAI API Key", type="password")
google_api_key = st.sidebar.text_input("Google API Key", type="password")
google_cse_id = st.sidebar.text_input("Google Custom Search Engine ID")

# Initialize APIs if keys are provided
if openai_key:
    from openai import OpenAI
    client = OpenAI(api_key=openai_key)
else:
    st.error("Please provide your OpenAI API key.")

if resemble_key:
    from resemble import Resemble
    Resemble.api_key(resemble_key)
else:
    st.error("Please provide your Resemble API key.")

if lumaai_key:
    from lumaai import LumaAI
    client_luma = LumaAI(auth_token=lumaai_key)
else:
    st.error("Please provide your LumaAI API key.")

if google_api_key and google_cse_id:
    api_key = google_api_key
    cse_id = google_cse_id
else:
    st.error("Please provide both the Google API key and CSE ID.")

# DEFINE FUNCTIONS TO USE

# Function to fetch news articles
def fetch_news(query, num_needed=10):
    base_url = "https://news.google.com/rss/search?q=" # We check in google news topics related to the user's input to assure the summary has updated information
    encoded_query = urllib.parse.quote(query)
    feed = feedparser.parse(base_url + encoded_query)
    entries = feed.entries[:num_needed]

    results = []
    for entry in entries:
        results.append({
            "Title": entry.title, # News title
            "Summary": entry.summary, #News summary (not working yet, we should remove it or improve it)
            "Source": entry.source.get("title", "N/A") if "source" in entry else "N/A", # News source
            "Published": entry.published if "published" in entry else "N/A", # News publishing date
            "Link": entry.link, # News link, chat GPT4 has access to internet, so it should be able to access it if necessary
        })
    return results

# Function to fetch academic papers
def fetch_papers(query, num_needed):
    search_query = scholarly.search_pubs(query) # We check in google scholar topics related to the user's input to assure the summary has updated information
    results = []
    num_checked = 0

    while len(results) < num_needed: # We create a loop to fetch as many entries as the user decide to give a context as broad as the user wants to GPT of what the academic community think about the given topic
        try:
            publication = next(search_query)
            num_checked += 1
            num_citations = publication.get("num_citations", 0)

            if num_citations >= 100: # We fetch only papers with more than 100 citations to assure that the information given to ChatGPT is relevant enough to create a coherent context
                results.append({
                    "Title": publication.get("bib", {}).get("title", "N/A"), # Paper title
                    "Authors": ", ".join(publication.get("bib", {}).get("author", ["N/A"])), # Paper authors
                    "Abstract": publication.get("bib", {}).get("abstract", "N/A"), # Paper abstract (working only in some cases)
                    "Year": publication.get("bib", {}).get("pub_year", "N/A"), # Paper publication year
                    "Citations": num_citations, # Paper number of citations
                    "Link": publication.get("pub_url", "N/A"), # Paper link, chat GPT4 has access to internet, so it should be able to access it if necessary
                    "PDF Link": publication.get("eprint_url", "N/A"), # Paper pdf link, chat GPT4 has access to internet, so it should be able to access it if necessary
                })
                #time.sleep(5) # We add a delay to avoid anti-scraping mechanisms from Google scholar
        except StopIteration:
            
            break
        except Exception as e:
            
            continue

    st.write(f"\nChecked {num_checked} papers to find {len(results)} that meet the criteria.")
    return results

# Function to save results to CSV to provide context to GPT in the input
def save_to_csv(results, file_name):
    if not results:
        st.write("No results to save.")
        return

    keys = results[0].keys()
    with open(file_name, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)
    st.write(f"Results saved to {file_name}")
    st.download_button(
        label="Download Results",
        data=open(file_name, "rb").read(),
        file_name=file_name,
        mime="text/csv"
    )


# Function to generate GPT-based summary
def generate_summary(context, query, number_of_scenes=10, word_limit=500):
    prompt = (
        f"You are a scriptwriter tasked with creating a narrated video script. The video will educate viewers about '{query}'. "
        f"Use the provided context below to create a series of {number_of_scenes} scenes with descriptive visuals and accompanying narration according following instructions: "
        f"Convert into prompts suitable for video-generation AI."
        f"Describe the subject, setting, and elements in detail."
        f"Specify visual details such as colors, shapes, and textures."
        f"Clearly express the overall emotion or mood."
        f"Use simple and direct language."
        f"Provide instructions for camera movements (zoom, pan, tilt, etc.)."
        f"Describe the movements of objects or characters in detail."
        f"Specify the key features of important objects."
        f"Depict environmental elements such as background, time of day, and weather."
        f"Ensure that the narration is engaging and provides all relevant details. To do that use the information you can acces and the context I will give you and make sure to stick to a concise format and a word limit of {word_limit} words.\n\n"
        f"Since it is a summarizing video try to include important facts and data that could help the audience get a general idea about the theme, even if to do so you need to exclude part of the context."
        f"### Context (remember this is just a context, you can complement it with your own information if necessary):\n{context}\n\n"
        f"### Output Format:\n"
        f"- Scene [Number]: [description of visuals]\n"
        f"- Narrator [Number]: [Narration content for the scene]\n"
        # f"### Example:\n"
        # f"- Scene 1: Black-and-white footage of Japanese cities during WWII, showing destruction and chaos.\n"
        # f"  Narrator: *\"World War II was a ruthless chapter in Japan's history, marked by severe war crimes committed by both military personnel and civilians. "
        # f"The aftermath of the war left Japan in ruins, facing profound consequences both within and beyond its borders.\"*\n\n"
        # f"Now, generate a narrated video script for '{query}' in the specified format."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a scriptwriter and video producer, skilled at creating narrated video scenes for educational purposes."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error with OpenAI API: {e}")
        return f"Error generating video scenes: {e}"

# Funtion to parse prompts for the video
def parse_prompts_video(summary):
    scene_pattern = r"- Scene \d+: (.+?)\n"
    scenes = re.findall(scene_pattern, summary)
    return scenes

# Function to extract narrator lines
def parse_prompts_voice(summary):
    narrator_pattern = r"- Narrator \d+: (.+?)\n"
    # Ensure the input ends with a newline to assure consistency in narrator audios (if not there is a mismatch between number of scenes and audio since the last narrator is not added)
    if not summary.endswith("\n"):
        summary += "\n"
    narrators = re.findall(narrator_pattern, summary)
    return narrators

# Function to generate voice-over
def generate_voice_segment(prompt):
    response = Resemble.v2.clips.create_sync(project_uuid, voice_uuid, prompt)
    file_name = f"voice_{int(time.time())}.mp3"
    st.write("API Response:", response)
    audio_src = response['item'].get('audio_src')
    if audio_src:
        audio_data = requests.get(audio_src).content
        with open(file_name, 'wb') as f:
            f.write(audio_data)
        return file_name
    else:
        raise ValueError("Failed to generate voice segment")

# Funtion to get images to improve video quality
def get_images(query):
  url = f'https://www.googleapis.com/customsearch/v1?q={query}&cx={cse_id}&searchType=image&key={api_key}'
  response = requests.get(url)
  data = response.json()

  # Display the first image URL from the response
  # image_url = data['items'][random.randint(1, 10)]['link']
  return data['items']

# Funtion to generate video
def generate_video_segment(prompt, number, urls):
  ids = []
  image = urls[random.randint(0, len(urls) - 1)]['link']
  generation = client_luma.generations.create(
    prompt=prompt,
    # duration = 2,
    # keyframes={
    #   "frame0": {
    #     "type": "image",
    #     "url": image
    #   }
    # }
  )
  completed = False
  while not completed:
    generation = client_luma.generations.get(id=generation.id)
    if generation.state == "completed":
      completed = True
    elif generation.state == "failed":
      raise RuntimeError(f"Generation failed: {generation.failure_reason}")
    st.write("Dreaming")
    time.sleep(5)

  ids.append(generation.id)

  while number > 1:
    completed = False
    image = urls[random.randint(0, len(urls) - 1)]['link']
    generation = client_luma.generations.create(
    prompt=prompt,
    keyframes={
      "frame0": {
        "type": "generation",
        "id": ids[len(ids)-1]
      },
      # "frame1": {
      #   "type": "image",
      #   "url": image
      # }
    })
    while not completed:
      generation = client_luma.generations.get(id=generation.id)
      if generation.state == "completed":
        completed = True
      elif generation.state == "failed":
        raise RuntimeError(f"Generation failed: {generation.failure_reason}")
      st.write("Dreaming")
      time.sleep(5)
    number = number - 1
    ids.append(generation.id)
    st.write(ids)

  video_url = generation.assets.video
  # download the video
  response = requests.get(video_url, stream=True)
  filename = f"{generation.id}.mp4"
  with open(filename, 'wb') as file:
      file.write(response.content)
  st.write(f"File downloaded as {generation.id}.mp4")

  st.video(filename)

  return filename

# Funtion to combine voice and video
def combine_segments(video_files, voice_files):
    clips = []
    for video, audio in zip(video_files, voice_files):
        video_clip = VideoFileClip(video)
        audio_clip = AudioFileClip(audio)
        video_clip = video_clip.set_audio(audio_clip)
        clips.append(video_clip)
    combined_video = concatenate_videoclips(clips)
    output_file = "final_video.mp4"
    combined_video.write_videofile(output_file, codec="libx264", audio_codec="aac")
    return output_file

# MAIN CODE

# Main program
def main():
    
    st.title("News and Papers Retrieval Tool")

    prompts = None
    scenes = None
    
    # Input section
    query = st.text_input("Enter your query (e.g., 'World War II in Japan'):", "")
    option = st.radio("Choose data source:", ["news", "papers"])
    num_needed = st.slider("Number of articles/papers to fetch:", 3, 5, 10)
    
    if st.button("Fetch Data"):
        if option == "papers":
            st.write("Fetching academic papers...")
            papers = fetch_papers(query, num_needed)
            save_to_csv(papers, "papers_results.csv")
            context = "\n".join([f"Title: {p['Title']}\nAbstract: {p['Abstract']}\nLink: {p['Link']}" for p in papers])
            st.write("Summary:")
            prompts = generate_summary(context, query)
            st.write(prompts)

        elif option == "news":
            st.write("Fetching news articles...")
            news = fetch_news(query, num_needed)
            save_to_csv(news, "news_results.csv")
            context = "\n".join([f"Title: {n['Title']}\nSource: {n['Source']}\nLink: {n['Link']}" for n in news])
            st.write("Summary:")
            prompts = generate_summary(context, query)
            st.write(prompts)

    # Define the information for the video generation part
    scenes = parse_prompts_video(prompts)
    narrators = parse_prompts_voice(prompts)
    voice_files = []
    video_files = []

    st.write("Scene:", scenes)
    st.write("Narrator:", narrators)

    if len(scenes) != len(narrators):
        raise ValueError("Mismatch between number of scenes and narrators")

    # Generate video and voice files
    for index, narrator in enumerate(narrators):
        try:
            voice_file = generate_voice_segment(narrator)
            voice_files.append(voice_file)
            audio = AudioSegment.from_file(voice_file)
            length = int(len(audio) / 5000) + 1
            urls = get_images(scenes[index])
            video_file = generate_video_segment(scenes[index], length, urls)
            video_files.append(video_file)
        except Exception as e:
            st.write(f"Error processing segment {index}: {e}")

    # Combine the segments
    try:
        final_video = combine_segments(video_files, voice_files)
        st.write(f"Final video created: {final_video}")
    except Exception as e:
        st.write(f"Error combining video and voice segments: {e}")

if __name__ == "__main__":
    main()
