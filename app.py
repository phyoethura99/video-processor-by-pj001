import streamlit as st
import os
import subprocess
import json
import math
import concurrent.futures
import asyncio
import edge_tts
from pathlib import Path

# TTS Voices, Recap Styles, and Emotions from PDF analysis
VOICES = [
    {"id": "v1", "name": "ကို စိုင်းစိုင်း", "gender": "ယောက်ျားလေး"},
    {"id": "v2", "name": "မဖွေးဖွေး", "gender": "မိန်းကလေး"},
    {"id": "v3", "name": "ကို နေတိုး", "gender": "ယောက်ျားလေး"},
    {"id": "v4", "name": "ကို အောင်ရဲလင်း", "gender": "ယောက်ျားလေး"},
    {"id": "v5", "name": "ကို မြင့်မြတ်", "gender": "ယောက်ျားလေး"},
    {"id": "v6", "name": "မဝတ်မှုံ ရွှေရည်", "gender": "မိန်းကလေး"},
    {"id": "v7", "name": "ကို ဒေါင်း", "gender": "ယောက်ျားလေး"},
    {"id": "v8", "name": "မသက်မွန်မြင့်", "gender": "မိန်းကလေး"},
    {"id": "v9", "name": "ကို လူ မင်း", "gender": "ယောက်ျားလေး"},
    {"id": "v10", "name": "မအိန္ဒြာကျော်ဇင်", "gender": "မိန်းကလေး"},
    {"id": "v11", "name": "မရွှေမှုံ ရတီ", "gender": "မိန်းကလေး"},
    {"id": "v12", "name": "ကို ပြေတီဦး", "gender": "ယောက်ျားလေး"},
    {"id": "v13", "name": "မသင်ဇာဝင့်ကျော်", "gender": "မိန်းကလေး"},
    {"id": "v14", "name": "ကို ပိုင်တံခွန်", "gender": "ယောက်ျားလေး"}
]

RECAP_STYLES = [
    {"id": "Normal", "name": "ပုံမှန်အသံ", "speed": 0, "pitch": 0},
    {"id": "NyoGyi_25", "name": "ကျားကြီး ၁", "speed": 0, "pitch": 25},
    {"id": "NyoGyi_35", "name": "ကျားကြီး ၂", "speed": 0, "pitch": 35},
    {"id": "NyoGyi_45", "name": "ကျားကြီး ၃", "speed": 0, "pitch": 45},
    {"id": "Nilar_40", "name": "နီလာ ချွဲသံ", "speed": 0, "pitch": 40},
    {"id": "Combo_15", "name": "ပေါင်းစပ် ၁၅", "speed": 15, "pitch": 15},
    {"id": "Combo_30", "name": "ပေါင်းစပ် ၃၀", "speed": 30, "pitch": 30},
    {"id": "Combo_50", "name": "ပေါင်းစပ် ၅၀", "speed": 50, "pitch": 50},
    {"id": "Pitch_20", "name": "အသံသေး ၂၀", "speed": 0, "pitch": 20},
    {"id": "Pitch_50", "name": "အသံသေး ၅၀", "speed": 0, "pitch": 50}
]

EMOTIONS = [
    {"id": "EXCITING", "name": "စိတ်လှုပ်ရှား 🤩", "s": 15, "p": 10},
    {"id": "CALM", "name": "တည်ငြိမ် 😌", "s": -10, "p": -5},
    {"id": "PROFESSIONAL", "name": "သတင်း 💼", "s": 0, "p": -2},
    {"id": "NARRATIVE", "name": "ဇာတ်ကြောင်း 📖", "s": -5, "p": 0},
    {"id": "HAPPY", "name": "ပျော်ရွှင် 😊", "s": 10, "p": 15},
    {"id": "SERIOUS", "name": "လေးနက် 😠", "s": -5, "p": -10},
    {"id": "WHISPER", "name": "တီးတိုး 🤫", "s": -15, "p": -20},
    {"id": "SAD", "name": "ဝမ်းနည်း 😢", "s": -15, "p": -15},
    {"id": "SARCASTIC", "name": "ရွဲ့ပြော 🙄", "s": -10, "p": 5},
    {"id": "ANGRY", "name": "ဒေါသထွက် 🤬", "s": 20, "p": -10},
    {"id": "FEAR", "name": "ကြောက်လန့် 😨", "s": 10, "p": 20}
]

st.set_page_config(page_title="Video & Text Processor", layout="wide")

def count_paragraphs(text):
    """Count paragraphs in text (separated by double newlines)"""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    return paragraphs

def generate_tts(text, output_path, voice_id="v1", speed=0, pitch=0):
    """Generate TTS audio using edge_tts with actual Myanmar voices"""
    voice_num = int(voice_id.replace('v', ''))
    if voice_num % 2 == 0:
        real_voice = "my-MM-ThihaNeural"
    else:
        real_voice = "my-MM-NilarNeural"
    
    rate_str = f"+{speed}%" if speed >= 0 else f"{speed}%"
    pitch_str = f"+{pitch}Hz" if pitch >= 0 else f"{pitch}Hz"
    
    async def _generate():
        communicate = edge_tts.Communicate(text, real_voice, rate=rate_str, pitch=pitch_str)
        await communicate.save(output_path)
        
    asyncio.run(_generate())
    return output_path

def get_video_duration(video_path):
    """Get video duration in seconds"""
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1:noprint_wrappers=1', video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return float(result.stdout)

def get_audio_duration(audio_path):
    """Get audio duration in seconds"""
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1:noprint_wrappers=1', audio_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return float(result.stdout)

def split_video(video_path, num_segments):
    """Split video into equal segments"""
    duration = get_video_duration(video_path)
    segment_duration = duration / num_segments
    
    segments = []
    for i in range(num_segments):
        start_time = i * segment_duration
        output_path = f"temp_segment_{i}.mp4"
        cmd = [
            'ffmpeg', '-y', '-ss', str(start_time), '-t', str(segment_duration),
            '-i', video_path, '-c', 'copy', output_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        segments.append(output_path)
    return segments, segment_duration

def process_segment(index, text, video_segment, audio_dir, final_segments_dir, voice_id, speed, pitch, play_dur, freeze1_dur, freeze1_zoom, freeze2_dur, freeze2_zoom):
    """Process a single segment with TTS and video editing"""
    # 1. Generate TTS
    audio_path = os.path.join(audio_dir, f"audio_{index}.mp3")
    generate_tts(text, audio_path, voice_id, speed, pitch)
    
    audio_duration = get_audio_duration(audio_path)
    orig_segment_duration = get_video_duration(video_segment)
    output_segment = os.path.join(final_segments_dir, f"segment_{index}.mp4")
    
    # 2. Build FFmpeg filter complex
    cycle_duration = play_dur + freeze1_dur + freeze2_dur
    num_cycles = math.ceil(audio_duration / cycle_duration)
    
    zoom_in_filter = "zoompan=z='min(zoom+0.0015,1.1)':d=1:s=hd720:fps=30"
    zoom_out_filter = "zoompan=z='max(zoom-0.0015,1.0)':d=1:s=hd720:fps=30"
    no_zoom_filter = "null"
    
    f1_zoom = zoom_in_filter if freeze1_zoom == "Zoom In" else (zoom_out_filter if freeze1_zoom == "Zoom Out" else no_zoom_filter)
    f2_zoom = zoom_in_filter if freeze2_zoom == "Zoom In" else (zoom_out_filter if freeze2_zoom == "Zoom Out" else no_zoom_filter)
    
    filter_parts = []
    concat_inputs = []
    speed_factor = audio_duration / orig_segment_duration
    filter_parts.append(f"[0:v]setpts=PTS*{speed_factor}[v_speed_adjusted];")
    
    for i in range(num_cycles):
        curr_start = i * cycle_duration
        
        # Play
        p_start, p_end = curr_start, curr_start + play_dur
        filter_parts.append(f"[v_speed_adjusted]trim=start={p_start}:end={p_end},setpts=PTS-STARTPTS[vplay_{i}];")
        concat_inputs.append(f"[vplay_{i}]")
        
        # Freeze 1
        f1_start = curr_start + play_dur
        filter_parts.append(f"[v_speed_adjusted]trim=start={f1_start},select=eq(n\\,0),setpts=PTS-STARTPTS,loop=loop=-1:size=1:start=0,trim=duration={freeze1_dur},{f1_zoom}[vfreeze1_{i}];")
        concat_inputs.append(f"[vfreeze1_{i}]")
        
        # Freeze 2
        f2_start = curr_start + play_dur + freeze1_dur
        filter_parts.append(f"[v_speed_adjusted]trim=start={f2_start},select=eq(n\\,0),setpts=PTS-STARTPTS,loop=loop=-1:size=1:start=0,trim=duration={freeze2_dur},{f2_zoom}[vfreeze2_{i}];")
        concat_inputs.append(f"[vfreeze2_{i}]")
    
    filter_parts.append(f"{''.join(concat_inputs)}concat=n={len(concat_inputs)}:v=1:a=0[vcombined];")
    filter_complex = ''.join(filter_parts) + f"[vcombined][1:a]concat=n=1:v=1:a=1,trim=duration={audio_duration}[v]"
    
    cmd = ['ffmpeg', '-y', '-i', video_segment, '-i', audio_path, '-filter_complex', filter_complex, '-map', '[v]', '-shortest', output_segment]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_segment

def merge_videos(video_list, output_path):
    """Merge multiple video segments into one"""
    # Filter out None values in case some segments failed
    valid_videos = [v for v in video_list if v is not None and os.path.exists(v)]
    if not valid_videos:
        raise Exception("No valid video segments found to merge.")

    concat_file = "concat_list.txt"
    with open(concat_file, 'w') as f:
        for video in valid_videos:
            f.write(f"file '{os.path.abspath(video)}'\n")
    
    cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_file, '-c', 'copy', output_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    if os.path.exists(concat_file):
        os.remove(concat_file)
        
    if result.returncode != 0:
        raise Exception(f"FFmpeg Merge Error: {result.stderr}")
    
    if not os.path.exists(output_path):
        raise Exception("Final output file was not created by FFmpeg.")

def main():
    st.title("🎬 Video & Text Processor with TTS")
    st.markdown("Processing text and video with custom effects and Myanmar TTS.")

    with st.sidebar:
        st.header("⚙️ Settings")
        selected_voice = st.selectbox("Select Voice", options=[v["name"] for v in VOICES])
        voice_id = next(v["id"] for v in VOICES if v["name"] == selected_voice)
        
        col1, col2 = st.columns(2)
        with col1:
            selected_style = st.selectbox("Recap Style", options=[s["name"] for s in RECAP_STYLES])
            style_data = next(s for s in RECAP_STYLES if s["name"] == selected_style)
        with col2:
            selected_emotion = st.selectbox("Emotion", options=[e["name"] for e in EMOTIONS])
            emotion_data = next(e for e in EMOTIONS if e["name"] == selected_emotion)
            
        final_speed = style_data["speed"] + emotion_data["s"]
        final_pitch = style_data["pitch"] + emotion_data["p"]
        st.caption(f"📊 Speed: {final_speed}%, Pitch: {final_pitch}Hz")
        
        st.markdown("---")
        play_duration = st.slider("▶️ Play Duration (s)", 1, 5, 3)
        col3, col4 = st.columns(2)
        with col3:
            freeze1_duration = st.slider("❄️ Freeze 1 (s)", 1, 3, 1)
            freeze1_zoom = st.selectbox("Zoom 1", ["None", "Zoom In", "Zoom Out"])
        with col4:
            freeze2_duration = st.slider("❄️ Freeze 2 (s)", 1, 3, 1)
            freeze2_zoom = st.selectbox("Zoom 2", ["None", "Zoom In", "Zoom Out"])
            
        st.markdown("---")
        text_input = st.text_area("📝 Enter Text", height=200)
        if text_input:
            paragraphs = count_paragraphs(text_input)
            st.info(f"📊 Paragraphs: {len(paragraphs)} | Characters: {len(text_input)}")
        
        video_file = st.file_uploader("🎥 Upload Video", type=["mp4", "mov", "avi"])

    if st.button("🚀 Start Processing"):
        if not text_input or not video_file:
            st.error("❌ Please provide both text and a video file.")
            return
        
        temp_dir = "temp_processing"
        audio_dir, video_dir, final_segments_dir = [os.path.join(temp_dir, d) for d in ["audio", "video", "final_segments"]]
        for d in [audio_dir, video_dir, final_segments_dir]: os.makedirs(d, exist_ok=True)
        
        video_path = os.path.join(video_dir, "input_video.mp4")
        with open(video_path, "wb") as f: f.write(video_file.read())
        
        paragraphs = count_paragraphs(text_input)
        num_paragraphs = len(paragraphs)
        
        # UI for detailed progress
        status_placeholder = st.empty()
        progress_bar = st.progress(0)
        
        with st.status("🚀 Processing...", expanded=True) as status:
            st.write("🎞️ Splitting video into segments...")
            video_segments, _ = split_video(video_path, num_paragraphs)
            
            final_video_segments = [None] * num_paragraphs
            completed = 0
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                future_to_index = {
                    executor.submit(process_segment, i, paragraphs[i], video_segments[i], audio_dir, final_segments_dir, voice_id, final_speed, final_pitch, play_duration, freeze1_duration, freeze1_zoom, freeze2_duration, freeze2_zoom): i 
                    for i in range(num_paragraphs)
                }
                
                for future in concurrent.futures.as_completed(future_to_index):
                    index = future_to_index[future]
                    try:
                        final_video_segments[index] = future.result()
                        completed += 1
                        st.write(f"✅ Segment {index+1}/{num_paragraphs} complete")
                        progress_bar.progress(completed / num_paragraphs)
                    except Exception as e:
                        st.error(f"❌ Error in segment {index+1}: {str(e)}")
            
            st.write("🎞️ Merging final video...")
            output_video = "final_output.mp4"
            try:
                merge_videos(final_video_segments, output_video)
                status.update(label="✅ Processing Complete!", state="complete")
            except Exception as e:
                st.error(f"❌ Merge Failed: {str(e)}")
                status.update(label="❌ Processing Failed", state="error")
                return
        
        if os.path.exists(output_video):
            with open(output_video, "rb") as f:
                st.download_button("📥 Download Final Video", f.read(), "output_video.mp4", "video/mp4")
        else:
            st.error("❌ Final video file not found. Please try again.")
        
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
