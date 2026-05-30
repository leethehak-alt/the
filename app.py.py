import os
import sys
import subprocess
import urllib.request
import json

# [긴급 처방] bs4와 requests가 없으면 코드가 실행되면서 스스로 즉석 설치하도록 만듭니다.
try:
    from bs4 import BeautifulSoup
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4", "requests"])
    from bs4 import BeautifulSoup
    import requests

import streamlit as st
from google import genai
from google.genai import types
from gtts import gTTS
import moviepy

# moviepy 핵심 기능 정의
ImageClip = moviepy.ImageClip
AudioFileClip = moviepy.AudioFileClip
TextClip = moviepy.TextClip
CompositeVideoClip = moviepy.CompositeVideoClip
concatenate_videoclips = moviepy.concatenate_videoclips

st.set_page_config(page_title="AI 멀티 트렌드 마스터 프로", page_icon="🎬", layout="centered")

# [1] 화면 상단 3단 모드 선택 장치
creation_mode = st.radio(
    "📱 어떤 방식으로 영상을 제작하실 건가요?",
    ["💡 일반 유튜브 대본용 (주제 입력)", "📝 티스토리 블로그용 (본문 글 요약)", "🔥 다음카페 실시간 핫이슈 (자동 수집)"],
    horizontal=True
)

st.markdown("---")

# 모드별 입력창 가변 처리
if "다음카페" in creation_mode:
    st.header("🔥 다음카페 실시간 핫이슈 쇼츠 자동 제작기")
    st.info("💡 주제를 적지 않아도 됩니다! 버튼을 누르면 다음 실시간 트렌드 키워드를 자동으로 수집하여 영상을 굽습니다.")
    user_input = "자동 수집 모드"
elif "블로그" in creation_mode:
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
    if "다음카페" in mode:
        prompt = f"""
        너는 대한민국 실시간 이슈와 트렌드를 가장 빠르게 전달하는 유튜브 쇼츠 크리에이터야.
        오늘의 다음카페 및 포털 트렌드 핵심 주제인 '{content}'에 대해 시청자들이 스와이프를 멈추고 몰입할 수 있는 30초 정보성 쇼츠 대본을 작성해줘.
        반드시 아래의 JSON 포맷으로만 답변하고 다른 텍스트는 절대 포함하지 마.
        {{
            "video_title": "[실시간 화제] 요즘 커뮤니티 난리난 역대급 사건",
            "scenes": [
                {{
                    "scene_number": 1,
                    "narration": "첫 번째 장면 나레이션 문구",
                    "image_prompt": "A modern concept graphic illustration of news and trend topic, vivid color, vertical 9:16"
                }}
            ]
        }}
        조건: 총 scene 3개로 구성할 것.
        """
    elif "블로그" in mode:
        prompt = f"""
        너는 블로그 전문 요약 크리에이터야. 입력된 블로그 글인 '{content}'을 요약한 30초 분량의 쇼츠 대본을 작성해줘.
        반드시 아래의 JSON 포맷으로만 답변해.
        {{
            "video_title": "블로그 핵심 요약",
            "scenes": [
                {{
                    "scene_number": 1,
                    "narration": "요약 내용 문구",
                    "image_prompt": "An artistic clean illustration, vertical 9:16"
                }}
            ]
        }}
        조건: 총 scene 3개로 구성.
        """
    else:
        prompt = f"""
        너는 유튜브 쇼츠 전문 크리에이터야. 주제인 '{content}'에 대한 흥미진진한 30초 분량의 쇼츠 대본을 작성해줘.
        반드시 아래의 JSON 포맷으로만 답변해.
        {{
            "video_title": "오늘의 추천 콘텐츠",
            "scenes": [
                {{
                    "scene_number": 1,
                    "narration": "장면 나레이션 내용",
                    "image_prompt": "A beautiful photo based on topic, high resolution, vertical 9:16"
                }}
            ]
        }}
        조건: 총 scene 3개로 구성.
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
    video_title_text = script_data.get("video_title", "실시간 핫이슈")
    video_clips = []
    
    for scene in scenes:
        num = scene["scene_number"]
        text_content = scene["narration"]
        image_path = f"{assets_folder}/scene_{num}.jpg"
        audio_path = f"{assets_folder}/scene_{num}.mp3"
        
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        try: 
            image_clip = ImageClip(image_path).with_duration(duration).resized((1080, 1920))
        except: 
            image_clip = ImageClip(image_path).set_duration(duration).resize((1080, 1920))
            
        try:
            sub_clip = (TextClip(text=text_content, font_size=42, color="white", font=font_path, size=(900, None), method="caption")
                         .with_duration(duration)
                         .with_position(("center", 1450)))
        except:
            sub_clip = (TextClip(text_content, fontsize=42, color="white", font=font_path, size=(900, None), method="caption")
                         .set_duration(duration)
                         .set_position(("center", 1450)))
        
        try: 
            scene_clip = CompositeVideoClip([image_clip, sub_clip]).with_audio(audio_clip)
        except: 
            scene_clip = CompositeVideoClip([image_clip, sub_clip]).set_audio(audio_clip)
            
        video_clips.append(scene_clip)
    
    final_concat = concatenate_videoclips(video_clips, method="compose")
    total_duration = final_concat.duration
    
    try:
        top_title_clip = (TextClip(text=video_title_text, font_size=65, color="yellow", font=font_path, stroke_color="black", stroke_width=3)
                          .with_duration(total_duration)
                          .with_position(("center", 220)))
    except:
        top_title_clip = (TextClip(video_title_text, fontsize=65, color="yellow", font=font_path)
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
        with st.spinner("AI가 실시간 정보를 분석하고 영상을 제작하는 중입니다..."):
            try:
                # [다음카페 모드일 때 크롤러 작동 장치]
                if "다음카페" in creation_mode:
                    try:
                        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                        res = requests.get("https://search.daum.net/search?w=tot&q=%EC%8B%A4%EC%8B%9C%EA%B0%84%20%EA%B2%B2%EC%8B%9C%EA%B8%80", headers=headers, timeout=5)
                        soup = BeautifulSoup(res.text, 'html.parser')
                        keywords = [tags.text.strip() for tags in soup.select('.tit_keyword')[:3] if tags.text.strip()]
                        if keywords:
                            user_input = ", ".join(keywords)
                        else:
                            user_input = "오늘의 대한민국 커뮤니티 인기 화제 키워드 소식"
                    except:
                        user_input = "오늘의 인터넷 실시간 트렌드 뉴스 소식"
                
                font_path = get_clean_font()
                client = genai.Client(api_key=USER_API_KEY)
                script_result = generate_shorts_script(client, user_input, creation_mode)
                
                if script_result:
                    assets_folder = "shorts_assets"
                    if not os.path.exists(assets_folder): 
                        os.makedirs(assets_folder)
                    
                    for scene in script_result["scenes"]:
                        tts = gTTS(text=scene["narration"], lang='ko', slow=False)
                        tts.save(f"{assets_folder}/scene_{scene['scene_number']}.mp3")
                        
                        img_prompt = scene.get("image_prompt", "A clean concept graphic, vertical 9:16")
                        image_path = f"{assets_folder}/scene_{scene['scene_number']}.jpg"
                        
                        try:
                            img_response = client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=f"Generate a beautiful 9:16 ratio vertical illustration image based on this description: {img_prompt}",
                                config=types.GenerateContentConfig(response_modalities=["IMAGE"], image_config=types.ImageConfig(aspect_ratio="9:16"))
                            )
                            for part in img_response.parts:
                                if part.inline_data:
                                    with open(image_path, "wb") as f: 
                                        f.write(part.inline_data.data)
                        except:
                            try:
                                clean_keyword = img_prompt.split(",")[0].replace(" ", "")
                                search_url = f"https://loremflickr.com/1080/1920/{clean_keyword},news,trend"
                                req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
                                with urllib.request.urlopen(req) as response, open(image_path, 'wb') as out_file:
                                    out_file.write(response.read())
                            except:
                                urllib.request.urlretrieve(f"https://picsum.photos/1080/1920", image_path)
                            
                    video_file_path = make_final_video(script_result, font_path)
                    
                    st.success(f"🎉 실시간 자동 생성 완료! 상단 제목: '{script_result['video_title']}'")
                    with open(video_file_path, "rb") as file:
                        st.download_button(label="📥 완성된 쇼츠 영상 다운로드", data=file, file_name="daum_trend_shorts.mp4", mime="video/mp4")
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")