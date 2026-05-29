import os
import json
import urllib.request
from google import genai
from google.genai import types
from gtts import gTTS
import moviepy

# 최신 2.0+ 버전에서 가장 에러 없는 다이렉트 경로 지정
ImageClip = moviepy.ImageClip
AudioFileClip = moviepy.AudioFileClip
concatenate_videoclips = moviepy.concatenate_videoclips

API_KEY = "AQ.Ab8RN6J3oC3Z7PJWe2tQCPNMCWYQrWV0G4jJF5DOOY15MERIcQ"
client = genai.Client(api_key=API_KEY)

def generate_shorts_script(topic):
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
                "keyword": "history"
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
    print("\n🎬 4단계: 최종 쇼츠 영상 생성을 시작합니다. (렌더링)")
    assets_folder = "shorts_assets"
    scenes = script_data.get("scenes", [])
    
    video_clips = []
    
    for scene in scenes:
        num = scene["scene_number"]
        image_path = f"{assets_folder}/scene_{num}.jpg"
        audio_path = f"{assets_folder}/scene_{num}.mp3"
        
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        # 구버전/최신버전 문법 모두 방어
        try:
            image_clip = ImageClip(image_path).with_duration(duration).with_audio(audio_clip)
        except:
            image_clip = ImageClip(image_path).set_duration(duration).set_audio(audio_clip)
            
        video_clips.append(image_clip)
        print(f"📹 [{num}번 장면] 비디오+오디오 합성 준비 완료 ({duration:.1f}초)")
        
    print("\n📦 모든 장면을 하나로 이어 붙이는 중입니다...")
    final_video = concatenate_videoclips(video_clips, method="compose")
    final_video.write_videofile("final_shorts.mp4", fps=24, codec="libx264", audio_codec="aac")
    print("\n🎉 대성공! 최종 영상이 'final_shorts.mp4' 파일로 저장되었습니다!")

if __name__ == "__main__":
    test_topic = "직장인 공감 유머 TOP 3"
    script_result = generate_shorts_script(test_topic)
    
    if script_result:
        assets_folder = "shorts_assets"
        if not os.path.exists(assets_folder): os.makedirs(assets_folder)
        
        for scene in script_result["scenes"]:
            tts = gTTS(text=scene["narration"], lang='ko', slow=False)
            tts.save(f"{assets_folder}/scene_{scene['scene_number']}.mp3")
            
            image_path = f"{assets_folder}/scene_{scene['scene_number']}.jpg"
            search_url = f"https://picsum.photos/1080/1920"
            try:
                urllib.request.urlretrieve(search_url, image_path)
            except:
                pass
                
        make_final_video(script_result)