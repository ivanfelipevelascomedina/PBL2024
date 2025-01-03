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
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, TextClip, CompositeVideoClip, CompositeAudioClip
from resemble import Resemble
from pydub import AudioSegment
from moviepy import editor
import subprocess
import textwrap
import streamlit as st
from moviepy.config import change_settings

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
    project_uuid = Resemble.v2.projects.all(1, 10)['items'][0]['uuid']
    voice_uuid = '0842fdf9'
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

    #st.write(f"\nChecked {num_checked} papers to find {len(results)} that meet the criteria.")
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
def generate_summary(context, query, number_of_scenes, word_limit):
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
    #st.write("API Response:", response)
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
def generate_video_segment(prompt, number, prompt_image=None):
    ids = []

    while number > 0:
        completed = False
        generation = client_luma.generations.create(
            prompt=prompt,
            loop=True,
            aspect_ratio="16:9",
        )
        ids.append(generation.id)
        st.write("Luma generation")
        while not completed:
            generation = client_luma.generations.get(id=generation.id)
            if generation.state == "completed":
                completed = True
            elif generation.state == "failed":
                raise RuntimeError(f"Generation failed: {generation.failure_reason}")
            st.write("Dreaming")
            time.sleep(5)
        number -= 1

    downloaded_files = []
    output_file = f"{time.time()}.mp4"

    # Download each video part
    for video_id in ids:
        try:
            video_url = client_luma.generations.get(id=video_id).assets.video
            response = requests.get(video_url, stream=True)
            filename = f"{video_id}.mp4"
            with open(filename, 'wb') as file:
                file.write(response.content)
                st.session_state.partial_video_files.append(filename)  # Save to session state
                st.write(f"Video {video_id} created as {filename}")
        except Exception as e:
            st.error(f"Error processing video {video_id}: {e}")

    os.system(f"ffmpeg -f concat -safe 0 -i file_list.txt -c copy {output_file}")
    st.write(f"Videos concatenated into {output_file}")

    return output_file


# Function to add subtitles
#def annotate(clip, txt, txt_color='white', fontsize=50, font='Helvetica-Bold', max_width=1):
#    max_width_px = clip.size[0] * max_width
#    # Wrap the text into multiple lines based on the max width
#    wrapped_text = textwrap.fill(txt, width=50)  # 50 characters per line as an example, adjust based on actual font
#    txtclip = editor.TextClip(wrapped_text, fontsize=fontsize, font=font, color=txt_color, stroke_color='black', stroke_width=1)
#    # Composite the text on top of the video clip
#    cvc = editor.CompositeVideoClip([clip, txtclip.set_pos(('center', 'bottom'))])
#
#    return cvc.set_duration(clip.duration)

# Function to combine video, voice and subtitles
def combine_segments(video_files, voice_files, output_file):
    try:
        clips = []
        video_clips = [VideoFileClip(video) for video in video_files]
        for video_clip, audio, in zip(video_clips, voice_files):
            audio_clip = AudioFileClip(audio)
            video_clip = video_clip.set_audio(audio_clip)
            clips.append(video_clip)

        combined_video = concatenate_videoclips(clips)
        combined_video.write_videofile(output_file, codec="libx264", audio_codec="aac")
        
        # Log file creation step
        #st.write(f"Tried creating {output_file}")
        #absolute_path = os.path.abspath(output_file)
        #st.write(f"Absolute path: {absolute_path}")
        #st.write(f"File exists after creation: {os.path.exists(absolute_path)}")
    except Exception as e:
        st.write(f"Error in combine_segments: {e}")

    return output_file

# Function to add music to a video
def add_BGM(music, video, output_file, music_volume=0.3):
    # Load the video clip and extract the original audio
    video_clip = VideoFileClip(video)
    original_audio = video_clip.audio

    # Load the background music and adjust its volume
    bgm = AudioFileClip(music).volumex(music_volume)

    # Ensure both audios have the same duration (either trim the BGM or loop it)
    if bgm.duration > video_clip.duration:
        bgm = bgm.subclip(0, video_clip.duration)  # Trim BGM if it's longer than the video
    elif bgm.duration < video_clip.duration:
        bgm = bgm.loop(duration=video_clip.duration)  # Loop BGM if it's shorter than the video

    # Mix the original audio with the background music (using CompositeAudioClip)
    final_audio = CompositeAudioClip([original_audio, bgm])

    # Set the final audio to the video
    video_clip = video_clip.set_audio(final_audio)

    # Write the final video with background music
    video_clip.write_videofile(output_file, codec="libx264", audio_codec="aac")

    return output_file


# MAIN CODE

# Main program
def main():
    
    st.title("Educational Video Generation Tool")
    
    multi = '''**Disclaimer**: The videos generated by this system are created using artificial intelligence and machine learning algorithms. While every effort is made to ensure the content aligns with the input parameters, the system may produce unexpected, inaccurate, or "hallucinated" elements that do not reflect reality. These unintended artifacts are inherent to the generative process and should not be interpreted as factual, accurate, or reliable.  
    Users are advised to critically evaluate the generated content and avoid using it in contexts where accuracy or realism is critical without thorough verification. The creators of this system are not responsible for any misunderstanding, misuse, or consequences arising from the generated content.'''
    st.markdown(multi)

    # Initialize session state flags
    if 'video_generation_started' not in st.session_state:
        st.session_state.video_generation_started = False
    if 'video_generated' not in st.session_state:
        st.session_state.video_generated = False

    # Step 1: Start Video Generation
    if not st.session_state.video_generation_started:
        if st.button("Start Video Generation"):
            # Set the session state flag
            st.session_state.video_generation_started = True

            # Reinitialize required session state variables
            st.session_state.voice_files = []  # To store generated voice files
            st.session_state.video_files = []  # To store generated video files
            st.session_state.partial_video_files = []  # To store generated parts of video files by LumaAI
            st.session_state.final_video_no_music = None  # To store the final combined video
            st.session_state.final_video_music = None  # To store the final combined video with music
            st.session_state.prompts = None  # To store prompts
            st.session_state.narrators = None  # To store narrators
            st.session_state.scenes = None  # To store scenes

    # Step 2: Input Section
    if st.session_state.video_generation_started and not st.session_state.video_generated:
        query = st.text_input("Enter your query (e.g., 'World War II in Japan'):", "")
        option = st.radio("Choose data source:", ["news", "papers"])
        num_needed = st.slider("Amount of papers/news to fetch:", 0, 5, 10)
        scenes_needed = st.slider("Number of scenes for the video:", 1, 5, 10)
        word_limit = st.slider("Word limit per narration:", 10, 100, 50)

        if st.button("Generate Video"):
            st.session_state.video_generated = True
            # Simulate video generation logic here
            st.write("Video is being generated...")
    
    # Step 3: Display Results
    if st.session_state.video_generated:
        st.write("Video generation started")
        if option == "papers":
            st.write("Fetching academic papers...")
            papers = fetch_papers(query, num_needed)
            save_to_csv(papers, "papers_results.csv")
            context = "\n".join([f"Title: {p['Title']}\nAbstract: {p['Abstract']}\nLink: {p['Link']}" for p in papers])
            st.write("Summary:")
            st.session_state.prompts = generate_summary(context, query, scenes_needed, word_limit)
            st.write(st.session_state.prompts)
            st.session_state.scenes = parse_prompts_video(st.session_state.prompts)
            st.session_state.narrators = parse_prompts_voice(st.session_state.prompts)
    
    
        elif option == "news":
            st.write("Fetching news articles...")
            news = fetch_news(query, num_needed)
            save_to_csv(news, "news_results.csv")
            context = "\n".join([f"Title: {n['Title']}\nSource: {n['Source']}\nLink: {n['Link']}" for n in news])
            st.write("Summary:")
            st.session_state.prompts = generate_summary(context, query, scenes_needed, word_limit)
            st.write(st.session_state.prompts)
            st.session_state.scenes = parse_prompts_video(st.session_state.prompts)
            st.session_state.narrators = parse_prompts_voice(st.session_state.prompts)
    
        if st.session_state.narrators and st.session_state.scenes:
            if len(st.session_state.scenes) != len(st.session_state.narrators):
                raise ValueError("Mismatch between number of scenes and narrators")
            
            for index, (narrator, scene) in enumerate(zip(st.session_state.narrators, st.session_state.scenes)): # Generate audio and video for each narrator-scene pair
                name_number = index
                voice_file = generate_voice_segment(narrator)
                st.session_state.voice_files.append(voice_file)
                st.write("Audio:", name_number)
                audio = AudioSegment.from_file(voice_file)
                length = int(len(audio) / 5000) + 1
                video_prompt = scene + '\n' + "camera fixes, no camera movement"
                st.write("Video prompt: ", video_prompt)
                video_file = generate_video_segment(video_prompt, length)
                if video_file:
                    st.session_state.video_files.append(video_file)
                    st.write("Video:", name_number)
                    # Read and display the generated video
                    with open(video_file, "rb") as video_file_a:
                        video_bytes_a = video_file_a.read()
                        st.video(video_bytes_a)
                    
                    # Access and display the video from session state
                    with open(video_file, "rb") as video_file_b:
                        video_bytes_b = video_file_b.read()
                        st.video(video_bytes_b)
                else:
                    st.warning(f"Video generation failed for scene:", name_number)
        
            # Combine the segments
            try:
                output_file_1 = f"final_video_no_music{time.time()}.mp4"
                output_file_2 = f"final_video_music{time.time()}.mp4"
                final_video_no_music = combine_segments(st.session_state.video_files, st.session_state.voice_files, output_file_1)
                st.session_state.final_video_no_music = final_video_no_music
        
                # Add background music
                final_video_music = add_BGM("bollywoodkollywood-sad-love-bgm-13349.mp3", st.session_state.final_video_no_music, output_file_2)
                st.session_state.final_video_music = final_video_music
        
                if st.session_state.final_video_music and os.path.exists(st.session_state.final_video_music):
                    with open(st.session_state.final_video_music, "rb") as video_file:
                        video_bytes = video_file.read()
                        st.video(video_bytes)
        
            except Exception as e:
                st.write(f"Error combining video and voice segments: {e}")
        
            # Allow users to download the video
            if os.path.exists(st.session_state.final_video_music):
                with open(st.session_state.final_video_music, "rb") as file:
                    st.download_button(
                        label="Download Final Video",
                        data=file,
                        file_name=output_file_2,
                        mime="video/mp4"
                    )

if __name__ == "__main__":
    main()
