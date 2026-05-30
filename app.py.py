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
st.title("🎬 AI 멀티 쇼츠 자동 제작기 (유튜브 대본 + 블로그 요약 겸용)")
st.write("선택한 모드에 맞춰 대본을 생성하고 영상과 한글 자막을 자동으로 합성합니다.")

USER_API_KEY = st.text_input("🔑 본인의 Gemini API 키를 입력하세요", type="password")

# [핵심] 사용자가 직접 모드를 선택하는 라디오 버튼 장치 추가!
creation_mode = st.radio(
    "📱 어떤 방식으로 영상을 제작하실 건가요?",
    ["💡 일반 유튜브 대본용 (주제 입력)", "📝 티스토리 블로그용 (본문 글 요약)"],
    horizontal=True
)

# 모드 선택에 따라 입력창 설명과 크기를 유연하게 변경
if "블로그" in creation_mode:
    user_input = st.text_area("✍️ 티스토리 블로그 본문 글을 통째로 복사해서 붙여넣으세요", placeholder="여기에 블로그 글 내용을 입력하세요...", height=250)
else:
    user_input = st.text_input("✍️ 쇼츠 영상 주제를 입력하세요", placeholder="예: 서울 멋진 카페리스트")

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
        except Exception as e:
            pass
    return font_path

def generate_shorts_script(client, content, mode):
    # 블로그 모드일 때와 일반 모드일 때 AI에게 주는 지시사항(프롬프트)을 완전히 다르게 분기시킵니다.
    if "블로그" in mode:
        prompt = f"""
        너는 블로그 전문 요약 크리에이터야.
        제공된 블로그 본문 내용인 '{content}'을 완벽하게 분석해서 시청자들이 30초 만에 이해할 수 있도록 핵심 위주로 요약한 쇼츠 대본을 작성해줘.
        
        반드시 아래의 JSON 포맷으로만 답변해야 해. 다른 부연 설명은 절대 하지 마.
        {{
            "title": "블로그 요약 쇼츠 제목",
            "scenes": [
                {{
                    "scene_number": 1,
                    "narration": "첫 번째 핵심 요약 내용 (친근한 말투로)",
                    "keyword": "이 장면의 핵심 소재와 매칭되는 구체적인 영어 단어 하나 (예: 노트북 글이면 'laptop', 맛집 글이면 'food', 리뷰면 'review')"
                }}
            ]
        }}
        조건: 총 scene은 3~4개로 요약 구성. keyword는 오직 영어 단어 하나여야 함.
        """
    else:
        prompt = f"""
        너는 유튜브 쇼츠 전문 크리에이터야.
        주제인 '{content}'에 대해 시청자의 이탈을 막을 수 있는 흥미진진한 30초 분량의 쇼츠 대본을 작성해줘.
        반드시 아래의 JSON 포맷으로만 답변해야 해. 다른 부연 설명은 절대 하지 마.
        {{
            "title": "쇼츠 제목",
            "scenes": [
                {{
                    "scene_number": 1,
                    "narration": "첫 번째 장면 나레이션 내용",
                    "keyword": "장면과 연관된 구체적인 영어 단어 하나 (예: coffee, laptop, travel, fashion)"
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

def make_final_video(script_data, font_path, mode):
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
        with st.spinner("선택하신 모드에 맞춰 AI가 영상을 굽는 중입니다... 약 1~2분 소요"):
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
                        
                        keyword = scene.get("keyword", "object")
                        image_path = f"{assets_folder}/scene_{scene['scene_number']}.jpg"
                        
                        # [핵심] 블로그 글 주제가 카페가 아닐 수 있으므로 만능 검색 엔진 가동!
                        # 만약 카페 주제라면 키워드 자체에 coffee나 cafe가 뽑혀 나오므로 완벽하게 대응됩니다.
                        search_url = f"https://loremflickr.com/1080/1920/{keyword},interior,clear,nice"
                        try:
                            req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req) as response, open(image_path, 'wb') as out_file:
                                out_file.write(response.read())
                        except:
                            try: urllib.request.urlretrieve(f"https://picsum.photos/1080/1920", image_path)
                            except: pass
                            
                    video_file_path = make_final_video(script_result, font_path, creation_mode)
                    
                    st.success("🎉 선택 모드 맞춤형 쇼츠 영상 제작 완료!")
                    with open(video_file_path, "rb") as file:
                        st.download_button(
                            label="📥 완성된 쇼츠 영상 다운로드 받기",
                            data=file,
                            file_name="my_hybrid_shorts.mp4",
                            mime="video/mp4"
                        )
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")