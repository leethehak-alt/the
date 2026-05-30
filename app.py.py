import os
import json
import urllib.request
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

st.set_page_config(page_title="AI 멀티 쇼츠 마스터 프로", page_icon="🎬", layout="centered")

# [1] 화면 상단 모드 선택
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
    if not os.path.exists(font_dir): os.makedirs(font_dir)
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
    # AI에게 영상 상단에 넣을 '강렬한 제목'도 함께 생성하라고 명령합니다.
    prompt = f"""
    너는 유튜브 쇼츠 전문 크리에이터야. '{content}'를 바탕으로 쇼츠 대본을 작성해줘.
    반드시 아래의 JSON 포맷으로만 답변해.
    {{
        "video_title": "시청자를 사로잡을 강력한 영상 상단 제목 (예: 서울 카페 TOP 3)",
        "scenes": [
            {{
                "scene_number": 1,
                "narration": "장면 나레이션",
                "image_prompt": "이미지 생성용 디테일한 영어 프롬프트 (vertical 9:16 강조)"
            }}
        ]
    }}
    조건: 총 scene 3~4개. 모드가 블로그면 핵심 요약 위주로 작성.
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
    video_title_text = script_data.get("video_title", "오늘의 추천")
    video_clips = []
    
    # 1. 먼저 전체 장면 클립을 만듭니다.
    for scene in scenes:
        num = scene["scene_number"]
        text_content = scene["narration"]
        image_path = f"{assets_folder}/scene_{num}.jpg"
        audio_path = f"{assets_folder}/scene_{num}.mp3"
        
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        try: image_clip = ImageClip(image_path).with_duration(duration).resized((1080, 1920))
        except: image_clip = ImageClip(image_path).set_duration(duration).resize((1080, 1920))
            
        # 하단 나레이션 자막 (흰색)
        try:
            sub_clip = (TextClip(text=text_content, font_size=45, color="white", font=font_path, size=(900, None), method="caption")
                         .with_duration(duration)
                         .with_position(("center", 1450)))
        except:
            sub_clip = (TextClip(text_content, fontsize=45, color="white", font=font_path, size=(900, None), method="caption")
                         .set_duration(duration)
                         .set_position(("center", 1450)))
        
        try: scene_clip = CompositeVideoClip([image_clip, sub_clip]).with_audio(audio_clip)
        except: scene_clip = CompositeVideoClip([image_clip, sub_clip]).set_audio(audio_clip)
            
        video_clips.append(scene_clip)
    
    # 2. 모든 장면을 합칩니다.
    final_concat = concatenate_videoclips(video_clips, method="compose")
    total_duration = final_concat.duration
    
    # 3. [대박 기능] 영상 상단에 고정될 '강력한 제목' 클립 추가 (노란색 강조)
    try:
        top_title_clip = (TextClip(text=video_title_text, font_size=75, color="yellow", font=font_path, stroke_color="black", stroke_width=2)
                          .with_duration(total_duration)
                          .with_position(("center", 200)))
    except:
        top_title_clip = (TextClip(video_title_text, fontsize=75, color="yellow", font=font_path)
                          .set_duration(total_duration)
                          .set_position(("center", 200)))
    
    # 4. 최종 합성 (배경 영상들 위에 상단 제목을 얹음)
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
        with st.spinner("AI가 상단 제목과 1:1 맞춤 이미지를 생성하여 영상을 제작 중입니다..."):
            try:
                font_path = get_clean_font()
                client = genai.Client(api_key=USER_API_KEY)
                script_result = generate_shorts_script(client, user_input, creation_mode)
                
                if script_result:
                    assets_folder = "shorts_assets"
                    if not os.path.exists(assets_folder): os.makedirs(assets_folder)
                    
                    for scene in script_result["scenes"]:
                        tts = gTTS(text=scene["narration"], lang='ko', slow=False)
                        tts.save(f"{assets_folder}/scene_{scene['scene_number']}.mp3")
                        
                        img_prompt = scene.get("image_prompt", "A high quality seoul cafe image, vertical 9:16")
                        image_path = f"{assets_folder}/scene_{scene['scene_number']}.jpg"
                        
                        # AI 이미지 직접 생성 엔진
                        try:
                            result = client.models.generate_images(
                                model='imagen-3.0-generate-002',
                                prompt=img_prompt,
                                config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="9:16", output_mime_type="image/jpeg")
                            )
                            for img in result.generated_images:
                                with open(image_path, "wb") as f: f.write(img.image.image_bytes)
                        except:
                            # 실패시 랜덤 이미지
                            urllib.request.urlretrieve(f"https://picsum.photos/1080/1920", image_path)
                            
                    video_file_path = make_final_video(script_result, font_path)
                    
                    st.success(f"🎉 '{script_result['video_title']}' 제목이 포함된 영상 제작 완료!")
                    with open(video_file_path, "rb") as file:
                        st.download_button(label="📥 완성된 쇼츠 영상 다운로드", data=file, file_name="ai_shorts_with_title.mp4", mime="video/mp4")
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")