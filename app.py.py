import os
import json
import urllib.request
import streamlit as st
from google import genai
from google.genai import types
from gtts import gTTS
import moviepy

# moviepy 기능 불러오기
ImageClip = moviepy.ImageClip
AudioFileClip = moviepy.AudioFileClip
TextClip = moviepy.TextClip
CompositeVideoClip = moviepy.CompositeVideoClip
concatenate_videoclips = moviepy.concatenate_videoclips

st.set_page_config(page_title="AI 쇼츠 제작기 마스터", page_icon="🎬", layout="centered")
st.title("🎬 AI 유튜브 쇼츠 자동 제작기 (자막 완벽 버전)")

USER_API_KEY = st.text_input("🔑 본인의 Gemini API 키를 입력하세요", type="password")
test_topic = st.text_input("✍️ 쇼츠 영상 주제를 입력하세요", placeholder="예: 직장인 공감 유머 TOP 3")

# 리눅스 서버용 한국어 폰트 자동 다운로드 함수 (네모 깨짐 방지)
def download_korean_font():
    font_dir = "fonts"
    if not os.path.exists(font_dir):
        os.makedirs(font_dir)
    font_path = os.path.join(font_dir, "NanumGothic.ttf")
    if not os.path.exists(font_path):
        # 네이버 나눔고딕 폰트 다운로드
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        try:
            urllib.request.urlretrieve(url, font_path)
        except:
            pass
    return font_path

def generate_shorts_script(client, topic):
    prompt = f"""
    너는 유튜브 쇼츠 전문 크리에이터야.
    주제인 '{topic}'에 대해 시청자의 이탈을 막을 수 있는 흥미진진한 30초 분량의 쇼츠 대본을 작성해줘.
    반드시 아래의 JSON 포맷으로만 답변해야 해. 다른 부연 설명은 절대 하지 마.
    {{
        "title": "쇼츠 제목",
        "scenes": [
            {{
                "scene_number": 1,
                "narration": "첫 번째 장면 나레이션 내용",
                "keyword": "장면에 정확히 매칭되는 구체적인 영어 단어 하나 (예: office, money, crying, shock)"
            }}
        ]
    }}
    조건: 총 scene은 4~5개로 구성.
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
    video_clips = []
    
    for scene in scenes:
        num = scene["scene_number"]
        text_content = scene["narration"]
        image_path = f"{assets_folder}/scene_{num}.jpg"
        audio_path = f"{assets_folder}/scene_{num}.mp3"
        
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        # 이미지 크기 맞춤 조정
        try:
            image_clip = ImageClip(image_path).with_duration(duration).resized((1080, 1920))
        except:
            image_clip = ImageClip(image_path).set_duration(duration).resize((1080, 1920))
            
        # 자막 한글 깨짐 방지를 위해 다운로드한 폰트(font_path) 강제 지정
        try:
            text_clip = (TextClip(text=text_content, font_size=45, color="white", font=font_path, size=(900, None), method="caption")
                         .with_duration(duration)
                         .with_position(("center", 1400)))
        except:
            text_clip = (TextClip(text_content, fontsize=45, color="white", font=font_path, size=(900, None), method="caption")
                         .set_duration(duration)
                         .set_position(("center", 1400)))
        
        try:
            scene_clip = CompositeVideoClip([image_clip, text_clip]).with_audio(audio_clip)
        except:
            scene_clip = CompositeVideoClip([image_clip, text_clip]).set_audio(audio_clip)
            
        video_clips.append(scene_clip)
        
    final_video = concatenate_videoclips(video_clips, method="compose")
    output_path = "final_shorts.mp4"
    final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
    return output_path

if st.button("🚀 쇼츠 영상 제작 시작!"):
    if not USER_API_KEY:
        st.error("API 키를 입력해 주세요!")
    elif not test_topic:
        st.error("주제를 입력해 주세요!")
    else:
        with st.spinner("AI가 고품질 영상을 굽는 중입니다... 약 1~2분 소요됩니다."):
            try:
                # 1. 한글 폰트 준비
                font_path = download_korean_font()
                
                # 2. 대본 생성
                client = genai.Client(api_key=USER_API_KEY)
                script_result = generate_shorts_script(client, test_topic)
                
                if script_result:
                    assets_folder = "shorts_assets"
                    if not os.path.exists(assets_folder): os.makedirs(assets_folder)
                    
                    for scene in script_result["scenes"]:
                        # 3. 목소리 파일 생성
                        tts = gTTS(text=scene["narration"], lang='ko', slow=False)
                        tts.save(f"{assets_folder}/scene_{scene['scene_number']}.mp3")
                        
                        # 4. 정확한 키워드 매칭 이미지 주소로 변경
                        keyword = scene.get("keyword", "office")
                        image_path = f"{assets_folder}/scene_{scene['scene_number']}.jpg"
                        
                        # 키워드별로 완벽히 다른 사진을 보장하는 최신 이미지 주소 체계 적용
                        search_url = f"https://images.unsplash.com/photo-1542838132-92c53300491e?w=1080&h=1920&fit=crop" # 기본값
                        search_url = f"https://loremflickr.com/1080/1920/{keyword}"
                        
                        try:
                            urllib.request.urlretrieve(search_url, image_path)
                        except:
                            try:
                                urllib.request.urlretrieve(f"https://picsum.photos/1080/1920", image_path)
                            except:
                                pass
                            
                    # 5. 비디오 합성
                    video_file_path = make_final_video(script_result, font_path)
                    
                    st.success("🎉 고품질 영상 제작 대성공!")
                    with open(video_file_path, "rb") as file:
                        st.download_button(
                            label="📥 완성된 쇼츠 영상 다운로드 받기",
                            data=file,
                            file_name="my_final_shorts.mp4",
                            mime="video/mp4"
                        )
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")