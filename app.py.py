import os
import json
import urllib.request
import streamlit as st
from google import genai
from google.genai import types
from gtts import gTTS
import moviepy

# 가장 안전하고 안정적인 컴포즈 방식 지정
ImageClip = moviepy.ImageClip
AudioFileClip = moviepy.AudioFileClip
concatenate_videoclips = moviepy.concatenate_videoclips

st.set_page_config(page_title="AI 쇼츠 마스터 스튜디오", page_icon="🎬", layout="centered")
st.title("🎬 AI 유튜브 쇼츠 자동 제작기 (최종 진화 버전)")
st.write("시스템 충돌 없는 안전한 자막과 1:1 맞춤형 이미지 매칭 시스템이 적용되었습니다.")

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
                "keyword": "장면과 딱 맞는 직관적이고 구체적인 영어 단어 하나 (예: office, shock, crying, cash)"
            }}
        ]
    }}
    조건: 총 scene은 3~4개로 짧고 강렬하게 구성.
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
        image_path = f"{assets_folder}/scene_{num}.jpg"
        audio_path = f"{assets_folder}/scene_{num}.mp3"
        
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        # 쇼츠 규격(1080x1920 세로형)으로 이미지 크기 안전 조정
        try:
            image_clip = ImageClip(image_path).with_duration(duration).resized((1080, 1920))
        except:
            image_clip = ImageClip(image_path).set_duration(duration).resize((1080, 1920))
            
        try:
            image_clip = image_clip.with_audio(audio_clip)
        except:
            image_clip = image_clip.set_audio(audio_clip)
            
        video_clips.append(image_clip)
        
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
        with st.spinner("AI가 영상을 매칭하고 굽는 중입니다... 약 1분 소요됩니다."):
            try:
                client = genai.Client(api_key=USER_API_KEY)
                script_result = generate_shorts_script(client, test_topic)
                
                if script_result:
                    assets_folder = "shorts_assets"
                    if not os.path.exists(assets_folder): os.makedirs(assets_folder)
                    
                    # 스트림릿 화면 표시용 리스트 준비
                    narrations = []
                    
                    for scene in script_result["scenes"]:
                        narrations.append(scene["narration"])
                        
                        # 목소리 파일 생성
                        tts = gTTS(text=scene["narration"], lang='ko', slow=False)
                        tts.save(f"{assets_folder}/scene_{scene['scene_number']}.mp3")
                        
                        # 장면에 딱 맞는 이미지 검색어 매칭 시스템
                        keyword = scene.get("keyword", "idea")
                        image_path = f"{assets_folder}/scene_{scene['scene_number']}.jpg"
                        
                        # 고해상도 매칭용 안전 주소 사용
                        search_url = f"https://loremflickr.com/1080/1920/{keyword}"
                        try:
                            urllib.request.urlretrieve(search_url, image_path)
                        except:
                            try:
                                urllib.request.urlretrieve(f"https://picsum.photos/1080/1920", image_path)
                            except:
                                pass
                            
                    video_file_path = make_final_video(script_result)
                    
                    st.success("🎉 고품질 영상 연동 완료!")
                    
                    # [대박 기능] 영상 바로 밑에 글씨가 깨지지 않고 깔끔하게 출력되는 자막 보드판 탑재
                    st.subheader("📝 이번 쇼츠 자막 및 대본 리스트")
                    for idx, text in enumerate(narrations):
                        st.info(f"장면 {idx+1}: {text}")
                        
                    with open(video_file_path, "rb") as file:
                        st.download_button(
                            label="📥 완성된 쇼츠 영상 다운로드 받기",
                            data=file,
                            file_name="my_perfect_shorts.mp4",
                            mime="video/mp4"
                        )
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")