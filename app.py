import streamlit as st
import os
import subprocess
import math
import concurrent.futures
import asyncio
import edge_tts
import time
import shutil
import gc

# TTS Voices, Recap Styles, and Emotions from PDF analysis
@st.cache_resource
def get_voices():
    return [
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

@st.cache_resource
def get_recap_styles():
    return [
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

@st.cache_resource
def get_emotions():
    return [
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

VOICES = get_voices()
RECAP_STYLES = get_recap_styles()
EMOTIONS = get_emotions()

st.set_page_config(page_title="Video & Text Processor", layout="wide")

def count_paragraphs(text):
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    return paragraphs

def generate_tts(text, output_path, voice_id="v1", speed=0, pitch=0):
    """Generate TTS with thread-safe asyncio loop to prevent event loop crashes."""
    voice_num = int(voice_id.replace('v', ''))
    real_voice = "my-MM-ThihaNeural" if voice_num % 2 == 0 else "my-MM-NilarNeural"
    rate_str = f"+{speed}%" if speed >= 0 else f"{speed}%"
    pitch_str = f"+{pitch}Hz" if pitch >= 0 else f"{pitch}Hz"
    
    # Create a new event loop for this thread (thread-safe)
    loop = asyncio.new_event_loop()
    try:
        async def _generate():
            communicate = edge_tts.Communicate(text, real_voice, rate=rate_str, pitch=pitch_str)
            await communicate.save(output_path)
        loop.run_until_complete(_generate())
    finally:
        loop.close()
    return output_path

async def generate_all_tts(paragraphs, audio_dir, voice_id, speed, pitch):
    """Generate TTS for all paragraphs in parallel using asyncio.gather (network I/O safe)."""
    tasks = []
    for i, paragraph in enumerate(paragraphs):
        tasks.append(generate_tts_async(paragraph, os.path.join(audio_dir, f"audio_{i}.mp3"), voice_id, speed, pitch))
    await asyncio.gather(*tasks)

async def generate_tts_async(text, output_path, voice_id, speed, pitch):
    """Async TTS generation for parallel execution."""
    voice_num = int(voice_id.replace('v', ''))
    real_voice = "my-MM-ThihaNeural" if voice_num % 2 == 0 else "my-MM-NilarNeural"
    rate_str = f"+{speed}%" if speed >= 0 else f"{speed}%"
    pitch_str = f"+{pitch}Hz" if pitch >= 0 else f"{pitch}Hz"
    communicate = edge_tts.Communicate(text, real_voice, rate=rate_str, pitch=pitch_str)
    await communicate.save(output_path)
    return output_path

def get_video_duration(video_path):
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return float(result.stdout.strip())

def get_video_resolution(video_path):
    cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=s=x:p=0', video_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    res = result.stdout.strip().split('x')
    w, h = int(res[0]), int(res[1])
    # Cap resolution at 1080p for stability on Streamlit Cloud
    if w > 1920:
        h = int(h * (1920 / w))
        w = 1920
    return w, h

def get_audio_duration(audio_path):
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return float(result.stdout.strip())

def split_video(video_path, num_segments, output_dir):
    """Split video into segments with re-encoding for accurate frame-level cutting."""
    duration = get_video_duration(video_path)
    segment_duration = duration / num_segments
    segments = []
    for i in range(num_segments):
        start_time = i * segment_duration
        output_path = os.path.join(output_dir, f"segment_{i}.mp4")
        # Use -c:v libx264 -preset fast -c:a aac for accurate segment splitting
        # (not -c copy, which cuts at keyframes only and causes duration inaccuracy)
        cmd = ['ffmpeg', '-y', '-ss', str(start_time), '-t', str(segment_duration),
               '-i', video_path, '-c:v', 'libx264', '-preset', 'fast', '-c:a', 'aac',
               '-avoid_negative_ts', 'make_zero', output_path]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        segments.append(output_path)
    return segments, segment_duration

def process_segment_with_retry(index, text, video_segment, audio_path, final_segments_dir, voice_id, speed, pitch, play_dur, freeze1_dur, freeze1_zoom, freeze2_dur, freeze2_zoom, max_retries=3):
    """Process segment with retry logic"""
    for attempt in range(max_retries):
        try:
            # 1. Generate TTS if not already done (thread-safe single call)
            if not os.path.exists(audio_path):
                generate_tts(text, audio_path, voice_id, speed, pitch)
            
            audio_duration = get_audio_duration(audio_path)
            orig_segment_duration = get_video_duration(video_segment)
            output_segment = os.path.join(final_segments_dir, f"segment_{index}.mp4")
            
            # 2. Build FFmpeg filter complex
            width, height = get_video_resolution(video_segment)
            cycle_duration = play_dur + freeze1_dur + freeze2_dur
            num_cycles = math.ceil(audio_duration / cycle_duration)
            
            # Cap resolution at 720p to reduce memory usage on Streamlit Cloud
            if width > 1280:
                height = int(height * (1280 / width))
                width = 1280
            
            res_str = f"{width}x{height}"
            fps = 30
            # Calculate total frames for each freeze section
            f1_frames = freeze1_dur * fps
            f2_frames = freeze2_dur * fps
            
            # Zoom expressions: total zoom change over freeze_duration
            # Zoom In: from 1.0 to 1.15 (15% zoom) over freeze duration
            # Zoom Out: from 1.15 to 1.0 (back to normal) over freeze duration
            # Use on=1 to track frame number, compute zoom per frame
            zoom_in = f"scale={width}:{height},setsar=1,zoompan=z='min(1+0.15*on/{f1_frames},1.15)':d={f1_frames}:s={res_str}:fps={fps}"
            zoom_out = f"scale={width}:{height},setsar=1,zoompan=z='max(1.15-0.15*on/{f1_frames},1.0)':d={f1_frames}:s={res_str}:fps={fps}"
            no_zoom = f"scale={width}:{height},setsar=1,loop=loop=-1:size=1:start=0,trim=duration={freeze1_dur}"
            
            # Build freeze1 filter (for freeze1_dur duration)
            f1_frames_calc = freeze1_dur * fps
            if freeze1_zoom == "Zoom In":
                f1_z = f"scale={width}:{height},setsar=1,zoompan=z='min(1+0.15*on/{f1_frames_calc},1.15)':d={f1_frames_calc}:s={res_str}:fps={fps}"
            elif freeze1_zoom == "Zoom Out":
                f1_z = f"scale={width}:{height},setsar=1,zoompan=z='max(1.15-0.15*on/{f1_frames_calc},1.0)':d={f1_frames_calc}:s={res_str}:fps={fps}"
            else:
                f1_z = None  # No zoom, just freeze frame
            
            # Build freeze2 filter (for freeze2_dur duration)
            f2_frames_calc = freeze2_dur * fps
            if freeze2_zoom == "Zoom In":
                f2_z = f"scale={width}:{height},setsar=1,zoompan=z='min(1+0.15*on/{f2_frames_calc},1.15)':d={f2_frames_calc}:s={res_str}:fps={fps}"
            elif freeze2_zoom == "Zoom Out":
                f2_z = f"scale={width}:{height},setsar=1,zoompan=z='max(1.15-0.15*on/{f2_frames_calc},1.0)':d={f2_frames_calc}:s={res_str}:fps={fps}"
            else:
                f2_z = None  # No zoom, just freeze frame
            
            filter_parts = []
            concat_inputs = []
            speed_factor = audio_duration / orig_segment_duration
            filter_parts.append(f"[0:v]setpts=PTS*{speed_factor}[v_speed];")
            
            for i in range(num_cycles):
                curr = i * cycle_duration
                # Play section: normal video playback
                filter_parts.append(f"[v_speed]trim=start={curr}:end={curr+play_dur},setpts=PTS-STARTPTS[vplay_{i}];")
                concat_inputs.append(f"[vplay_{i}]")
                
                # Freeze 1 section: freeze frame with optional zoom
                f1_trim_start = curr + play_dur
                if f1_z:
                    filter_parts.append(f"[v_speed]trim=start={f1_trim_start},select=eq(n\\,0),setpts=PTS-STARTPTS{f1_z}[vf1_{i}];")
                else:
                    filter_parts.append(f"[v_speed]trim=start={f1_trim_start},select=eq(n\\,0),setpts=PTS-STARTPTS,loop=loop=-1:size=1:start=0,trim=duration={freeze1_dur}[vf1_{i}];")
                concat_inputs.append(f"[vf1_{i}]")
                
                # Freeze 2 section: freeze frame with optional zoom
                f2_trim_start = curr + play_dur + freeze1_dur
                if f2_z:
                    filter_parts.append(f"[v_speed]trim=start={f2_trim_start},select=eq(n\\,0),setpts=PTS-STARTPTS{f2_z}[vf2_{i}];")
                else:
                    filter_parts.append(f"[v_speed]trim=start={f2_trim_start},select=eq(n\\,0),setpts=PTS-STARTPTS,loop=loop=-1:size=1:start=0,trim=duration={freeze2_dur}[vf2_{i}];")
                concat_inputs.append(f"[vf2_{i}]")
            
            filter_parts.append(f"{''.join(concat_inputs)}concat=n={len(concat_inputs)}:v=1:a=0[vcomb];")
            filter_complex = ''.join(filter_parts) + f"[vcomb][1:a]concat=n=1:v=1:a=1,trim=duration={audio_duration}[v]"
            
            cmd = ['ffmpeg', '-y', '-i', video_segment, '-i', audio_path, '-filter_complex', filter_complex, '-map', '[v]', '-shortest', output_segment]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if result.returncode == 0 and os.path.exists(output_segment):
                # Clean up temp segment after successful processing to save disk space
                if os.path.exists(video_segment):
                    os.remove(video_segment)
                return output_segment
            else:
                raise Exception(f"FFmpeg failed: {result.stderr}")
                
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retry
                continue
            else:
                raise e

def merge_videos(video_list, output_path):
    valid_videos = [v for v in video_list if v is not None and os.path.exists(v)]
    if not valid_videos:
        raise Exception("No valid segments to merge.")
    concat_file = "concat_list.txt"
    with open(concat_file, 'w') as f:
        for video in valid_videos:
            f.write(f"file '{os.path.abspath(video)}'\n")
    cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_file, '-c', 'copy', output_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if os.path.exists(concat_file):
        os.remove(concat_file)
    if result.returncode != 0:
        raise Exception(f"Merge Error: {result.stderr}")

def main():
    st.title("🎬 Video & Text Processor with TTS")
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
        final_speed, final_pitch = style_data["speed"] + emotion_data["s"], style_data["pitch"] + emotion_data["p"]
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
            st.error("❌ Provide text and video.")
            return
        
        # Early cleanup of previous temp files
        temp_dir = "temp_processing"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        audio_dir, video_dir, final_segments_dir = [os.path.join(temp_dir, d) for d in ["audio", "video", "final_segments"]]
        for d in [audio_dir, video_dir, final_segments_dir]:
            os.makedirs(d, exist_ok=True)
        video_path = os.path.join(video_dir, "input_video.mp4")
        
        # Chunk-by-chunk write to save RAM
        with open(video_path, "wb") as f:
            while chunk := video_file.read(8192):
                f.write(chunk)
        
        paragraphs = count_paragraphs(text_input)
        num_paragraphs = len(paragraphs)
        progress_bar = st.progress(0)
        
        # Force garbage collection to free RAM after file write
        del video_file
        gc.collect()
        
        with st.status("🚀 Processing...", expanded=True) as status:
            # Step 1: Generate all TTS audio in parallel using asyncio (network I/O, not CPU-bound)
            st.write("🎙️ Generating TTS audio...")
            asyncio.run(generate_all_tts(paragraphs, audio_dir, voice_id, final_speed, final_pitch))
            st.write("✅ TTS generation complete.")
            
            # Step 2: Split video into segments
            st.write("🎞️ Splitting video...")
            video_segments, _ = split_video(video_path, num_paragraphs, video_dir)
            st.write("✅ Video splitting complete.")
            
            # Delete the original uploaded video to save disk space
            if os.path.exists(video_path):
                os.remove(video_path)
                st.write("🗑️ Original uploaded video removed to save space.")
            
            # Force garbage collection to free RAM
            gc.collect()
            
            # Step 3: Edit video segments with 2 workers (CPU-bound FFmpeg)
            st.write("🎬 Editing video segments...")
            final_video_segments = [None] * num_paragraphs
            completed = 0
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future_to_index = {
                    executor.submit(
                        process_segment_with_retry,
                        i, paragraphs[i], video_segments[i],
                        os.path.join(audio_dir, f"audio_{i}.mp3"),
                        final_segments_dir, voice_id, final_speed, final_pitch,
                        play_duration, freeze1_duration, freeze1_zoom,
                        freeze2_duration, freeze2_zoom
                    ): i
                    for i in range(num_paragraphs)
                }
                for future in concurrent.futures.as_completed(future_to_index):
                    index = future_to_index[future]
                    try:
                        final_video_segments[index] = future.result()
                        completed += 1
                        st.write(f"✅ Segment {index+1}/{num_paragraphs} processed")
                        progress_bar.progress(completed / num_paragraphs)
                    except Exception as e:
                        st.error(f"❌ Failed segment {index+1} after retries: {str(e)}")
            
            # Step 4: Merge final video
            st.write("🎞️ Merging final video...")
            output_video = "final_output.mp4"
            try:
                merge_videos(final_video_segments, output_video)
                status.update(label="✅ Complete!", state="complete")
            except Exception as e:
                st.error(f"❌ Merge Failed: {str(e)}")
                status.update(label="❌ Failed", state="error")
                return
        
        if os.path.exists(output_video):
            # Download directly from file path without loading into RAM
            st.download_button(
                "📥 Download Final Video",
                data=open(output_video, "rb"),
                file_name="output_video.mp4",
                mime="video/mp4"
            )
        
        # Cleanup all temp files
        shutil.rmtree(temp_dir, ignore_errors=True)
        if os.path.exists(output_video):
            os.remove(output_video)

if __name__ == "__main__":
    main()
