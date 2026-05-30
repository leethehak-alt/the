import os
import json
import urllib.request
import requests
from bs4 import BeautifulSoup
import streamlit as st
from google import genai
from google.genai import types
from gtts import gTTS
import moviepy

# moviepy 필수 엔진 바인딩
ImageClip = moviepy.ImageClip
AudioFileClip = moviepy.AudioFileClip
TextClip = moviepy.TextClip
CompositeVideoClip = moviepy.CompositeVideoClip
concatenate_videoclips = moviepy.concatenate_videoclips

# 앱 페이지 레이아웃 설정
st.set_page_config(page_title="AI 멀티 쇼츠 마스터 프로", page_icon="🎬", layout="centered")

creation_mode = st.radio(
    "📱 어떤 방식으로 영상을 제작하실 건가요?",
    ["💡 일반 유튜브 대본용 (주제 입력)", "📝 티스토리 블로그용 (본문 글 요약)"],
    horizontal=True
)

st.markdown("---")

if "블로그" in creation_mode:
    st.header("📝 티스토리 블로그 ➡️ 쇼츠 자동 변환기")
    user_input = st.text_area("✍️ 블로그 본문 글을 복사해서 붙여넣으세요", placeholder="여기에 블로그 글 내용을 입력하세요...", height=250)
else:
    st.header("💡 일반 유튜브 쇼츠 제작기")
    user_input = st.text_input("✍️ 쇼츠 영상 주제를 입력하세요", placeholder="예: 서울 멋진 카페리스트")

st.markdown("---")
USER_API_KEY = st.text_input("🔑 본인의 Gemini API 키를 입력하세요", type="password")

def get_clean_font():
    font_dir = "fonts"
    if not os.path.exists(font_dir): 
        os.makedirs(font_dir)
    font_path = os.path.join(font_dir, "NanumGothic.ttf")
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(font_path, 'wb') as out_file:
                out_file.write(response.read())
        except: 
            pass
    return font_path

def generate_shorts_script(client, content, mode):
    if "블로그" in mode:
        prompt = f"블로그 글인 '{content}'을 핵심 요약한 30초 분량의 쇼츠 대본을 짜줘. 반드시 JSON 포맷으로만 답변해."
    else:
        prompt = f"주제인 '{content}'에 대한 대본을 짜줘. 반드시 JSON 포맷으로만 답변해."
        
    prompt += """
    반드시 아래의 구조화된 JSON 포맷으로만 응답하고 다른 설명 텍스트는 절대 붙이지 마:
    {
        "video_title": "오늘의 추천 소식",
        "scenes": [
            {
                "scene_number": 1,
                "narration": "장면의 한국어 설명 문구",
                "image_prompt": "A beautiful photo based on topic, high resolution, vertical 9:16"
            }
        ]
    }
    조건: 총 장면(scenes)은 딱 3개로 구성해줘.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(response.text)

def make_final_video(script_data, font_path):
    assets_folder = "shorts_assets"
    scenes = script_data.get("scenes", [])
    video_title_text = script_data.get("video_title", "AI Shorts")
    video_clips = []
    
    for scene in scenes:
        num = scene["scene_number"]
        text_content = scene["narration"]
        image_path = f"{assets_folder}/scene_{num}.jpg"
        audio_path = f"{assets_folder}/scene_{num}.mp3"
        
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        try: image_clip = ImageClip(image_path).with_duration(duration).resized((1080, 1920))
        except: image_clip = ImageClip(image_path).set_duration(duration).resize((1080, 1920))
            
        try:
            sub_clip = (TextClip(text=text_content, font_size=40, color="white", font=font_path, size=(900, None), method="caption")
                         .with_duration(duration)
                         .with_position(("center", 1450)))
        except:
            sub_clip = (TextClip(text_content, fontsize=40, color="white", font=font_path, size=(900, None), method="caption")
                         .set_duration(duration)
                         .set_position(("center", 1450)))
        
        try: scene_clip = CompositeVideoClip([image_clip, sub_clip]).with_audio(audio_clip)
        except: scene_clip = CompositeVideoClip([image_clip, sub_clip]).set_audio(audio_clip)
            
        video_clips.append(scene_clip)
    
    final_concat = concatenate_videoclips(video_clips, method="compose")
    total_duration = final_concat.duration
    
    try:
        top_title_clip = (TextClip(text=video_title_text, font_size=60, color="yellow", font=font_path, stroke_color="black", stroke_width=3)
                          .with_duration(total_duration)
                          .with_position(("center", 220)))
    except:
        top_title_clip = (TextClip(video_title_text, fontsize=60, color="yellow", font=font_path)
                          .set_duration(total_duration)
                          .set_position(("center", 220)))
    
    final_video = CompositeVideoClip([final_concat, top_title_clip])
    output_path = "final_shorts.mp4"
    final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
    return output_path

if st.button("🚀 멀티 쇼츠 영상 제작 시작!"):
    if not USER_API_KEY:
        st.error("API 키를 입력해 주세요!")
    elif not user_input:
        st.error("내용을 입력해 주세요!")
    else:
        with st.spinner("AI 공장이 비디오를 열심히 제작 중입니다... 잠시만 기다려주세요."):
            try:
                font_path = get_clean_font()
                client = genai.Client(api_key=USER_API_KEY)
                script_result = generate_shorts_script(client, user_input, creation_mode)
                
                if script_result:
                    assets_folder = "shorts_assets"
                    if not os.path.exists(assets_folder): 
                        os.makedirs(assets_folder)
                    
                    for scene in script_result["scenes"]:
                        # 1. TTS 오디오 추출
                        tts = gTTS(text=scene["narration"], lang='ko', slow=False)
                        tts.save(f"{assets_folder}/scene_{scene['scene_number']}.mp3")
                        
                        # 2. 이미지 생성 및 저장
                        img_prompt = scene.get("image_prompt", "A clean concept graphic, vertical 9:16")
                        image_path = f"{assets_folder}/scene_{scene['scene_number']}.jpg"
                        
                        try:
                            img_response = client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=f"Generate a beautiful vertical image: {img_prompt}",
                                config=types.GenerateContentConfig(response_modalities=["IMAGE"], image_config=types.ImageConfig(aspect_ratio="9:16"))
                            )
                            for part in img_response.parts:
                                if part.inline_data:
                                    with open(image_path, "wb") as f: f.write(part.inline_data.data)
                        except:
                            try:
                                clean_keyword = img_prompt.split(",")[0].replace(" ", "")
                                search_url = f"https://loremflickr.com/1080/1920/{clean_keyword}"
                                req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
                                with urllib.request.urlopen(req) as response, open(image_path, 'wb') as out_file:
                                    out_file.write(response.read())
                            except:
                                urllib.request.urlretrieve("https://picsum.photos/1080/1920", image_path)
                            
                    # 3. 비디오 최종 병합
                    video_file_path = make_final_video(script_result, font_path)
                    
                    st.success("🎉 쇼츠 비디오가 성공적으로 포장되었습니다!")
                    with open(video_file_path, "rb") as file:
                        st.download_button(label="📥 완성된 쇼츠 영상 다운로드", data=file, file_name="ai_factory_shorts.mp4", mime="video/mp4")
            except Exception as e:
                st.error(f"제작 중 에러 발생: {e}")
