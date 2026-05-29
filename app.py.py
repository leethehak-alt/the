import os
import json
import urllib.request
import streamlit as st
from google import genai
from google.genai import types
from gtts import gTTS
import moviepy

# moviepy 기능 정의
ImageClip = moviepy.ImageClip
AudioFileClip = moviepy.AudioFileClip
TextClip = moviepy.TextClip
CompositeVideoClip = moviepy.CompositeVideoClip
concatenate_videoclips = moviepy.concatenate_videoclips

st.set_page_config(page_title="AI 쇼츠 마스터 오토", page_icon="🎬", layout="centered")
st.title("🎬 AI 유튜브 쇼츠 자동 제작기 (자막+이미지 일치 버전)")
st.write("폰트를 자동으로 설치하여 영상 내에 한글 자막을 직접 합성합니다.")

USER_API_KEY = st.text_input("🔑 본인의 Gemini API 키를 입력하세요", type="password")
test_topic = st.text_input("✍️ 쇼츠 영상 주제를 입력하세요", placeholder="예: 서울 멋진 카페리스트")

# 프로그램이 직접 한글 폰트를 인터넷에서 다운로드받는 안전 장치
def get_clean_font():
    font_dir = "fonts"
    if not os.path.exists(font_dir):
        os.makedirs(font_dir)
    font_path = os.path.join(font_dir, "NanumGothic.ttf")
    
    if not os.path.exists(font_path):
        # 구글 공식 저장소에서 깨지지 않는 나눔고딕 폰트 직접 서빙
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(font_path, 'wb') as out_file:
                out_file.write(response.read())
        except Exception as e:
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
                "keyword": "장면과 딱 매칭되는 구체적인 영어 단어 하나 (예: cafe, coffee, seoul, dessert)"
            }}
        ]
    }}
    조건: 총 scene은 3~4개로 구성.
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
        
        # 쇼츠 정규 세로 비율(1080x1920) 리사이징
        try:
            image_clip = ImageClip(image_path).with_duration(duration).resized((1080, 1920))
        except:
            image_clip = ImageClip(image_path).set_duration(duration).resize((1080, 1920))
            
        # 다운로드받은 나눔고딕으로 영상 위에 직접 자막 박기 (가로폭 900 제한으로 자동 줄바꿈)
        try:
            text_clip = (TextClip(text=text_content, font_size=45, color="white", font=font_path, size=(900, None), method="caption")
                         .with_duration(duration)
                         .with_position(("center", 1450)))
        except:
            text_clip = (TextClip(text_content, fontsize=45, color="white", font=font_path, size=(900, None), method="caption")
                         .set_duration(duration)
                         .set_position(("center", 1450)))
        
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
        with st.spinner("AI가 폰트를 세팅하고 맞춤형 영상과 자막을 합성하고 있습니다... 약 1~2분 소요"):
            try:
                # 폰트 자동 세팅
                font_path = get_clean_font()
                
                client = genai.Client(api_key=USER_API_KEY)
                script_result = generate_shorts_script(client, test_topic)
                
                if script_result:
                    assets_folder = "shorts_assets"
                    if not os.path.exists(assets_folder): os.makedirs(assets_folder)
                    
                    for scene in script_result["scenes"]:
                        # 성우 목소리 음성 구우 기
                        tts = gTTS(text=scene["narration"], lang='ko', slow=False)
                        tts.save(f"{assets_folder}/scene_{scene['scene_number']}.mp3")
                        
                        # AI 단어 기반 1:1 이미지 실시간 변경 연동
                        keyword = scene.get("keyword", "cafe")
                        image_path = f"{assets_folder}/scene_{scene['scene_number']}.jpg"
                        
                        # 키워드가 완벽하게 매칭되는 고해상도 세로 사진 엔진 가동
                        search_url = f"https://loremflickr.com/1080/1920/{keyword},seoul,cafe,coffee,interior"
                        
                            try:
                            req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req) as response, open(image_path, 'wb') as out_file:
                                out_file.write(response.read())
                        except:
                            try: urllib.request.urlretrieve(f"https://picsum.photos/1080/1920", image_path)
                            except: pass
                            
                    video_file_path = make_final_video(script_result, font_path)
                    
                    st.success("🎉 자막 합본 영상 제작 완료!")
                    with open(video_file_path, "rb") as file:
                        st.download_button(
                            label="📥 완성된 쇼츠 영상 다운로드 받기",
                            data=file,
                            file_name="my_ai_shorts_with_subtitles.mp4",
                            mime="video/mp4"
                        )
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")