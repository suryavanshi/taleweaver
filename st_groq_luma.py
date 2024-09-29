import os
import time
import json
import streamlit as st
from groq import Groq
from lumaai import AsyncLumaAI
import asyncio
from dotenv import load_dotenv

load_dotenv()
# Set up API clients
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
luma_client = AsyncLumaAI(auth_token=os.environ.get("LUMAAI_API_KEY"))

async def generate_video(prompt, narrative):
    # Generate initial video
    title = narrative['part1']['title']
    video_prompt1 = narrative['part1']['narrative'] + ' Zoom In ' + f'On the top right it says "{title}".'
    # video_prompt1 = f'Write on top right: "{title}".' + narrative['part1']['narrative']
    
   
    generation = await luma_client.generations.create(
        prompt=video_prompt1,
        aspect_ratio="16:9"
    )
    print("gen id:",generation.id)
    # Wait for the generation to complete
    while True:
        generation = await luma_client.generations.get(id=generation.id)
        # st.write("Part1:",generation)
        if generation.state == 'completed':
            break
        elif generation.state == 'failed':
            st.write("Generation failed!!",generation.failure_reason)
        await asyncio.sleep(5)
    
    # Extend the video 3 times
    for part in ['part2', 'part3']:
        title = narrative[part]['title']
        video_prompt = narrative[part]['narrative'] + ' Zoom Out ' + f'On the top right it says "{title}".' 
        print(f"{part} prompt:{video_prompt}")
        extension = await luma_client.generations.create(
            prompt=video_prompt,
            keyframes={
                "frame0": {
                    "type": "generation",
                    "id": generation.id
                }
            }
        )
        print("ext id:",extension.id)
        # Wait for the extension to complete
        while True:
            extension = await luma_client.generations.get(id=extension.id)
            if extension.state == 'completed':
                break
            elif extension.state == 'failed':
                st.write("Generation failed!!",generation.failure_reason)
                break
            await asyncio.sleep(5)
        
        # Update the generation ID for the next extension
        generation = extension
    
    return generation.assets.video

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

def main():
    st.title("TaleWeaver")
    
    input_type = st.selectbox("Choose input type:", ["Product Description","Tutorial", "Mood", "Interactive Storytelling Generator","Historical Event", "Dream"])
    user_input = st.text_area(f"Describe your {input_type.lower()}:")
    
    if st.button("Generate Video"):
        with st.spinner("Generating narrative..."):
            narrative = generate_narrative(input_type.lower(), user_input)
        
        st.text_area("Generated Narrative:", value=narrative, height=200)
        
        with st.spinner("Creating video... This may take a few minutes."):
            video_url = asyncio.run(generate_video(user_input, narrative))
        
        st.video(video_url)

if __name__ == "__main__":
    main()