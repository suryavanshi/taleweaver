import os
import time
import json
import requests
import streamlit as st
from groq import Groq
from lumaai import AsyncLumaAI
import asyncio
from dotenv import load_dotenv
from moviepy.editor import VideoFileClip, concatenate_videoclips

load_dotenv()
# Set up API clients
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
luma_client = AsyncLumaAI(auth_token=os.environ.get("LUMAAI_API_KEY"))

async def generate_video(prompt):
    generation = await luma_client.generations.create(
        prompt=prompt,
        aspect_ratio="16:9"
    )
    
    while True:
        generation = await luma_client.generations.get(id=generation.id)
        if generation.state == 'completed':
            return generation.assets.video
        elif generation.state == 'failed':
            print("Gen failed")
            raise Exception("Video generation failed")
        
        await asyncio.sleep(10)

def download_video(url, filename):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(filename, 'wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)

def combine_videos(video_files, output_file):
    clips = [VideoFileClip(video) for video in video_files]
    final_clip = concatenate_videoclips(clips)
    final_clip.write_videofile(output_file)
    final_clip.close()
    for clip in clips:
        clip.close()

def generate_narrative(input_type, user_input):
    # prompt = f"""Create a vivid, detailed narrative with three parts based on the following {input_type}: {user_input}. 
    # Return the three parts as JSON, with keys part1, part2, part3. Each part should be only 1 line.
    # Use below format:\n{{'part1':'narrative part1','part2':'narative part2','part3':'narative part3'}}"""
    prompt = f"""Create a vivid narrative with three parts based on the following {input_type}: {user_input}. 
    Return the three parts as JSON, with keys part1, part2, part3. The narrative should be around 3 lines.
    Use below format:
    {{"part1": {{"title": "title1", "narrative": "narrative part1"}},
    "part2": {{"title": "title2", "narrative": "narrative part2"}},
    "part3": {{"title": "title3", "narrative": "narrative part3"}}}}"""
    chat_completion = groq_client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama-3.1-70b-versatile",
        response_format={"type": "json_object"}
    )
    narrative_json = json.loads(chat_completion.choices[0].message.content)
    # return chat_completion.choices[0].message.content
    return narrative_json

async def process_videos(user_input, narrative_parts):
    video_files = []
    for i, (part, content) in enumerate(narrative_parts.items(), 1):
        print("part,content:",part,content)
        title = content['title']
        video_prompt = content['narrative'] + f'On the top right it says "{title}".'
        # prompt = f"{user_input}. {content}"
        print("Vid prompt:",video_prompt)
        video_url = await generate_video(video_prompt)
        filename = f"video_part{i}.mp4"
        download_video(video_url, filename)
        video_files.append(filename)
    
    output_file = "combined_video.mp4"
    print("Starting to combine!!")
    combine_videos(video_files, output_file)
    
    # Clean up individual video files
    for file in video_files:
        os.remove(file)
    
    return output_file

def main():
    st.title("TaleWeaver")
    
    input_type = st.selectbox("Choose input type:", ["Product Description","Tutorial", "Mood", "Interactive Storytelling Generator","Historical Event", "Dream"])
    user_input = st.text_area(f"Describe your {input_type.lower()}:")
    
    if st.button("Generate Video"):
        with st.spinner("Generating narrative..."):
            narrative = generate_narrative(input_type.lower(), user_input)
        
        st.text_area("Generated Narrative:", value=narrative, height=200)
      
    
        with st.spinner("Creating videos and combining... This may take several minutes."):
            output_file = asyncio.run(process_videos(user_input, narrative))
        
        
        st.video(output_file)

if __name__ == "__main__":
    main()