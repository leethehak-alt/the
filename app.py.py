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

st.set_page_config(page_title="AI 멀티 쇼츠 마스터 프로 v2", page_icon="🎬", layout="centered")

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
    # 최신 규격에 맞게 대본 구성과 전용 이미지 프롬프트 추출 지시를 강화합니다.
    prompt = f"""
    너는 유튜브 쇼츠 전문 크리에이터야. '{content}'를 기반으로 매혹적인 30초 쇼츠 대본을 작성해줘.
    반드시 아래의 JSON 포맷으로만 답변하고 다른 텍스트는 절대 포함하지 마.
    {{
        "video_title": "영상 상단에 고정할 강렬한 쇼츠 제목 (예: 서울 감성 카페 TOP 3)",
        "scenes": [
            {{
                "scene_number": 1,
                "narration": "첫 번째 장면 나레이션 문구 (한글 자막용)",
                "image_prompt": "이 나레이션 내용과 100% 일치하는 사진을 만들기 위한 사실적이고 구체적인 영어 묘사 (예: 'A photorealistic shot of a modern design cafe in Seoul, concrete wall, warm soft lighting, macro lens on a fresh cream dessert, vertical 9:16')"
            }}
        ]
    }}
    조건: 총 scene 3개로 구성. 모드가 블로그면 핵심 글 요약 위주로 분배할 것.
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
    
    # 1. 각 장면 클립 생성 및 싱크 타이밍 완전 동기화
    for scene in scenes:
        num = scene["scene_number"]
        text_content = scene["narration"]
        image_path = f"{assets_folder}/scene_{num}.jpg"
        audio_path = f"{assets_folder}/scene_{num}.mp3"
        
        # 오디오 길이를 정확히 파악하여 해당 장면의 '기준 시간'으로 삼음
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        # [교정] 이미지 클립의 재생 시간을 오디오 재생 시간과 칼같이 맞춤
        try: image_clip = ImageClip(image_path).with_duration(duration).resized((1080, 1920))
        except: image_clip = ImageClip(image_path).set_duration(duration).resize((1080, 1920))
            
        # 하단 나레이션 자막 클립 (시간 완전 일치)
        try:
            sub_clip = (TextClip(text=text_content, font_size=42, color="white", font=font_path, size=(900, None), method="caption")
                         .with_duration(duration)
                         .with_position(("center", 1450)))
        except:
            sub_clip = (TextClip(text_content, fontsize=42, color="white", font=font_path, size=(900, None), method="caption")
                         .set_duration(duration)
                         .set_position(("center", 1450)))
        
        try: scene_clip = CompositeVideoClip([image_clip, sub_clip]).with_audio(audio_clip)
        except: scene_clip = CompositeVideoClip([image_clip, sub_clip]).set_audio(audio_clip)
            
        video_clips.append(scene_clip)
    
    # 2. 개별 순서대로 클립들을 끈김없이 정렬 합체
    final_concat = concatenate_videoclips(video_clips, method="compose")
    total_duration = final_concat.duration
    
    # 3. [교정] 생성된 자막 제목을 영상 "상단"에 노란색 고정 타이틀로 레이어 얹기
    try:
        top_title_clip = (TextClip(text=video_title_text, font_size=70, color="yellow", font=font_path, stroke_color="black", stroke_width=3)
                          .with_duration(total_duration)
                          .with_position(("center", 220)))
    except:
        top_title_clip = (TextClip(video_title_text, fontsize=70, color="yellow", font=font_path)
                          .set_duration(total_duration)
                          .set_position(("center", 220)))
    
    # 4. 전체 타임라인 병합 오버레이
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
        with st.spinner("AI가 매칭 텍스트와 타이틀을 상단에 인쇄하며, 각 프레임별 전용 이미지를 생성하는 중입니다..."):
            try:
                font_path = get_clean_font()
                client = genai.Client(api_key=USER_API_KEY)
                script_result = generate_shorts_script(client, user_input, creation_mode)
                
                if script_result:
                    assets_folder = "shorts_assets"
                    if not os.path.exists(assets_folder): os.makedirs(assets_folder)
                    
                    for scene in script_result["scenes"]:
                        # 1. 성우 파일 쓰기
                        tts = gTTS(text=scene["narration"], lang='ko', slow=False)
                        tts.save(f"{assets_folder}/scene_{scene['scene_number']}.mp3")
                        
                        # 2. [완벽 교정] 엉뚱한 외부 링크 대신 Gemini 2.5 고유 모달리티 다이렉트 이미지 드로잉 사용!
                        img_prompt = scene.get("image_prompt", "A clean visual slide, vertical 9:16")
                        image_path = f"{assets_folder}/scene_{scene['scene_number']}.jpg"
                        
                        try:
                            # 2.5 전용 고해상도 드로잉 엔진 스위칭
                            img_response = client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=f"Generate a beautiful 9:16 ratio vertical illustration image based on this description: {img_prompt}",
                                config=types.GenerateContentConfig(
                                    response_modalities=["IMAGE"],
                                    image_config=types.ImageConfig(aspect_ratio="9:16")
                                )
                            )
                            # 바이너리 이미지 데이터 파싱 후 완벽 저장
                            for part in img_response.parts:
                                if part.inline_data:
                                    with open(image_path, "wb") as f:
                                        f.write(part.inline_data.data)
                        except Exception as drawing_err:
                            # 만약 계정 한도 초과 오류 발생 시, 차선책으로 풍경이 아닌 '카페 고정 테마 이미지 키워드' 강제 매칭 다운로드
                            try:
                                clean_keyword = img_prompt.split(",")[0].replace(" ", "")
                                search_url = f"https://loremflickr.com/1080/1920/{clean_keyword},cafe,interior"
                                req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
                                with urllib.request.urlopen(req) as response, open(image_path, 'wb') as out_file:
                                    out_file.write(response.read())
                            except:
                                urllib.request.urlretrieve(f"https://picsum.photos/1080/1920", image_path)
                            
                    video_file_path = make_final_video(script_result, font_path)
                    
                    st.success(f"🎉 영상 상단 고정 대제목: '{script_result['video_title']}' 합성 완료!")
                    with open(video_file_path, "rb") as file:
                        st.download_button(label="📥 완성된 완벽 싱크 쇼츠 영상 다운로드", data=file, file_name="final_perfect_shorts.mp4", mime="video/mp4")
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")