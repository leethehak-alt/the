import os
import json
import urllib.request
import streamlit as st
from google import genai
from google.genai import types
from gtts import gTTS
import moviepy

# moviepy 최신 버전 기능 불러오기
ImageClip = moviepy.ImageClip
AudioFileClip = moviepy.AudioFileClip
TextClip = moviepy.TextClip
CompositeVideoClip = moviepy.CompositeVideoClip
concatenate_videoclips = moviepy.concatenate_videoclips

st.set_page_config(page_title="AI 쇼츠 제작기 Pro", page_icon="🎬", layout="centered")
st.title("🎬 AI 유튜브 쇼츠 자동 제작기 Pro")
st.write("자막 자동 생성 및 주제 맞춤형 이미지 매칭 기능이 적용된 버전입니다.")

USER_API_KEY = st.text_input("🔑 본인의 Gemini API 키를 입력하세요", type="password")
test_topic = st.text_input("✍️ 쇼츠 영상 주제를 입력하세요", placeholder="예: 직장인 공감 유머 TOP 3")

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
                "keyword": "장면에 어울리는 구체적인 영어 단어 하나 (예: office, tired, computer)"
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

def make_final_video(script_data):
    assets_folder = "shorts_assets"
    scenes = script_data.get("scenes", [])
    video_clips = []
    
    for scene in scenes:
        num = scene["scene_number"]
        text_content = scene["narration"]
        image_path = f"{assets_folder}/scene_{num}.jpg"
        audio_path = f"{assets_folder}/scene_{num}.mp3"
        
        # 1. 오디오 로드 및 길이 측정
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        # 2. 이미지 클립 생성 (쇼츠 전용 세로 비율 크기 조절)
        try:
            image_clip = ImageClip(image_path).with_duration(duration).resized((1080, 1920))
        except:
            image_clip = ImageClip(image_path).set_duration(duration).resize((1080, 1920))
            
        # 3. 자막(텍스트) 클립 생성
        try:
            # 글자 크기 40, 하얀색, 하단 중앙 배치, 자막 가로폭 제한
            text_clip = (TextClip(text=text_content, font_size=40, color="white", size=(900, None), method="caption")
                         .with_duration(duration)
                         .with_position(("center", 1500))) # 화면 하단 배치
        except:
            text_clip = (TextClip(text_content, fontsize=40, color="white", size=(900, None), method="caption")
                         .set_duration(duration)
                         .set_position(("center", 1500)))
        
        # 4. 이미지 위에 자막 얹기 및 오디오 결합
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
                client = genai.Client(api_key=USER_API_KEY)
                script_result = generate_shorts_script(client, test_topic)
                
                if script_result:
                    assets_folder = "shorts_assets"
                    if not os.path.exists(assets_folder): os.makedirs(assets_folder)
                    
                    for scene in script_result["scenes"]:
                        # TTS 성우 음성 파일 생성
                        tts = gTTS(text=scene["narration"], lang='ko', slow=False)
                        tts.save(f"{assets_folder}/scene_{scene['scene_number']}.mp3")
                        
                        # AI가 추천한 키워드로 맞춤형 이미지 다운로드
                        keyword = scene.get("keyword", "nature")
                        image_path = f"{assets_folder}/scene_{scene['scene_number']}.jpg"
                        search_url = f"https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=1080&h=1920&fit=crop&q=80" 
                        # 무작위 대신 키워드를 섞은 주소 활용
                        search_url = f"https://source.unsplash.com/featured/1080x1920/?{keyword}"
                        
                        try:
                            urllib.request.urlretrieve(search_url, image_path)
                        except:
                            # 백업용 이미지 주소
                            try:
                                urllib.request.urlretrieve(f"https://picsum.photos/1080/1920", image_path)
                            except:
                                pass
                            
                    video_file_path = make_final_video(script_result)
                    
                    st.success("🎉 고품질 영상 제작 대성공!")
                    with open(video_file_path, "rb") as file:
                        st.download_button(
                            label="📥 완성된 쇼츠 영상 다운로드 받기",
                            data=file,
                            file_name="my_improved_shorts.mp4",
                            mime="video/mp4"
                        )
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")