import streamlit as st
import os
import subprocess
import json
import math
import concurrent.futures
from openai import OpenAI
from pathlib import Path

# Initialize OpenAI client
client = OpenAI()

# TTS Voices, Recap Styles, and Emotions from PDF analysis
# These will be used with edge_tts
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
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    return paragraphs

def get_video_duration(video_path):
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return float(result.stdout)

def split_video(video_path, output_dir, num_segments):
    duration = get_video_duration(video_path)
    segment_duration = duration / num_segments
    
    segments = []
    for i in range(num_segments):
        start_time = i * segment_duration
        output_path = os.path.join(output_dir, f"segment_{i}.mp4")
        cmd = [
            'ffmpeg', '-y', '-ss', str(start_time), '-t', str(segment_duration),
            '-i', video_path, '-c', 'copy', output_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        segments.append(output_path)
    return segments, segment_duration

import asyncio
import edge_tts

def generate_tts(text, output_path, voice_id="v1", speed=0, pitch=0):
    # Map custom voice IDs to actual edge_tts voices (assuming standard Myanmar voices or fallbacks)
    # Since edge_tts doesn't have native Myanmar voices named v1-v14, 
    # we will use a fallback or the closest available. 
    # For demonstration, we use a standard voice, but in a real app, 
    # this mapping should point to the exact Azure voice names.
    # Let's use a generic voice for now, and apply rate/pitch.
    real_voice = "en-US-AriaNeural" # Fallback voice
    
    # Format rate and pitch for edge_tts (e.g., "+10%", "-5Hz")
    rate_str = f"+{speed}%" if speed >= 0 else f"{speed}%"
    pitch_str = f"+{pitch}Hz" if pitch >= 0 else f"{pitch}Hz"
    
    async def _generate():
        communicate = edge_tts.Communicate(text, real_voice, rate=rate_str, pitch=pitch_str)
        await communicate.save(output_path)
        
    asyncio.run(_generate())
    return output_path

def get_audio_duration(audio_path):
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', audio_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return float(result.stdout)

def process_segment(index, text, video_segment, audio_dir, final_segments_dir, voice_id, speed, pitch, play_dur, freeze1_dur, freeze1_zoom, freeze2_dur, freeze2_zoom):
    # 1. Generate TTS
    audio_path = os.path.join(audio_dir, f"audio_{index}.mp3")
    generate_tts(text, audio_path, voice_id, speed, pitch)
    
    audio_duration = get_audio_duration(audio_path)
    
    # 2. Apply "3s play, 2s freeze" and adjust speed to match audio duration
    # This is a complex ffmpeg filter. 
    # For simplicity in this script, we'll first create the "freeze" effect and then scale it.
    # Effect: play 3s, freeze 2s. Total cycle 5s. 
    # If we want it to match audio_duration, we need to adjust the speed.
    
    output_segment = os.path.join(final_segments_dir, f"final_segment_{index}.mp4")
    
    # First, let's get the original segment duration
    orig_segment_duration = get_video_duration(video_segment)
    
    # Implementing custom play/freeze/zoom logic
    
    # 1. Speed adjust the entire video segment to match audio_duration
    temp_speed_adjusted_video = os.path.join(final_segments_dir, f"temp_speed_adjusted_{index}.mp4")
    speed_adjust_cmd = [
        'ffmpeg', '-y', '-i', video_segment,
        '-filter:v', f"setpts=PTS*{audio_duration/orig_segment_duration}",
        '-an', # No audio, we will add TTS later
        temp_speed_adjusted_video
    ]
    subprocess.run(speed_adjust_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Now, the temp_speed_adjusted_video has the same duration as audio_duration.
    # We need to apply the play/freeze/zoom cycle repeatedly over this video.
    
    # Define zoompan filters
    zoom_in_filter = "zoompan=z=\'min(zoom+0.0015,1.1)\\\'
:d=1:s=hd720:fps=30"
    zoom_out_filter = "zoompan=z=\'max(zoom-0.0015,1.0)\\\'
:d=1:s=hd720:fps=30"
    no_zoom_filter = "null"

    freeze1_zoom_filter = no_zoom_filter
    if freeze1_zoom == "Zoom In":
        freeze1_zoom_filter = zoom_in_filter
    elif freeze1_zoom == "Zoom Out":
        freeze1_zoom_filter = zoom_out_filter

    freeze2_zoom_filter = no_zoom_filter
    if freeze2_zoom == "Zoom In":
        freeze2_zoom_filter = zoom_in_filter
    elif freeze2_zoom == "Zoom Out":
        freeze2_zoom_filter = zoom_out_filter

    # Calculate the number of cycles needed
    cycle_duration = play_dur + freeze1_dur + freeze2_dur
    num_cycles = math.ceil(audio_duration / cycle_duration)

    filter_complex_parts = []
    concat_inputs = []

    # Input for the speed-adjusted video
    input_video_stream = "[0:v]"

    for i in range(num_cycles):
        current_cycle_start_time = i * cycle_duration
        
        # Play segment for this cycle
        play_start = current_cycle_start_time
        play_end = current_cycle_start_time + play_dur
        filter_complex_parts.append(
            f"{input_video_stream}trim=start={play_start}:end={play_end},setpts=PTS-STARTPTS[vplay_{i}];"
        )
        concat_inputs.append(f"[vplay_{i}]")

        # Freeze 1 segment for this cycle
        freeze1_frame_time = current_cycle_start_time + play_dur # Frame at the end of play
        filter_complex_parts.append(
            f"{input_video_stream}trim=start={freeze1_frame_time},select=eq(n\\,0),setpts=PTS-STARTPTS,loop=loop=-1:size=1:start=0,trim=duration={freeze1_dur},{freeze1_zoom_filter}[vfreeze1_{i}];"
        )
        concat_inputs.append(f"[vfreeze1_{i}]")

        # Freeze 2 segment for this cycle
        freeze2_frame_time = current_cycle_start_time + play_dur + freeze1_dur # Frame at the end of freeze1
        filter_complex_parts.append(
            f"{input_video_stream}trim=start={freeze2_frame_time},select=eq(n\\,0),setpts=PTS-STARTPTS,loop=loop=-1:size=1:start=0,trim=duration={freeze2_dur},{freeze2_zoom_filter}[vfreeze2_{i}];"
        )
        concat_inputs.append(f"[vfreeze2_{i}]")

    # Concatenate all cycles
    filter_complex_parts.append(
        f"{\'\'.join(concat_inputs)}concat=n={len(concat_inputs)}:v=1:a=0[vcombined];"
    )

    # Final command to add audio and trim to audio_duration
    filter_complex = 
        f"[0:v]setpts=PTS*{audio_duration/orig_segment_duration}[v_speed_adjusted];" + \
        \'\'.join(filter_complex_parts) + \
        f"[vcombined][1:a]concat=n=1:v=1:a=1,trim=duration={audio_duration}[v]"

    cmd = [
        \`ffmpeg\`, \`-y\`, \`-i\`, video_segment, \`-i\`, audio_path,
        \`-filter_complex\`, filter_complex,
        \`-map\`, \`[v]\`, \`-shortest\`, output_segment
    ]
    
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_segment

def main():
    st.title("🎬 AI Video & Text Processor")
    st.markdown("""
    This app splits a video into segments based on the number of paragraphs in your text, 
    generates TTS for each paragraph, adjusts video speed to match the audio, 
    and applies a '3s Play, 2s Freeze' effect for copyright protection.
    """)

    with st.sidebar:
        st.header("Inputs & Settings")
        
        st.subheader("1. Voice Settings")
        selected_voice = st.selectbox("Select Voice", options=[v["name"] for v in VOICES])
        voice_id = next(v["id"] for v in VOICES if v["name"] == selected_voice)
        
        col1, col2 = st.columns(2)
        with col1:
            selected_style = st.selectbox("Recap Style", options=[s["name"] for s in RECAP_STYLES])
            style_data = next(s for s in RECAP_STYLES if s["name"] == selected_style)
        with col2:
            selected_emotion = st.selectbox("Emotion", options=[e["name"] for e in EMOTIONS])
            emotion_data = next(e for e in EMOTIONS if e["name"] == selected_emotion)
            
        # Combine speed and pitch from style and emotion
        final_speed = style_data["speed"] + emotion_data["s"]
        final_pitch = style_data["pitch"] + emotion_data["p"]
        
        st.caption(f"Applied Speed: {final_speed}%, Pitch: {final_pitch}Hz")
        
        st.markdown("---")
        st.subheader("2. Video Editing Settings")
        play_duration = st.slider("Play Duration (seconds)", min_value=1, max_value=5, value=3)
        
        col3, col4 = st.columns(2)
        with col3:
            freeze1_duration = st.slider("Freeze 1 Duration (seconds)", min_value=1, max_value=3, value=1)
            freeze1_zoom = st.selectbox("Freeze 1 Zoom Effect", options=["None", "Zoom In", "Zoom Out"])
        with col4:
            freeze2_duration = st.slider("Freeze 2 Duration (seconds)", min_value=1, max_value=3, value=1)
            freeze2_zoom = st.selectbox("Freeze 2 Zoom Effect", options=["None", "Zoom In", "Zoom Out"])
            
        st.markdown("---")
        st.subheader("3. Content")
        text_input = st.text_area("Enter Text (Unlimited words)", height=300)
        video_file = st.file_uploader("Upload Video (Max 2GB, 1 Hour)", type=["mp4", "mov", "avi"])

    if st.button("Start Processing"):
        if not text_input or not video_file:
            st.error("Please provide both text and a video file.")
            return

        paragraphs = count_paragraphs(text_input)
        num_paragraphs = len(paragraphs)
        st.info(f"Detected {num_paragraphs} paragraphs.")

        # Save uploaded video
        os.makedirs("temp", exist_ok=True)
        video_path = os.path.join("temp", video_file.name)
        with open(video_path, "wb") as f:
            f.write(video_file.getbuffer())

        # Create directories
        audio_dir = "temp/audio"
        segments_dir = "temp/segments"
        final_segments_dir = "temp/final_segments"
        os.makedirs(audio_dir, exist_ok=True)
        os.makedirs(segments_dir, exist_ok=True)
        os.makedirs(final_segments_dir, exist_ok=True)

        # 1. Split Video
        with st.status("Splitting video into segments...") as status:
            video_segments, seg_dur = split_video(video_path, segments_dir, num_paragraphs)
            status.update(label="Video split complete!", state="complete")

        # 2. Process segments in parallel
        st.write("Processing segments (TTS + Speed Adjustment + Effects)...")
        progress_bar = st.progress(0)
        
        final_video_segments = [None] * num_paragraphs
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_index = {
                executor.submit(process_segment, i, paragraphs[i], video_segments[i], audio_dir, final_segments_dir, voice_id, final_speed, final_pitch, play_duration, freeze1_duration, freeze1_zoom, freeze2_duration, freeze2_zoom): i 
                for i in range(num_paragraphs)
            }
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result_path = future.result()
                    final_video_segments[index] = result_path
                except Exception as e:
                    st.error(f"Error processing segment {index}: {e}")
                
                completed += 1
                progress_bar.progress(completed / num_paragraphs)

        # 3. Merge final segments
        st.write("Merging all segments into final video...")
        list_file = "temp/concat_list.txt"
        with open(list_file, "w") as f:
            for seg in final_video_segments:
                if seg:
                    f.write(f"file '{os.path.abspath(seg)}'\n")

        final_output = "output_final.mp4"
        merge_cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_file,
            '-c', 'copy', final_output
        ]
        subprocess.run(merge_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        st.success("Processing complete!")
        st.video(final_output)
        
        with open(final_output, "rb") as f:
            st.download_button("Download Final Video", f, file_name="processed_video.mp4")

if __name__ == "__main__":
    main()
