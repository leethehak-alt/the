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

st.set_page_config(page_title="AI 멀티 쇼츠 마스터", page_icon="🎬", layout="centered")

# [1] 화면 상단 모드 선택 장치
creation_mode = st.radio(
    "📱 어떤 방식으로 영상을 제작하실 건가요?",
    ["💡 일반 유튜브 대본용 (주제 입력)", "📝 티스토리 블로그용 (본문 글 요약)"],
    horizontal=True
)

# [2] 선택한 모드를 상단에 크고 명확하게 타이틀로 띄워주는 장치 추가!
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
        except: pass
    return font_path

def generate_shorts_script(client, content, mode):
    if "블로그" in mode:
        prompt = f"""
        너는 블로그 전문 요약 크리에이터야. 입력된 블로그 글인 '{content}'을 분석해서 시청자들이 30초 만에 이해할 수 있도록 핵심 위주로 요약한 쇼츠 대본을 작성해줘.
        반드시 아래의 JSON 포맷으로만 답변해야 해. 부연 설명 금지.
        {{
            "title": "블로그 요약 쇼츠 제목",
            "scenes": [
                {{
                    "scene_number": 1,
                    "narration": "첫 번째 핵심 요약 내용",
                    "image_prompt": "이 나레이션 장면에 백퍼센트 정확히 매칭되는 사실적이고 세련된 고품질 이미지 생성용 영어 프롬프트 (예: 'A cinematic shot of a modern Seoul cafe interior, warm lighting, espresso machine, 8k resolution, vertical 9:16')"
                }}
            ]
        }}
        조건: 총 scene은 3~4개로 구성.
        """
    else:
        prompt = f"""
        너는 유튜브 쇼츠 전문 크리에이터야. 주제인 '{content}'에 대해 시청자의 이탈을 막을 수 있는 흥미진진한 30초 분량의 쇼츠 대본을 작성해줘.
        반드시 아래의 JSON 포맷으로만 답변해야 해. 부연 설명 금지.
        {{
            "title": "쇼츠 제목",
            "scenes": [
                {{
                    "scene_number": 1,
                    "narration": "첫 번째 장면 나레이션 내용",
                    "image_prompt": "이 나레이션 장면에 백퍼센트 정확히 매칭되는 사실적이고 세련된 고품질 이미지 생성용 영어 프롬프트 (예: 'A cozy coffee shop in Seoul with beautiful latte art on the table, photorealistic, vertical 9:16')"
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
        
        try: image_clip = ImageClip(image_path).with_duration(duration).resized((1080, 1920))
        except: image_clip = ImageClip(image_path).set_duration(duration).resize((1080, 1920))
            
        try:
            text_clip = (TextClip(text=text_content, font_size=45, color="white", font=font_path, size=(900, None), method="caption")
                         .with_duration(duration)
                         .with_position(("center", 1450)))
        except:
            text_clip = (TextClip(text_content, fontsize=45, color="white", font=font_path, size=(900, None), method="caption")
                         .set_duration(duration)
                         .set_position(("center", 1450)))
        
        try: scene_clip = CompositeVideoClip([image_clip, text_clip]).with_audio(audio_clip)
        except: scene_clip = CompositeVideoClip([image_clip, text_clip]).set_audio(audio_clip)
            
        video_clips.append(scene_clip)
        
    final_video = concatenate_videoclips(video_clips, method="compose")
    output_path = "final_shorts.mp4"
    final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
    return output_path

if st.button("🚀 멀티 쇼츠 영상 제작 시작!"):
    if not USER_API_KEY:
        st.error("API 키를 입력해 주세요!")
    elif not user_input:
        st.error("내용을 입력해 주세요!")
    else:
        with st.spinner("Gemini AI가 각 장면에 완벽히 매치되는 고품질 인공지능 이미지를 직접 생성하고 비디오를 합성 중입니다... 약 1~2분 소요"):
            try:
                font_path = get_clean_font()
                client = genai.Client(api_key=USER_API_KEY)
                script_result = generate_shorts_script(client, user_input, creation_mode)
                
                if script_result:
                    assets_folder = "shorts_assets"
                    if not os.path.exists(assets_folder): os.makedirs(assets_folder)
                    
                    for scene in script_result["scenes"]:
                        # 1. 성우 음성 구우 기
                        tts = gTTS(text=scene["narration"], lang='ko', slow=False)
                        tts.save(f"{assets_folder}/scene_{scene['scene_number']}.mp3")
                        
                        # 2. 외부 허접한 사이트 대신, 구글 최고급 AI(Imagen 3) 엔진으로 1:1 맞춤형 사진 즉석 생성!!
                        img_prompt = scene.get("image_prompt", "A cozy cafe interior, vertical 9:16")
                        image_path = f"{assets_folder}/scene_{scene['scene_number']}.jpg"
                        
                        try:
                            result = client.models.generate_images(
                                model='imagen-3.0-generate-002',
                                prompt=img_prompt,
                                config=types.GenerateImagesConfig(
                                    number_of_images=1,
                                    aspect_ratio="9:16", # 쇼츠 규격 세로 고정
                                    output_mime_type="image/jpeg"
                                )
                            )
                            for generated_image in result.generated_images:
                                with open(image_path, "wb") as f:
                                    f.write(generated_image.image.image_bytes)
                        except Exception as img_err:
                            # 만약 이미지 생성 제한이 걸리면 백업용 랜덤 이미지 작동
                            try: urllib.request.urlretrieve(f"https://picsum.photos/1080/1920", image_path)
                            except: pass
                            
                    video_file_path = make_final_video(script_result, font_path)
                    
                    st.success("🎉 자막 및 1:1 AI 커스텀 이미지 쇼츠 제작 대성공!")
                    with open(video_file_path, "rb") as file:
                        st.download_button(
                            label="📥 완성된 쇼츠 영상 다운로드 받기",
                            data=file,
                            file_name="my_perfect_ai_shorts.mp4",
                            mime="video/mp4"
                        )
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")